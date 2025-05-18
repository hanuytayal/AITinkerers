import os
import pandas as pd
import openai
from openai import OpenAI
from datetime import datetime
import time
import json
import re
from typing import Optional, Callable, List, Dict, Any

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
        
        # Streaming callback
        self.stream_callback = None
    
    def add_reasoning_step(self, step, step_type="standard"):
        print(f"[DEBUG] add_reasoning_step called: {step} ({step_type})")
        """
        Add a reasoning step with timestamp, avoiding duplicates by content and type.
        """
        for existing in self.reasoning_steps:
            if existing["content"] == step and existing["type"] == step_type:
                return self.reasoning_steps
        reasoning_step = {
            "timestamp": datetime.now().isoformat(),
            "content": step,
            "type": step_type
        }
        self.reasoning_steps.append(reasoning_step)
        if self.stream_callback:
            self.stream_callback(reasoning_step)
        return self.reasoning_steps
    
    def analyze_logs(self, logs_df, stream_callback: Optional[Callable[[Dict], None]] = None):
        """
        Analyze log data using OpenAI to identify issues
        
        Args:
            logs_df (pandas.DataFrame): DataFrame containing log data
            stream_callback: Optional callback function that will be called with each new reasoning step
            
        Returns:
            list: List of identified issues with details
        """
        # Set the streaming callback if provided
        self.stream_callback = stream_callback
        
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
            
            # Define the function for creating tickets with proper name field
            create_ticket_tool = {
                "type": "function",
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
            
            # Prepare the prompt for OpenAI with reasoning best practices
            prompt = f"""Analyze these system logs to identify critical issues that require attention from oncall engineers.

PROBLEM: 
I need to detect FATAL severity issues that occurred at least 5 times in these logs and create tickets for them.

CONTEXT:
- These are system logs from various services
- We need to identify patterns of recurring critical failures
- Only FATAL issues with 5+ occurrences need tickets
- Engineers need clear information about the issue and recommended actions

APPROACH:
To solve this problem, I will:
1. Identify all ERROR and FATAL level log entries
2. Group these entries by service and message pattern
3. Count occurrences of each unique error pattern
4. Filter to keep only FATAL issues with count >= 5
5. For each qualifying issue:
   a. Determine first and last occurrence timestamps
   b. Analyze the message content for root cause hints
   c. Formulate appropriate recommended actions
6. Create tickets for each critical issue (count >= 5)

Here are the logs to analyze:
{logs_text}
"""
            
            self.add_reasoning_step("Analyzing logs...")
            
            # Use streaming API for real-time updates
            current_content = ""
            last_processed_length = 0
            current_tool_call_id = None
            current_tool_call_function_name = None
            current_tool_call_args = ""

            # --- NEW: Accumulate reasoning summary deltas by item_id ---
            summary_accumulators = {}  # item_id -> list of deltas
            # --- NEW: Accumulate function call arguments by item_id ---
            function_call_accumulators = {}  # item_id -> list of deltas
            function_call_names = {}  # item_id -> function name

            # Use responses API for o4-mini model with reasoning summaries
            response = self.client.responses.create(
                model="o4-mini",  # Using reasoning-optimized model
                input=[
                    {"role": "user", "content": prompt}
                ],
                tools=[create_ticket_tool],
                tool_choice="auto",  # Allow model to choose when to use tools
                reasoning={"summary": "auto"},  # Enable reasoning summaries
                stream=True  # Enable streaming
            )

            for chunk in response:
                # DEBUG: Print every event type and relevant fields
                print("[DEBUG] Event type:", getattr(chunk, 'type', None))
                if hasattr(chunk, 'type'):
                    print("[DEBUG] Event:", chunk)
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'content') and chunk.delta.content:
                    print("[DEBUG] Content delta:", chunk.delta.content)
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'tool_calls') and chunk.delta.tool_calls:
                    print("[DEBUG] Tool calls:", chunk.delta.tool_calls)
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'reasoning') and chunk.delta.reasoning:
                    print("[DEBUG] Reasoning delta:", chunk.delta.reasoning)

                # Process message content chunks
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'content') and chunk.delta.content:
                    delta_content = chunk.delta.content
                    current_content += delta_content
                    if '.' in delta_content or '\n' in delta_content:
                        paragraphs = current_content[last_processed_length:].split('\n\n')
                        if len(paragraphs) > 1:
                            for para in paragraphs[:-1]:
                                if para.strip():
                                    self.add_reasoning_step(para.strip())
                            last_processed_length = len(current_content) - len(paragraphs[-1])

                # --- NEW: Properly accumulate and emit streamed reasoning summaries ---
                if hasattr(chunk, 'type'):
                    # Start of a new summary part (optional, can be used to reset accumulator)
                    if chunk.type == 'response.reasoning_summary_part.added':
                        item_id = getattr(chunk, 'item_id', None)
                        if item_id:
                            summary_accumulators[item_id] = []
                    # Streaming summary text delta
                    elif chunk.type == 'response.reasoning_summary_text.delta':
                        item_id = getattr(chunk, 'item_id', None)
                        delta_text = getattr(chunk, 'delta', None)
                        if item_id and delta_text is not None:
                            if item_id not in summary_accumulators:
                                summary_accumulators[item_id] = []
                            summary_accumulators[item_id].append(delta_text)
                    # End of summary: emit the full summary
                    elif chunk.type == 'response.reasoning_summary_text.done':
                        item_id = getattr(chunk, 'item_id', None)
                        text = getattr(chunk, 'text', None)
                        # Prefer the accumulated text if available
                        if item_id and item_id in summary_accumulators:
                            full_summary = ''.join(summary_accumulators[item_id])
                            if full_summary.strip():
                                self.add_reasoning_step(full_summary, step_type="summary")
                            del summary_accumulators[item_id]
                        elif text:
                            self.add_reasoning_step(text, step_type="summary")
                    # Handle when a reasoning step is completed
                    elif chunk.type == 'response.reasoning_step.done' and hasattr(chunk, 'step'):
                        if chunk.step:
                            self.add_reasoning_step(chunk.step, step_type="reasoning_step")

                # Check specifically for reasoning data in the delta field (legacy, keep for compatibility)
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'reasoning'):
                    reasoning = chunk.delta.reasoning
                    if hasattr(reasoning, 'summary'):
                        reasoning_summary = reasoning.summary
                        if reasoning_summary:
                            self.add_reasoning_step(reasoning_summary, step_type="summary")
                    if hasattr(reasoning, 'steps') and reasoning.steps:
                        for step in reasoning.steps:
                            if step:
                                self.add_reasoning_step(step, step_type="reasoning_step")

                # --- NEW: Function tool call streaming protocol ---
                if chunk.type == 'response.output_item.added':
                    # If this is a function call, store the function name for this item_id
                    item = getattr(chunk, 'item', None)
                    if item and getattr(item, 'type', None) == 'function_call':
                        item_id = getattr(item, 'id', None)
                        function_name = getattr(item, 'name', None)
                        if item_id and function_name:
                            function_call_names[item_id] = function_name
                            function_call_accumulators[item_id] = []
                elif chunk.type == 'response.function_call_arguments.delta':
                    item_id = getattr(chunk, 'item_id', None)
                    delta = getattr(chunk, 'delta', None)
                    if item_id and delta is not None:
                        if item_id not in function_call_accumulators:
                            function_call_accumulators[item_id] = []
                        function_call_accumulators[item_id].append(delta)
                elif chunk.type == 'response.function_call_arguments.done':
                    item_id = getattr(chunk, 'item_id', None)
                    arguments = getattr(chunk, 'arguments', None)
                    # Prefer the accumulated arguments if available
                    if item_id and item_id in function_call_accumulators:
                        full_args = ''.join(function_call_accumulators[item_id])
                        if not full_args.strip() and arguments:
                            full_args = arguments
                        try:
                            args = json.loads(full_args)
                            function_name = function_call_names.get(item_id, None)
                            if function_name == 'create_ticket':
                                if args.get('severity') == 'Critical' and args.get('count', 0) >= 5:
                                    self.identified_issues.append(args)
                                    self.add_reasoning_step(
                                        f"Identified critical issue in {args.get('service')}: {args.get('issue_type')} ({args.get('count')} occurrences)",
                                        step_type="issue"
                                    )
                        except Exception as e:
                            self.add_reasoning_step(f"Error processing function call: {str(e)}", step_type="error")
                        # Clean up
                        del function_call_accumulators[item_id]
                        if item_id in function_call_names:
                            del function_call_names[item_id]
                    elif arguments:
                        try:
                            args = json.loads(arguments)
                            function_name = function_call_names.get(item_id, None)
                            if function_name == 'create_ticket':
                                if args.get('severity') == 'Critical' and args.get('count', 0) >= 5:
                                    self.identified_issues.append(args)
                                    self.add_reasoning_step(
                                        f"Identified critical issue in {args.get('service')}: {args.get('issue_type')} ({args.get('count')} occurrences)",
                                        step_type="issue"
                                    )
                        except Exception as e:
                            self.add_reasoning_step(f"Error processing function call: {str(e)}", step_type="error")
                        if item_id in function_call_names:
                            del function_call_names[item_id]

            # Process any remaining content
            if current_content[last_processed_length:].strip():
                self.add_reasoning_step(current_content[last_processed_length:].strip())

            # --- NEW: After streaming, process any function calls or reasoning items in the final output ---
            for item in getattr(response, 'output', []):
                if getattr(item, 'type', None) == 'function_call' and getattr(item, 'name', None) == 'create_ticket':
                    try:
                        args = json.loads(item.arguments)
                        # Deduplicate: only add if not already present
                        if not any(
                            issue.get('issue_type') == args.get('issue_type') and
                            issue.get('service') == args.get('service') and
                            issue.get('first_seen') == args.get('first_seen') and
                            issue.get('last_seen') == args.get('last_seen')
                            for issue in self.identified_issues
                        ):
                            self.identified_issues.append(args)
                            self.add_reasoning_step(
                                f"Identified critical issue in {args.get('service')}: {args.get('issue_type')} ({args.get('count')} occurrences)",
                                step_type="issue"
                            )
                    except Exception as e:
                        print(f"[ERROR] Failed to process function call arguments: {e}")
                # Always add reasoning summaries as summary steps, using deduplication
                if getattr(item, 'type', None) == 'reasoning' and hasattr(item, 'summary'):
                    for summary in getattr(item, 'summary', []):
                        if hasattr(summary, 'text') and summary.text:
                            print(f"[DEBUG] Adding summary from final output: {summary.text}")
                            self.add_reasoning_step(summary.text, step_type="summary")

            # Return the identified issues
            return self.identified_issues
            
        except Exception as e:
            error_msg = f"Error analyzing logs with OpenAI: {e}"
            print(error_msg)
            self.add_reasoning_step(error_msg, step_type="error")
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
        self.add_reasoning_step("Using mock analysis mode due to API unavailability", step_type="info")
        
        # Filter for FATAL logs
        fatal_logs = logs_df[logs_df['level'] == 'FATAL']
        
        # Group by service and message
        grouped = fatal_logs.groupby(['service', 'message'])
        
        issues = []
        for (service, message), group in grouped:
            count = len(group)
            if count >= 5:  # Only include issues that occurred 5+ times
                timestamps = sorted(group['timestamp'].tolist())
                
                # Simulate reasoning steps with delays for streaming effect
                self.add_reasoning_step(f"Found {count} occurrences of FATAL error in {service}")
                time.sleep(0.5)  # Add delay to simulate streaming
                
                # Add a mock reasoning summary for demonstration
                if len(issues) == 0:  # Only add summary for the first issue
                    self.add_reasoning_step(
                        f"Summary: The logs show multiple FATAL errors in {service} related to '{message}'. This indicates a critical system issue.",
                        step_type="summary"
                    )
                    time.sleep(0.5)  # Add delay to simulate streaming
                
                self.add_reasoning_step(f"Analyzing message pattern: '{message}'")
                time.sleep(0.5)  # Add delay to simulate streaming
                
                self.add_reasoning_step(f"First occurrence at {timestamps[0]}, last at {timestamps[-1]}")
                time.sleep(0.5)  # Add delay to simulate streaming
                
                issue = {
                    "issue_type": "Critical Error",
                    "service": service,
                    "severity": "Critical",
                    "first_seen": timestamps[0],
                    "last_seen": timestamps[-1],
                    "count": count,
                    "description": f"Multiple occurrences of: {message}"
                }
                
                issues.append(issue)
                
                self.add_reasoning_step(f"Creating ticket for {service}: {count} occurrences of '{message}'", step_type="issue")
                time.sleep(0.5)  # Add delay to simulate streaming
        
        self.identified_issues = issues
        return issues
    
    def get_reasoning_steps(self):
        """Get the list of reasoning steps"""
        return self.reasoning_steps
    
    def get_identified_issues(self):
        """Get the list of identified issues"""
        return self.identified_issues 