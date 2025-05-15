import asyncio
import contextlib
import logging
from typing import Any, Callable, Dict, Optional

from server_shutdown import shutdown_manager

logger = logging.getLogger(__name__)

class TransportShutdownHandler:
    """Base class for transport-specific shutdown handlers."""
    
    def __init__(self, transport_name: str):
        """
        Initialize the transport handler.
        
        Args:
            transport_name: Name of the transport (e.g., 'stdio', 'sse')
        """
        self.transport_name = transport_name
        self._shutdown_callbacks: Dict[str, Callable] = {}
        
        # Register this handler with the shutdown manager
        shutdown_manager.register_transport_shutdown_hook(
            transport_name, self.handle_shutdown
        )
    
    def register_shutdown_callback(self, name: str, callback: Callable):
        """
        Register a callback for this transport.
        
        Args:
            name: Unique name for this callback
            callback: Function to call during shutdown
        """
        self._shutdown_callbacks[name] = callback
    
    async def handle_shutdown(self):
        """Handle transport-specific shutdown. Override in subclasses."""
        # Call all registered callbacks
        for name, callback in self._shutdown_callbacks.items():
            try:
                result = callback()
                if asyncio.iscoroutine(result):
                    await result
                    
            except Exception as e:
                logger.error(f"Error in {self.transport_name} shutdown callback {name}: {e}")

class StdioTransportHandler(TransportShutdownHandler):
    """Handles graceful shutdown for STDIO transport."""
    
    def __init__(self):
        """Initialize the STDIO transport handler."""
        super().__init__("stdio")
        self.read_stream = None
        self.write_stream = None
    
    def set_streams(self, read_stream: Any, write_stream: Any):
        """
        Set the read/write streams for this transport.
        
        Args:
            read_stream: The stream used for reading
            write_stream: The stream used for writing
        """
        self.read_stream = read_stream
        self.write_stream = write_stream
    
    async def handle_shutdown(self):
        """
        Handle STDIO transport shutdown.
        
        This method specifically addresses the BrokenResourceError that occurs
        when shutting down stdio streams.
        """
        # Call parent method to run registered callbacks
        await super().handle_shutdown()
        
        # Gracefully close streams if they exist
        if self.write_stream:
            with contextlib.suppress(Exception):
                if hasattr(self.write_stream, 'aclose') and callable(getattr(self.write_stream, 'aclose')):
                    try:
                        await self.write_stream.aclose()
                    except Exception as e:
                        pass  # Suppress expected errors
                elif hasattr(self.write_stream, 'close') and callable(getattr(self.write_stream, 'close')):
                    self.write_stream.close()
        
        if self.read_stream:
            with contextlib.suppress(Exception):
                if hasattr(self.read_stream, 'aclose') and callable(getattr(self.read_stream, 'aclose')):
                    try:
                        await self.read_stream.aclose()
                    except Exception as e:
                        pass  # Suppress expected errors
                elif hasattr(self.read_stream, 'close') and callable(getattr(self.read_stream, 'close')):
                    self.read_stream.close()

class SseTransportHandler(TransportShutdownHandler):
    """Handles graceful shutdown for SSE transport."""
    
    def __init__(self):
        """Initialize the SSE transport handler."""
        super().__init__("sse")
        self.active_sessions = {}
    
    def register_session(self, session_id: str, session_obj: Any):
        """
        Register an active SSE session.
        
        Args:
            session_id: Unique session identifier
            session_obj: Session object to be closed during shutdown
        """
        self.active_sessions[session_id] = session_obj
    
    def remove_session(self, session_id: str):
        """
        Remove a session from tracking.
        
        Args:
            session_id: Session identifier to remove
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    async def handle_shutdown(self):
        """
        Handle SSE transport shutdown.
        
        This manages the graceful closing of SSE connections and proper
        notification to clients.
        """
        # Call parent method to run registered callbacks
        await super().handle_shutdown()
        
        # Close all active sessions
        close_tasks = []
        for session_id, session in self.active_sessions.items():
            try:
                # Send a close notification if possible
                if hasattr(session, 'send_close_notification') and callable(getattr(session, 'send_close_notification')):
                    try:
                        notify_task = session.send_close_notification()
                        if asyncio.iscoroutine(notify_task):
                            close_tasks.append(asyncio.create_task(notify_task))
                    except Exception as e:
                        pass  # Suppress expected errors
                
                # Close the session
                if hasattr(session, 'close') and callable(getattr(session, 'close')):
                    close_method = session.close()
                    if asyncio.iscoroutine(close_method):
                        close_tasks.append(asyncio.create_task(close_method))
                        
            except Exception as e:
                logger.error(f"Error closing SSE session {session_id}: {e}")
        
        # Wait for all close operations with a timeout
        if close_tasks:
            try:
                await asyncio.wait(close_tasks, timeout=3.0)
            except asyncio.TimeoutError:
                pass  # Suppress timeout error
            except Exception as e:
                logger.error(f"Error waiting for SSE sessions to close: {e}")

# Create default transport handlers
stdio_handler = StdioTransportHandler()
sse_handler = SseTransportHandler() 