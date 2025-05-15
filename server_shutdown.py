import asyncio
import logging
import sys
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from signal_handler import graceful_shutdown

logger = logging.getLogger(__name__)

class ShutdownReason(Enum):
    """Reasons for server shutdown."""
    NORMAL = auto()         # Normal shutdown requested by code
    SIGNAL = auto()         # Shutdown triggered by signal (SIGINT, SIGTERM)
    ERROR = auto()          # Shutdown due to unrecoverable error
    TIMEOUT = auto()        # Shutdown timed out
    UNKNOWN = auto()        # Unknown reason

class ShutdownStatus(Enum):
    """Status of shutdown process."""
    NOT_STARTED = auto()    # Shutdown not initiated
    IN_PROGRESS = auto()    # Shutdown in progress
    COMPLETED = auto()      # Shutdown completed successfully
    FORCED = auto()         # Shutdown was forced after timeout
    FAILED = auto()         # Shutdown failed

class ServerShutdownManager:
    """
    Manager for MCP server graceful shutdown across different transport types.
    
    This class coordinates the shutdown process, ensuring that transport-specific
    cleanup happens correctly and that in-progress operations can complete.
    """
    
    def __init__(self, default_timeout: float = 5.0):
        """
        Initialize the shutdown manager.
        
        Args:
            default_timeout: Default timeout in seconds for shutdown operations
        """
        self.default_timeout = default_timeout
        self.status = ShutdownStatus.NOT_STARTED
        self.reason = ShutdownReason.UNKNOWN
        
        # Hooks for different stages of shutdown
        self._pre_shutdown_hooks: List[Callable] = []
        self._transport_shutdown_hooks: Dict[str, Callable] = {}
        self._post_shutdown_hooks: List[Callable] = []
        
        # Track active connections
        self.active_connections: Dict[str, Any] = {}
        
        # Exit code to use when terminating
        self.exit_code = 0
        
        # Register with global signal handler
        graceful_shutdown.register_shutdown_hook("server_shutdown", self._handle_signal_shutdown)
    
    def add_active_connection(self, conn_id: str, conn_obj: Any):
        """
        Track an active connection.
        
        Args:
            conn_id: Unique identifier for the connection
            conn_obj: The connection object
        """
        self.active_connections[conn_id] = conn_obj
    
    def remove_active_connection(self, conn_id: str):
        """
        Remove a tracked connection.
        
        Args:
            conn_id: Connection identifier to remove
        """
        if conn_id in self.active_connections:
            del self.active_connections[conn_id]
    
    def register_pre_shutdown_hook(self, hook: Callable):
        """
        Register a function to run before shutdown starts.
        
        Args:
            hook: Function to call before shutdown
        """
        self._pre_shutdown_hooks.append(hook)
    
    def register_transport_shutdown_hook(self, transport_name: str, hook: Callable):
        """
        Register a transport-specific shutdown function.
        
        Args:
            transport_name: Name of the transport (e.g., 'stdio', 'sse')
            hook: Function to handle transport-specific shutdown
        """
        self._transport_shutdown_hooks[transport_name] = hook
    
    def register_post_shutdown_hook(self, hook: Callable):
        """
        Register a function to run after shutdown is complete.
        
        Args:
            hook: Function to call after shutdown
        """
        self._post_shutdown_hooks.append(hook)
    
    async def shutdown(self, reason: ShutdownReason = ShutdownReason.NORMAL, 
                      timeout: Optional[float] = None) -> bool:
        """
        Initiate graceful shutdown sequence.
        
        Args:
            reason: Reason for shutdown
            timeout: Maximum time to wait for shutdown (None = use default_timeout)
            
        Returns:
            True if shutdown completed successfully, False otherwise
        """
        if self.status != ShutdownStatus.NOT_STARTED:
            logger.error(f"Shutdown already in progress with status {self.status}")
            return False
        
        self.status = ShutdownStatus.IN_PROGRESS
        self.reason = reason
        timeout = timeout or self.default_timeout
        
        try:
            # Run pre-shutdown hooks
            for hook in self._pre_shutdown_hooks:
                try:
                    result = hook()
                    # Handle both regular and coroutine functions
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in pre-shutdown hook {hook.__name__}: {e}")
            
            # Close active connections
            await self._close_active_connections(timeout)
            
            # Run transport-specific shutdown hooks
            for transport_name, hook in self._transport_shutdown_hooks.items():
                try:
                    result = hook()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in transport shutdown hook for {transport_name}: {e}")
            
            # Run post-shutdown hooks
            for hook in self._post_shutdown_hooks:
                try:
                    result = hook()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in post-shutdown hook {hook.__name__}: {e}")
            
            self.status = ShutdownStatus.COMPLETED
            return True
            
        except asyncio.TimeoutError:
            self.status = ShutdownStatus.FORCED
            self.exit_code = 1
            logger.error(f"Shutdown timed out after {timeout}s")
            return False
        except Exception as e:
            self.status = ShutdownStatus.FAILED
            self.exit_code = 2
            logger.error(f"Shutdown failed: {e}")
            return False
    
    async def _close_active_connections(self, timeout: float):
        """
        Close all active connections with a timeout.
        
        Args:
            timeout: Maximum time to wait for connections to close
        """
        if not self.active_connections:
            return
        
        close_tasks = []
        
        for conn_id, conn in self.active_connections.items():
            if hasattr(conn, 'close') and callable(conn.close):
                try:
                    close_method = conn.close()
                    if asyncio.iscoroutine(close_method):
                        close_tasks.append(asyncio.create_task(close_method))
                except Exception as e:
                    logger.error(f"Error scheduling close for connection {conn_id}: {e}")
        
        if close_tasks:
            done, pending = await asyncio.wait(close_tasks, timeout=timeout)
            
            if pending:
                logger.error(f"{len(pending)} connection close operations timed out")
                for task in pending:
                    task.cancel()
    
    def _handle_signal_shutdown(self):
        """Handle shutdown triggered by signal handler."""
        loop = asyncio.get_event_loop()
        shutdown_task = asyncio.create_task(
            self.shutdown(ShutdownReason.SIGNAL)
        )
        
        # Add a timeout to force exit if shutdown doesn't complete
        shutdown_timeout = self.default_timeout * 1.5  # Give a bit extra time
        
        def force_exit():
            logger.error("Forcing exit after shutdown timeout")
            sys.exit(1)
        
        loop.call_later(shutdown_timeout, force_exit)
    
    def exit(self):
        """Exit the process with the appropriate status code."""
        sys.exit(self.exit_code)

# Create a default shutdown manager
shutdown_manager = ServerShutdownManager() 