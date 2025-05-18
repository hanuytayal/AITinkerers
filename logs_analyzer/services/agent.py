import os
import pandas as pd
import openai
from openai import OpenAI
from datetime import datetime
import time
import json
import re

class LogAnalysisAgent:
    def __init__(self, openai_api_key=None, ticket_service=None):
        # Use provided API key or try to get from environment
        self.api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            print("Warning: OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        # Track reasoning steps
        self.reasoning_steps = []
        
        # Store reference to ticket service
        self.ticket_service = ticket_service
        
        # Store identified issues
        self.identified_issues = []
    
    def add_reasoning_step(self, step):
        """Add a reasoning step with timestamp"""
        self.reasoning_steps.append({
            "timestamp": datetime.now().isoformat(),
            "content": step
        })
        return self.reasoning_steps
    
    def analyze_logs(self, logs_df):
        """
        Analyze log data using OpenAI to identify issues
        
        Args:
            logs_df (pandas.DataFrame): DataFrame containing log data
            
        Returns:
            list: List of identified issues with details
        """
        if self.api_key is None:
            # If no API key, use mock data for testing
            return self._mock_analysis(logs_df)
        
        try:
            # Reset reasoning steps and issues
            self.reasoning_steps = []
            self.identified_issues = []
            self.add_reasoning_step("Starting log analysis process")
            
            # Convert dataframe to text for sending to OpenAI
            logs_text = logs_df.to_string(index=False)
            
            # Note: Not truncating logs anymore, sending everything to the model
            self.add_reasoning_step(f"Analyzing {len(logs_df)} log entries")
            
            # Define the function for creating tickets
            create_ticket_tool = {
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
                            "first_seen": {
                                "type": "string",
                                "description": "Timestamp of first occurrence"
                            },
                            "last_seen": {
                                "type": "string",
                                "description": "Timestamp of last occurrence"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of occurrences"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the issue"
                            }
                        },
                        "required": ["issue_type", "service", "severity", "count", "description"]
                    }
                }
            }
            
            # Prepare the prompt for OpenAI with reasoning best practices
            prompt = f"""Analyze these system logs to identify critical issues that require attention from oncall engineers.

            Think through this step-by-step:
            1. First, identify all ERROR and FATAL level log entries
            2. Group them by service and message pattern
            3. Count occurrences of each pattern
            4. Filter to keep only FATAL issues with count >= 5
            5. For each remaining issue, analyze the timestamps, pattern, and impact
            6. Determine severity based on the log level and message content
            7. Recommend specific actions based on the issue type
            
            FORMAT YOUR RESPONSE AS JSON with the following structure:
            [
                {{
                    "issue_type": "string",
                    "service": "string",
                    "severity": "string",
                    "first_seen": "timestamp",
                    "last_seen": "timestamp",
                    "count": number,
                    "description": "string",
                    "recommended_action": "string"
                    "knowledge_sources":"string"
                }}
            ]
            
            Here are the logs:
            {logs_text}
            """
            
            self.add_reasoning_step("Sending logs to OpenAI reasoning model for analysis")
            
            # Call OpenAI API with reasoning model and function calling using best practices
            response = self.client.chat.completions.create(
                model="o4-mini",  # Using reasoning-optimized model
                messages=[
                    {"role": "user", "content": prompt}
                ],
                tools=[create_ticket_tool],
                tool_choice="auto"
            )
            
            # Process the response and extract reasoning
            self._process_openai_response(response)
            
            # Return the identified issues
            return self.identified_issues
            
        except Exception as e:
            error_msg = f"Error analyzing logs with OpenAI: {e}"
            print(error_msg)
            self.add_reasoning_step(error_msg)
            # Fall back to mock data on error
            return self._mock_analysis(logs_df)
    
    def _process_openai_response(self, response):
        """Process the OpenAI response to extract reasoning and function calls"""
        # Extract message content if available
        choice = response.choices[0]
        
        if hasattr(choice, 'message') and choice.message:
            message = choice.message
            
            # Process content for reasoning
            if message.content:
                reasoning_content = message.content
                # Split the content into reasoning steps
                reasoning_steps = reasoning_content.split("\n\n")
                for step in reasoning_steps:
                    if step.strip():
                        self.add_reasoning_step(step.strip())
            
            # Extract function calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.type == 'function' and tool_call.function.name == 'create_ticket':
                        try:
                            # Parse arguments
                            args = json.loads(tool_call.function.arguments)
                            
                            # Validate issue - must be Critical and occur >= 5 times
                            if args.get('severity') == 'Critical' and args.get('count', 0) >= 5:
                                # Store the issue
                                self.identified_issues.append(args)
                                
                                self.add_reasoning_step(f"Identified critical issue in {args.get('service')}: {args.get('issue_type')} ({args.get('count')} occurrences)")
                        except Exception as e:
                            self.add_reasoning_step(f"Error processing function call: {e}")
            
            # Try to extract issues from regular message content if no function calls
            else:
                content = message.content
                
                # Try to extract JSON from the response
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    try:
                        json_str = json_match.group()
                        issues = json.loads(json_str)
                        
                        # Filter for critical issues with count >= 5
                        filtered_issues = [issue for issue in issues 
                                        if issue.get('severity') == 'Critical' and issue.get('count', 0) >= 5]
                        
                        self.identified_issues = filtered_issues
                        
                        issue_count = len(filtered_issues)
                        self.add_reasoning_step(f"Identified {issue_count} critical issues requiring immediate attention")
                    except Exception as e:
                        self.add_reasoning_step(f"Error parsing issues from response: {e}")
    
    def _mock_analysis(self, logs_df):
        """Generate mock analysis results for testing or when API is unavailable"""
        self.add_reasoning_step("Using mock analysis mode due to API unavailability")
        
        # Filter for FATAL logs
        fatal_logs = logs_df[logs_df['level'] == 'FATAL']
        
        # Group by service and message
        grouped = fatal_logs.groupby(['service', 'message'])
        
        issues = []
        for (service, message), group in grouped:
            count = len(group)
            if count >= 5:  # Only include issues that occurred 5+ times
                timestamps = sorted(group['timestamp'].tolist())
                
                # Simulate reasoning steps
                self.add_reasoning_step(f"Found {count} occurrences of FATAL error in {service}")
                self.add_reasoning_step(f"Analyzing message pattern: '{message}'")
                self.add_reasoning_step(f"First occurrence at {timestamps[0]}, last at {timestamps[-1]}")
                
                issue = {
                    "issue_type": "Critical Error" if "OOM" not in message else "Out of Memory",
                    "service": service,
                    "severity": "Critical",
                    "first_seen": timestamps[0],
                    "last_seen": timestamps[-1],
                    "count": count,
                    "description": f"{message} occurred {count} times",
                    "recommended_action": "Restart service" if "OOM" in message else "Investigate error condition",
                    "knowledge_sources":"Test"  
                } 
                
                issues.append(issue)
                self.add_reasoning_step(f"Creating ticket for critical issue in {service}: {message} ({count} occurrences)")
        
        # Simulate processing time
        time.sleep(1)
        
        return issues 
    
    def get_reasoning_steps(self):
        """Get the reasoning steps from the analysis"""
        return self.reasoning_steps
    
    def get_identified_issues(self):
        """Get the identified issues"""
        return self.identified_issues 