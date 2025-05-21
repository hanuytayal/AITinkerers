import os
import pandas as pd
from werkzeug.utils import secure_filename

class FileUtils:
    """Utilities for handling file operations in the application"""
    
    @staticmethod
    def allowed_file(filename, allowed_extensions=None):
        """Check if a file has an allowed extension"""
        if allowed_extensions is None:
            allowed_extensions = ['.csv']
        
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in [ext.lstrip('.') for ext in allowed_extensions]
    
    @staticmethod
    def save_uploaded_file(file, upload_folder):
        """Save an uploaded file to the specified folder"""
        if not file:
            return None
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filepath
    
    @staticmethod
    def read_log_file(filepath):
        """Read a log file and return a pandas DataFrame"""
        try:
            # Auto-detect file type by extension
            if filepath.endswith('.csv'):
                return pd.read_csv(filepath)
            else:
                # Default to CSV
                return pd.read_csv(filepath)
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    @staticmethod
    def get_log_files(upload_folder):
        """Get a list of log files in the upload folder"""
        if not os.path.exists(upload_folder):
            return []
        
        files = []
        for filename in os.listdir(upload_folder):
            if FileUtils.allowed_file(filename, ['.csv']):
                files.append(filename)
        
        return files 