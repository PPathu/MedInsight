import re
import threading
import time
import logging
from typing import Dict, List, Optional, Callable

# Set up logging
logger = logging.getLogger(__name__)

class ModelLoadingMonitor:
    """
    Singleton class to track model loading progress.
    This allows other parts of the application to check and stream loading progress.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelLoadingMonitor, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the monitor state."""
        self.current_progress = {}
        self.is_loading = False
        self.last_update = time.time()
        self.subscribers = []
        
    def update_progress(self, file_name: str, progress: int, total: int = 100):
        """Update the progress for a specific file."""
        self.is_loading = True
        self.last_update = time.time()
        
        # Store progress for this file
        self.current_progress[file_name] = {
            'progress': progress,
            'total': total,
            'percentage': progress / total * 100
        }
        
        # Notify subscribers
        for callback in self.subscribers:
            try:
                callback(self.get_progress_summary())
            except Exception as e:
                logger.error(f"Error in progress subscriber callback: {e}")
    
    def subscribe(self, callback: Callable):
        """Subscribe to progress updates."""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from progress updates."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_progress_summary(self) -> Dict:
        """Get a summary of all current progress."""
        # Calculate overall progress by averaging individual file progress
        overall = 0
        if self.current_progress:
            percentages = [info['percentage'] for info in self.current_progress.values()]
            overall = sum(percentages) / len(percentages)
        
        return {
            'overall_progress': overall,
            'files': self.current_progress,
            'is_loading': self.is_loading,
            'timestamp': self.last_update
        }
    
    def reset(self):
        """Reset the progress state."""
        self.current_progress = {}
        self.is_loading = False
        self.last_update = time.time()
        
        # Notify subscribers of reset
        for callback in self.subscribers:
            try:
                callback(self.get_progress_summary())
            except Exception as e:
                logger.error(f"Error in progress subscriber callback: {e}")
    
    def mark_loading_complete(self):
        """Mark loading as complete."""
        self.is_loading = False
        
        # Update all progress to 100%
        for file_name in self.current_progress:
            self.current_progress[file_name]['progress'] = self.current_progress[file_name]['total']
            self.current_progress[file_name]['percentage'] = 100
            
        # Notify subscribers
        for callback in self.subscribers:
            try:
                callback(self.get_progress_summary())
            except Exception as e:
                logger.error(f"Error in progress subscriber callback: {e}")

# Create singleton instance
progress_monitor = ModelLoadingMonitor()

# Regex patterns to detect loading progress in logs
SAFETENSOR_PROGRESS_PATTERN = re.compile(r'model[-_](\d+)[-_]of[-_](\d+)\.safetensors:?\s+(\d+)%')
TOKENIZER_PROGRESS_PATTERN = re.compile(r'(tokenizer_config|vocab|merges)\.json:?\s+(\d+)%')
FETCHING_PATTERN = re.compile(r'Fetching (\d+) files:?\s+(\d+)%')

def monitor_stderr_for_progress(line: str) -> bool:
    """
    Parse stderr/stdout output to detect model loading progress.
    Returns True if progress was detected and updated.
    """
    # Check for safetensor file loading
    match = SAFETENSOR_PROGRESS_PATTERN.search(line)
    if match:
        file_id, total_files, percentage = match.groups()
        file_name = f"model-{file_id}-of-{total_files}.safetensors"
        progress_monitor.update_progress(file_name, int(percentage))
        return True
    
    # Check for tokenizer file loading
    match = TOKENIZER_PROGRESS_PATTERN.search(line)
    if match:
        file_type, percentage = match.groups()
        progress_monitor.update_progress(f"{file_type}.json", int(percentage))
        return True
    
    # Check for fetching files
    match = FETCHING_PATTERN.search(line)
    if match:
        num_files, percentage = match.groups()
        progress_monitor.update_progress(f"fetching_{num_files}_files", int(percentage))
        return True
    
    return False 
