#!/usr/bin/env python3
"""
Auto-reload Development Server for SigmaHQ RAG Application

This script provides auto-reload functionality for the Gradio application
using the watchdog library to monitor file changes.
"""

import sys
import os
import subprocess
import signal
import time
import logging
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """Handle file system events for auto-reload."""
    
    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
        self.last_restart = time.time()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Get the file path
        file_path = Path(event.src_path)
        
        # Only restart for Python files
        if file_path.suffix == '.py':
            current_time = time.time()
            
            # Debounce restarts (wait at least 2 seconds between restarts)
            if current_time - self.last_restart > 2.0:
                logger.info(f"File changed: {file_path}")
                logger.info("Restarting application...")
                self.last_restart = current_time
                self.restart_callback()


class DevelopmentServer:
    """Development server with auto-reload functionality."""
    
    def __init__(self):
        self.process = None
        self.observer = None
        self.running = False
        
    def start_app(self):
        """Start the application process."""
        if self.process:
            self.stop_app()
        
        # Change to project directory
        project_root = Path(__file__).parent.absolute()
        os.chdir(project_root)
        
        # Start the application
        try:
            cmd = [sys.executable, "main.py", "--dev"]
            logger.info(f"Starting application with command: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd)
            logger.info(f"Application started with PID: {self.process.pid}")
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise
    
    def stop_app(self):
        """Stop the application process."""
        if self.process:
            logger.info("Stopping application...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Application did not terminate gracefully, killing...")
                self.process.kill()
                self.process.wait()
            finally:
                self.process = None
    
    def start_observer(self):
        """Start the file system observer."""
        if self.observer:
            self.stop_observer()
        
        # Set up file system monitoring
        self.observer = Observer()
        handler = FileChangeHandler(self.restart_app)
        
        # Watch the entire project directory
        project_root = Path(__file__).parent.absolute()
        self.observer.schedule(handler, str(project_root), recursive=True)
        
        logger.info(f"Starting file system observer for: {project_root}")
        self.observer.start()
    
    def stop_observer(self):
        """Stop the file system observer."""
        if self.observer:
            logger.info("Stopping file system observer...")
            self.observer.stop()
            self.observer.join()
            self.observer = None
    
    def restart_app(self):
        """Restart the application."""
        self.stop_app()
        time.sleep(1)  # Wait a moment before restarting
        self.start_app()
    
    def run(self):
        """Run the development server with auto-reload."""
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start the application
            self.start_app()
            
            # Start file system monitoring
            self.start_observer()
            
            logger.info("Development server is running!")
            logger.info("Auto-reload enabled - changes to Python files will restart the server")
            logger.info("Application will be available at: http://localhost:8000")
            logger.info("Press Ctrl+C to stop the server")
            
            # Keep the server running
            while self.running:
                time.sleep(1)
                
                # Check if the application process is still running
                if self.process and self.process.poll() is not None:
                    logger.warning("Application process terminated unexpectedly, restarting...")
                    self.restart_app()
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Error in development server: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the development server."""
        self.running = False
        self.stop_observer()
        self.stop_app()
        logger.info("Development server stopped")


def main():
    """Main entry point for the development server."""
    print("Starting SigmaHQ RAG Development Server with Auto-Reload")
    print("=" * 60)
    
    server = DevelopmentServer()
    try:
        server.run()
    except Exception as e:
        logger.error(f"Failed to start development server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()