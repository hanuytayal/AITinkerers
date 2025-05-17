import os
import shutil
import sys

def setup_example():
    """Copy the example log file to the uploads directory"""
    
    # Create uploads directory if it doesn't exist
    os.makedirs('uploads', exist_ok=True)
    
    # Check if the example file exists
    example_path = '../data/logs/oom.csv'
    if not os.path.exists(example_path):
        print(f"Error: Could not find example file at {example_path}")
        return False
    
    # Copy the file to uploads directory
    try:
        shutil.copy(example_path, 'uploads/oom.csv')
        print(f"Success: Copied example log file to uploads/oom.csv")
        return True
    except Exception as e:
        print(f"Error copying file: {e}")
        return False

if __name__ == "__main__":
    setup_example() 