#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
from app import app

def check_env():
    """Check that environment is properly set up"""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.environ.get('OPENAI_API_KEY'):
        print("Warning: OpenAI API key not found. Set OPENAI_API_KEY environment variable for AI analysis.")
        print("Without an API key, the application will use mock analysis.")
        
        # Ask if user wants to continue
        response = input("Continue without API key? (y/n): ")
        if response.lower() != 'y':
            print("Exiting. Set API key and try again.")
            return False
    
    return True

def main():
    """Run the Flask application"""
    if not check_env():
        sys.exit(1)
    
    # Create uploads directory if it doesn't exist
    os.makedirs('uploads', exist_ok=True)
    
    # Check if running directly or imported
    if __name__ == '__main__':
        print("Starting Log Analysis Agent...")
        print("Access the web interface at http://127.0.0.1:5000")
        app.run(debug=True)

if __name__ == '__main__':
    main() 