import os
import pandas as pd
import openai
from datetime import datetime
import time
import json
import re

class LogAnalysisAgent:
    def __init__(self, openai_api_key=None):
        # Use provided API key or try to get from environment
        self.api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            print("Warning: OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        else:
            openai.api_key = self.api_key
        
        # Track reasoning steps
        self.reasoning_steps = []
    
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
            # Reset reasoning steps
            self.reasoning_steps = []
            self.add_reasoning_step("Starting log analysis process")
            
            # Convert dataframe to text for sending to OpenAI
            logs_text = logs_df.to_string(index=False)
            
            # Truncate if too large
            if len(logs_text) > 12000:  # OpenAI has token limits
                logs_text = logs_text[:12000] + "\n[Truncated]..."
                self.add_reasoning_step("Log data truncated due to size limitations")
            
            # Prepare the prompt for OpenAI with reasoning
            prompt = f"""
            You are a log analysis agent. Analyze these system logs and identify critical issues 
            that require attention from oncall engineers.
            
            Focus on:
            1. Error and Fatal level issues
            2. Patterns of failures in specific services
            3. Out of memory (OOM) errors
            4. Service unavailability 
            5. Database connection issues
            
            For each issue, provide:
            - Issue type
            - Affected service
            - Severity (Critical, High, Medium, Low)
            - First occurrence timestamp
            - Last occurrence timestamp
            - Count of occurrences
            - Description of the issue
            - Recommended action
            
            EXTREMELY IMPORTANT: Only issues with FATAL severity that occurred 5 or more times should be included.

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
                }}
            ]
            
            Here are the logs:
            {logs_text}
            """
            
            self.add_reasoning_step("Sending logs to OpenAI reasoning model for analysis")
            
            # Call OpenAI API with reasoning model
            response = openai.ChatCompletion.create(
                model="o1-mini",  # Using reasoning-optimized model
                messages=[
                    {"role": "system", "content": "You are a log analysis AI assistant that thinks step by step and provides detailed reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic responses
                max_tokens=4000,
                top_p=0.95,
                seed=42,
                # Enable reasoning
                tools=[{"type": "reasoning"}],
                tool_choice={"type": "reasoning"}
            )
            
            # Extract and parse the response content
            result = response.choices[0].message.content
            
            # Extract reasoning if available
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    if tool_call.type == 'reasoning':
                        reasoning_content = tool_call.reasoning.content
                        # Split reasoning into steps
                        reasoning_steps = reasoning_content.split("\n\n")
                        for step in reasoning_steps:
                            if step.strip():
                                self.add_reasoning_step(step.strip())
            
            self.add_reasoning_step("Parsing model response to extract identified issues")
            
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON content in the response
            json_match = re.search(r'\[[\s\S]*\]', result)
            if json_match:
                json_str = json_match.group()
                issues = json.loads(json_str)
            else:
                issues = json.loads(result)  # Try parsing the whole response
            
            # Ensure only FATAL issues with count >= 5 are included
            filtered_issues = [issue for issue in issues 
                               if issue.get('severity') == 'Critical' and issue.get('count', 0) >= 5]
            
            issue_count = len(filtered_issues)
            self.add_reasoning_step(f"Identified {issue_count} critical issues requiring immediate attention")
            
            return filtered_issues
            
        except Exception as e:
            error_msg = f"Error analyzing logs with OpenAI: {e}"
            print(error_msg)
            self.add_reasoning_step(error_msg)
            # Fall back to mock data on error
            return self._mock_analysis(logs_df)
    
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
                issues.append({
                    "issue_type": "Critical Error" if "OOM" not in message else "Out of Memory",
                    "service": service,
                    "severity": "Critical",
                    "first_seen": timestamps[0],
                    "last_seen": timestamps[-1],
                    "count": count,
                    "description": f"{message} occurred {count} times",
                    "recommended_action": "Restart service" if "OOM" in message else "Investigate error condition"
                })
                
                self.add_reasoning_step(f"Identified critical issue in {service}: {message} ({count} occurrences)")
        
        # Add synthetic pause to simulate API processing time
        time.sleep(1)
        
        return issues
    
    def get_reasoning_steps(self):
        """Get the reasoning steps from the analysis"""
        return self.reasoning_steps 