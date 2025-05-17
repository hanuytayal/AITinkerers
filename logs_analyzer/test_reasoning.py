#!/usr/bin/env python3
"""
Test script to verify OpenAI reasoning model integration with function calling
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import json

def test_reasoning_model():
    """Test the OpenAI reasoning model functionality with function calling"""
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
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Define the ticket creation function
        create_ticket_function = {
            "type": "function",
            "function": {
                "name": "create_ticket",
                "description": "Create a ticket for an oncall engineer to address a critical issue",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_type": {
                            "type": "string",
                            "description": "Type of the issue (e.g., 'Out of Memory', 'Critical Error')"
                        },
                        "service": {
                            "type": "string",
                            "description": "The service experiencing the issue"
                        },
                        "severity": {
                            "type": "string",
                            "description": "Severity level (Critical, High, Medium, Low)"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of occurrences"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the issue"
                        },
                        "recommended_action": {
                            "type": "string",
                            "description": "Recommended action to solve the issue"
                        }
                    },
                    "required": ["issue_type", "service", "severity", "count", "description", "recommended_action"]
                }
            }
        }
        
        # Simple test prompt for reasoning with function calling
        prompt = """
        Please analyze this short log extract and identify any critical issues:
        
        2025-05-17T20:41:36.921897,payment-service,INFO,Fatal OOM error in payment-service
        2025-05-17T20:42:33.921897,payment-service,DEBUG,Fatal OOM error in payment-service
        2025-05-17T20:44:03.921897,payment-service,INFO,Fatal OOM error in payment-service
        2025-05-17T20:45:15.921897,payment-service,DEBUG,Fatal OOM error in payment-service
        2025-05-17T20:45:27.921897,payment-service,INFO,Fatal OOM error in payment-service
        
        Only create tickets for FATAL severity issues that occurred 5 or more times.
        After analyzing the logs, create tickets using the create_ticket function.
        """
        
        # Call OpenAI API with reasoning model and function calling using new client syntax
        response = client.chat.completions.create(
            model="o4-mini",  # Using reasoning-optimized model
            messages=[
                {"role": "system", "content": "You are a log analysis assistant that thinks step by step and creates tickets for critical issues."},
                {"role": "user", "content": prompt}
            ],
            tools=[{"type": "reasoning"}, create_ticket_function],
            tool_choice="auto"
        )
        
        # Print raw response for debugging
        print("\nRaw API Response:")
        print(json.dumps(response.model_dump(), indent=2))
        
        # Extract reasoning and function calls
        choice = response.choices[0]
        if hasattr(choice, 'message') and choice.message.tool_calls:
            print("\nTool Calls Found:")
            
            for tool_call in choice.message.tool_calls:
                # Extract reasoning
                if tool_call.type == 'reasoning':
                    print("\nReasoning Output:")
                    print(tool_call.reasoning)
                
                # Extract function calls for ticket creation
                elif tool_call.type == 'function' and tool_call.function.name == 'create_ticket':
                    print("\nFunction Call - Create Ticket:")
                    args = json.loads(tool_call.function.arguments)
                    print(json.dumps(args, indent=2))
        
        # Print regular content
        print("\nRegular Output:")
        print(choice.message.content)
        
        print("\nOpenAI reasoning model test with function calling successful!")
        return True
        
    except Exception as e:
        print(f"\nError connecting to OpenAI reasoning model: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI reasoning model integration with function calling...")
    success = test_reasoning_model()
    sys.exit(0 if success else 1) 