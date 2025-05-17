#!/usr/bin/env python3
"""
Test script to verify OpenAI reasoning model integration
"""

import os
import sys
from dotenv import load_dotenv
import openai
import json

def test_reasoning_model():
    """Test the OpenAI reasoning model functionality"""
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
        
        # Simple test prompt for reasoning
        prompt = """
        Please analyze this short log extract and identify any critical issues:
        
        2025-05-17T20:41:36.921897,payment-service,INFO,Fatal OOM error in payment-service
        2025-05-17T20:42:33.921897,payment-service,DEBUG,Fatal OOM error in payment-service
        2025-05-17T20:44:03.921897,payment-service,INFO,Fatal OOM error in payment-service
        2025-05-17T20:45:15.921897,payment-service,DEBUG,Fatal OOM error in payment-service
        2025-05-17T20:45:27.921897,payment-service,INFO,Fatal OOM error in payment-service
        """
        
        # Call OpenAI API with reasoning model
        response = openai.ChatCompletion.create(
            model="o1-mini",  # Using reasoning-optimized model
            messages=[
                {"role": "system", "content": "You are a log analysis assistant that thinks step by step."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1,
            tools=[{"type": "reasoning"}],
            tool_choice={"type": "reasoning"}
        )
        
        # Print raw response for debugging
        print("\nRaw API Response:")
        print(json.dumps(response, indent=2))
        
        # Extract reasoning
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                if tool_call.type == 'reasoning':
                    print("\nReasoning Output:")
                    print(tool_call.reasoning.content)
        
        # Print regular content
        print("\nRegular Output:")
        print(response.choices[0].message.content)
        
        print("\nOpenAI reasoning model test successful!")
        return True
        
    except Exception as e:
        print(f"\nError connecting to OpenAI reasoning model: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI reasoning model integration...")
    success = test_reasoning_model()
    sys.exit(0 if success else 1) 