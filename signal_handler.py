import asyncio
import logging
import signal
import sys
from types import FrameType
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class GracefulShutdown:
    """
    Utility class for handling graceful shutdown across different transport types.
    
    This class sets up signal handlers for graceful termination and provides
    a coordinated way to shut down the MCP server regardless of transport.
    """
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.original_handlers: Dict[int, Any] = {}
        self._shutdown_hooks: Dict[str, Callable] = {}
        self._is_shutting_down = False
        
    def setup_signal_handlers(self):
        """Set up handlers for SIGINT and SIGTERM."""
        # Store original handlers
        self.original_handlers[signal.SIGINT] = signal.getsignal(signal.SIGINT)
        self.original_handlers[signal.SIGTERM] = signal.getsignal(signal.SIGTERM)
        
        # Set new handlers
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        
        logger.info("Signal handlers for graceful shutdown have been set up")
    
    def _handle_shutdown_signal(self, sig: int, frame: Optional[FrameType]):
        """
        Handle termination signals (SIGINT, SIGTERM).
        
        Args:
            sig: Signal number
            frame: Current stack frame
        """
        sig_name = signal.Signals(sig).name
        
        if self._is_shutting_down:
            # If we're already shutting down, another signal means force exit
            logger.warning(f"Received {sig_name} again during shutdown. Forcing exit.")
            # Restore original handler and re-raise signal
            signal.signal(sig, self.original_handlers[sig])
            signal.raise_signal(sig)
            return
            
        logger.info(f"Received {sig_name} signal. Starting graceful shutdown...")
        self._is_shutting_down = True
        
        # Set asyncio event to coordinate shutdown across async code
        if not self.shutdown_event.is_set():
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(self.shutdown_event.set)
            except RuntimeError:
                # No event loop running, just set the event
                self.shutdown_event.set()
        
        # Run any registered shutdown hooks
        self._run_shutdown_hooks()
    
    def is_shutting_down(self) -> bool:
        """Return True if shutdown is in progress."""
        return self._is_shutting_down
    
    def register_shutdown_hook(self, name: str, hook: Callable):
        """
        Register a function to be called during shutdown.
        
        Args:
            name: A unique name for the hook
            hook: Callable that will be executed during shutdown
        """
        self._shutdown_hooks[name] = hook
        logger.debug(f"Registered shutdown hook: {name}")
    
    def _run_shutdown_hooks(self):
        """Run all registered shutdown hooks."""
        for name, hook in self._shutdown_hooks.items():
            try:
                logger.debug(f"Running shutdown hook: {name}")
                hook()
            except Exception as e:
                logger.error(f"Error in shutdown hook {name}: {e}")
    
    def restore_signal_handlers(self):
        """Restore original signal handlers."""
        for sig, handler in self.original_handlers.items():
            signal.signal(sig, handler)
            
# Singleton instance
graceful_shutdown = GracefulShutdown() 