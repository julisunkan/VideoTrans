import os
import logging
from datetime import datetime, timedelta

class FileCleanupService:
    def __init__(self):
        """Initialize file cleanup service."""
        self.upload_dir = 'uploads'
        self.output_dir = 'outputs'
        self.max_age_hours = 24  # Files older than 24 hours will be deleted
    
    def cleanup_old_files(self):
        """Remove files older than max_age_hours."""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=self.max_age_hours)
            
            # Clean upload directory
            self._cleanup_directory(self.upload_dir, cutoff_time)
            
            # Clean output directory
            self._cleanup_directory(self.output_dir, cutoff_time)
            
            logging.info("File cleanup completed successfully")
            
        except Exception as e:
            logging.error(f"File cleanup failed: {str(e)}")
    
    def _cleanup_directory(self, directory, cutoff_time):
        """Clean files in a specific directory."""
        if not os.path.exists(directory):
            return
        
        deleted_count = 0
        
        for filename in os.listdir(directory):
            if filename.startswith('.'):  # Skip hidden files like .gitkeep
                continue
                
            filepath = os.path.join(directory, filename)
            
            try:
                # Get file modification time
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_mtime < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
                    logging.info(f"Deleted old file: {filepath}")
                    
            except Exception as e:
                logging.warning(f"Failed to delete file {filepath}: {str(e)}")
        
        if deleted_count > 0:
            logging.info(f"Deleted {deleted_count} old files from {directory}")
    
    def cleanup_session_files(self, session_id):
        """Clean files for a specific session."""
        try:
            # Find and delete files matching the session ID
            for directory in [self.upload_dir, self.output_dir]:
                if not os.path.exists(directory):
                    continue
                    
                for filename in os.listdir(directory):
                    if session_id in filename:
                        filepath = os.path.join(directory, filename)
                        try:
                            os.remove(filepath)
                            logging.info(f"Deleted session file: {filepath}")
                        except Exception as e:
                            logging.warning(f"Failed to delete session file {filepath}: {str(e)}")
                            
        except Exception as e:
            logging.error(f"Session cleanup failed: {str(e)}")
