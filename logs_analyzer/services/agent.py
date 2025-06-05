import os
from openai import OpenAI, APIError
from datetime import datetime
import time # Keep for mock analysis
import json
# Remove unused re, Optional, Callable, List, Dict, Any for now, will re-add as needed by full refactoring
from typing import Optional, Callable, List, Dict, Any

# --- Constants ---
# Prompt from the original analyze_logs method; this will be used by the refactored version
LOG_ANALYSIS_PROMPT_TEMPLATE_FROM_ANALYZE_LOGS = """Analyze these system logs to identify critical issues that require attention from oncall engineers.

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

# Default model configurations (can be overridden in __init__)
DEFAULT_MODEL_NAME = "o4-mini" # From original analyze_logs
# Standard chat model often used with tools, if o4-mini is specialized
CHAT_COMPLETIONS_MODEL = "gpt-4-1106-preview"
DEFAULT_TEMPERATURE = 0.2 # A common default
DEFAULT_MAX_TOKENS = 2000 # A common default

# --- Custom Exceptions ---
class AgentError(Exception):
    """Base class for errors in LogAnalysisAgent."""
class OpenAIClientError(AgentError):
    """Errors related to OpenAI API client or calls."""
class ToolProcessingError(AgentError):
    """Errors related to processing tool calls or their arguments."""


class LogAnalysisAgent:
    """
    Agent responsible for analyzing logs using OpenAI models, including handling
    streaming responses (if applicable with chosen API), reasoning steps,
    and tool calls (like creating tickets).
    """
    def __init__(self, openai_api_key: Optional[str] = None,
                 ticket_service: Optional[Any] = None, # Define a base class for TicketService if possible
                 model_name: str = CHAT_COMPLETIONS_MODEL): # Default to standard chat model
        """
        Initializes the LogAnalysisAgent.

        Args:
            openai_api_key (Optional[str]): OpenAI API key. If None, attempts to use
                                           OPENAI_API_KEY environment variable.
            ticket_service (Optional[Any]): An instance of a ticket service client.
            model_name (str): The OpenAI model to be used for analysis.
        """
        self.api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            print("Warning: OpenAI API key not provided. OpenAI related functionalities might fail.")
            # Initialize client anyway; OpenAI class handles missing key for some cases or raises error.
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = OpenAI(api_key=self.api_key)

        self.model_name = model_name
        self.reasoning_steps: List[Dict[str, Any]] = []
        self.ticket_service = ticket_service
        self.identified_issues: List[Dict[str, Any]] = []
        self.stream_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Tool definition for create_ticket, as used in original analyze_logs
        # This will be used if we adapt analyze_logs to use the chat completions tool pattern
        self.tools = [self._get_create_ticket_tool_definition()]


    def _get_create_ticket_tool_definition(self) -> Dict[str, Any]:
        """Returns the definition for the 'create_ticket' tool."""
        return {
            "type": "function",
            "function": { # Correctly nest 'function' key
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
                        "first_seen": { # Added based on original tool definition in analyze_logs
                            "type": "string",
                            "description": "Timestamp of first occurrence"
                        },
                        "last_seen": { # Added based on original tool definition in analyze_logs
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

    def add_reasoning_step(self, step: str, step_type: str = "standard"):
        print(f"[DEBUG] add_reasoning_step called: {step} ({step_type})")
        """
        Add a reasoning step with timestamp, avoiding duplicates by content and type.
        """
        # Basic deduplication based on exact content and type match
        # More sophisticated deduplication might be needed for similar but not identical steps.
        for existing_step in self.reasoning_steps:
            if existing_step["content"] == step and existing_step["type"] == step_type:
                # print(f"[DEBUG] Duplicate reasoning step skipped: {step}")
                return # Avoid returning self.reasoning_steps from here

        reasoning_step_data = {
            "timestamp": datetime.now().isoformat(),
            "content": step,
            "type": step_type
        }
        self.reasoning_steps.append(reasoning_step_data)
        if self.stream_callback:
            try:
                self.stream_callback(reasoning_step_data)
            except Exception as e_cb: # pylint: disable=broad-except
                print(f"Error in stream_callback: {e_cb}")
        # return self.reasoning_steps # Method primarily for side effect, return not usually needed by caller

    # --- Helper methods for the new analyze_logs structure ---
    def _append_message_to_history(self, messages: List[Dict[str, Any]], role: str,
                                   content: Optional[str] = None,
                                   tool_calls: Optional[List[Any]] = None,
                                   tool_call_id: Optional[str] = None,
                                   name: Optional[str] = None):
        """
        Appends a structured message to the conversation history.
        Ensures content is present if no tool_calls, as per OpenAI API requirements for some roles.
        """
        message: Dict[str, Any] = {"role": role}
        if content is not None:
            message["content"] = content

        if tool_calls:
            # Ensure tool_calls are in the correct dictionary format if they are Pydantic objects
            processed_tool_calls = []
            for tc in tool_calls:
                if hasattr(tc, 'model_dump'): # Check if it's a Pydantic model instance
                    processed_tool_calls.append(tc.model_dump(exclude_unset=True))
                elif isinstance(tc, dict):
                    processed_tool_calls.append(tc)
                else:
                    # Handle unexpected tool_call type, or raise error
                    print(f"Warning: Unexpected tool_call type: {type(tc)}")
                    processed_tool_calls.append(str(tc)) # Fallback
            message["tool_calls"] = processed_tool_calls
            # If there are tool_calls, content for 'assistant' role can be None or empty.
            # If content is None and role is 'assistant' with tool_calls, ensure content is not an empty string
            # if role == "assistant" and message.get("content") is None:
            #    message["content"] = "" # Or None, API handles None for content if tool_calls present
        elif role == "assistant" and content is None:
            # Assistant message must have content if there are no tool_calls
            message["content"] = "" # Or raise an error if this state is unexpected

        if tool_call_id: # For role 'tool'
            message["tool_call_id"] = tool_call_id
        if name: # For role 'tool', this is the function name
            message["name"] = name

        # Final check for 'tool' role: must have tool_call_id and content
        if role == "tool" and ("tool_call_id" not in message or "content" not in message):
            raise ValueError(f"Tool message is missing tool_call_id or content: {message}")

        messages.append(message)

    def _call_openai_api_with_tools(self, messages: List[Dict[str, Any]],
                                    tools: List[Dict[str, Any]],
                                    tool_choice: str = "auto") -> Dict[str, Any]:
        """
        Makes a call to the OpenAI Chat Completions API with tools.

        Args:
            messages: Conversation history.
            tools: List of tool definitions.
            tool_choice: OpenAI tool choice option.

        Returns:
            The assistant's response message as a dictionary.

        Raises:
            OpenAIClientError: If the API call fails.
        """
        api_args: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            # Add temperature, max_tokens from self if needed, e.g.
            # "temperature": self.temperature, (if self.temperature is defined)
            # "max_tokens": self.max_tokens, (if self.max_tokens is defined)
        }
        self.add_reasoning_step(f"Calling OpenAI API ({self.model_name}) with {len(messages)} messages and {len(tools)} tools.",
                                step_type="api_call")
        try:
            response = self.client.chat.completions.create(**api_args)
            response_message = response.choices[0].message
            # Convert Pydantic model to dict for consistent handling (role, content, tool_calls)
            return {
                "role": str(response_message.role), # Ensure role is string ("assistant")
                "content": response_message.content,
                "tool_calls": response_message.tool_calls # This will be a list of ChatCompletionMessageToolCall
            }
        except APIError as e:
            self.add_reasoning_step(f"OpenAI API Error: {e}", step_type="error")
            raise OpenAIClientError(f"OpenAI API Error: {e}") from e
        except Exception as e: # Catch other potential errors
            self.add_reasoning_step(f"Unexpected error during API call: {e}", step_type="error")
            raise OpenAIClientError(f"Unexpected error during API call: {e}") from e

    def _execute_tool_call_from_api(self, tool_name: str, tool_args_str: str) -> str:
        """
        Executes a tool based on its name and JSON string arguments from API.
        Returns tool output as a string.
        """
        self.add_reasoning_step(f"Attempting to execute tool: {tool_name} with args: {tool_args_str}",
                                step_type="tool_execution")
        try:
            tool_args = json.loads(tool_args_str)
        except json.JSONDecodeError as e:
            error_msg = f"Error: Invalid JSON arguments for tool {tool_name}: {e}. Args: {tool_args_str}"
            self.add_reasoning_step(error_msg, step_type="error")
            return error_msg

        # Simplified dispatcher for now, assuming 'create_ticket' is the primary tool from original code
        if tool_name == "create_ticket":
            # Validation for required fields should align with the tool's JSON schema
            required_fields = ["issue_type", "service", "severity", "count", "description"]
            missing = [rf for rf in required_fields if rf not in tool_args]
            if missing:
                return f"Error: Missing required arguments for create_ticket: {', '.join(missing)}"
            
            # Logic from original analyze_logs for processing 'create_ticket'
            if tool_args.get('severity') == 'Critical' and tool_args.get('count', 0) >= 5:
                # Deduplication logic from original analyze_logs
                is_duplicate = any(
                    issue.get('issue_type') == tool_args.get('issue_type') and
                    issue.get('service') == tool_args.get('service') and
                    issue.get('first_seen') == tool_args.get('first_seen') and # Assuming these are in args
                    issue.get('last_seen') == tool_args.get('last_seen')
                    for issue in self.identified_issues
                )
                if not is_duplicate:
                    self.identified_issues.append(tool_args) # Side effect: updates instance state
                    self.add_reasoning_step(
                        f"Identified critical issue (via tool call): {tool_args.get('service')} - {tool_args.get('issue_type')}",
                        step_type="issue"
                    )
                else:
                    self.add_reasoning_step(f"Duplicate critical issue identified, not re-adding: {tool_args.get('summary')}", step_type="info")


                if self.ticket_service:
                    try:
                        # The ticket_service might expect a different format or more/less fields
                        # This is a placeholder for the actual call.
                        # Original code directly appended `args` which might not be what `create_ticket` method expects.
                        # Assuming ticket_service.create_ticket can handle the `args` dictionary directly.
                        return self.ticket_service.create_ticket(tool_args)
                    except Exception as e_ticket:
                        error_msg = f"Error calling ticket service: {e_ticket}"
                        self.add_reasoning_step(error_msg, step_type="error")
                        return error_msg
                return f"Ticket created (simulated for tool call): {tool_args.get('summary')}"
            return f"Issue not critical or count < 5, ticket not created by tool: {tool_args.get('summary')}"
        else:
            error_msg = f"Error: Unknown tool name '{tool_name}'."
            self.add_reasoning_step(error_msg, step_type="error")
            return error_msg

    def analyze_logs(self, logs_df, stream_callback: Optional[Callable[[Dict], None]] = None):
        """
        Analyze log data using OpenAI to identify issues

        Args:
            logs_df (pandas.DataFrame): DataFrame containing log data.
                                        Note: Pylint flagged pandas as unused in the original agent.py.
                                        If logs_df is indeed a DataFrame, pandas import is needed.
                                        For now, assuming logs_text is passed directly or generated before this call.
            stream_callback (Optional[Callable[[Dict[str, Any]], None]]): Callback for streaming steps.

        Returns:
            List[Dict[str, Any]]: List of identified issues.
        """
        # For now, assume logs_df is actually logs_text or is converted to text before this method
        # If logs_df is a pandas DataFrame, ensure pandas is imported and used.
        # Let's rename logs_df to logs_text_content to reflect its assumed nature here.
        logs_text_content = logs_df # This needs to be string content.

        self.stream_callback = stream_callback

        if not self.api_key or not self.client: # If API key was missing, client might be None or unusable
            self.add_reasoning_step("API key not configured. Using mock analysis.", step_type="error")
            # Assuming logs_text_content can be passed to _mock_analysis or _mock_analysis is adapted
            # For this refactoring, I'll assume _mock_analysis can work without a DataFrame.
            # If it needs a DataFrame, the caller of analyze_logs must handle that.
            return self._mock_analysis(logs_text_content) # Pass the content

        try:
            self.reasoning_steps = []
            self.identified_issues = []
            self.add_reasoning_step("Starting log analysis process")

            # The original code converted logs_df.to_string(index=False)
            # Assuming logs_text_content is already this string.
            # self.add_reasoning_step(f"Analyzing {len(logs_df)} log entries") # This needs len of lines or structured data
            self.add_reasoning_step(f"Analyzing log text of length {len(logs_text_content)} characters.")

            create_ticket_tool = self._get_create_ticket_tool_definition()

            prompt = LOG_ANALYSIS_PROMPT_TEMPLATE.format(logs_text=logs_text_content)
            
            self.add_reasoning_step("Sending logs to OpenAI for analysis...")
            
            # Use streaming API for real-time updates (core logic to be refactored into helpers)
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
                reasoning={"summary": "detailed", "effort": "high"},  # Enable reasoning summaries
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