#!/usr/bin/env python3
"""
Simple test script to verify OpenAI API connection
"""

import os
import sys
from dotenv import load_dotenv
import openai

def test_openai_connection():
    """Test connection to OpenAI API"""
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set your API key and try again.")
        print("You can get an API key from https://platform.openai.com/api-keys")
        return False
    
    try:
        # Set API key
        openai.api_key = api_key
        
        # Simple API call to test connection
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a log analysis assistant."},
                {"role": "user", "content": "Say 'OpenAI connection successful!' if you can read this."}
            ],
            max_tokens=20
        )
        
        # Print response
        print("\nAPI Response:")
        print(response.choices[0].message.content)
        print("\nOpenAI API connection test successful!")
        return True
        
    except Exception as e:
        print(f"\nError connecting to OpenAI API: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI API connection...")
    success = test_openai_connection()
    sys.exit(0 if success else 1) 