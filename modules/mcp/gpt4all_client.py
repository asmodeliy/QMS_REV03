
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from gpt4all import GPT4All
    GPT4ALL_AVAILABLE = True
except ImportError:
    GPT4ALL_AVAILABLE = False
    print("Warning: gpt4all not installed. Install with: pip install gpt4all")

from modules.mcp.server import (
    list_projects,
    get_project_details,
    list_tasks,
    get_task_details,
    get_project_summary,
    list_users
)


class QMSAssistant:
    
    def __init__(
        self, 
        model_name: str = "gpt4all-falcon-newbpe-q4_0.gguf",
        model_path: Optional[str] = "/home/ronnie/llm/models"
    ):

        if not GPT4ALL_AVAILABLE:
            raise ImportError("gpt4all is not installed. Install with: pip install gpt4all")
        
        self.model_name = model_name
        
        if model_path is None:
            model_path = os.environ.get('GPT4ALL_MODEL_PATH')
        
        self.model_path = model_path
        self.model = None
        self.conversation_history = []
        
        self.tools = {
            "list_projects": {
                "function": list_projects,
                "description": "List all projects in the QMS system. Parameters: active_only (bool), limit (int)",
                "parameters": ["active_only", "limit"]
            },
            "get_project_details": {
                "function": get_project_details,
                "description": "Get detailed information about a specific project. Parameters: project_id (int)",
                "parameters": ["project_id"]
            },
            "list_tasks": {
                "function": list_tasks,
                "description": "List tasks in QMS. Parameters: project_id (int), status (str), limit (int)",
                "parameters": ["project_id", "status", "limit"]
            },
            "get_task_details": {
                "function": get_task_details,
                "description": "Get detailed task information. Parameters: task_id (int)",
                "parameters": ["task_id"]
            },
            "get_project_summary": {
                "function": get_project_summary,
                "description": "Get system-wide statistics. No parameters required.",
                "parameters": []
            },
            "list_users": {
                "function": list_users,
                "description": "List users in the system. Parameters: active_only (bool), limit (int)",
                "parameters": ["active_only", "limit"]
            }
        }
    
    def load_model(self):
        if self.model is None:
            print(f"Loading GPT4All model: {self.model_name}...")
            
            if self.model_path:
                print(f"Using model path: {self.model_path}")
                model_file = Path(self.model_path) / self.model_name
                if model_file.exists():
                    print(f"Found model file at: {model_file}")
                else:
                    print(f"Warning: Model file not found at {model_file}")
                    print("GPT4All will attempt to use the specified path...")
                
                self.model = GPT4All(self.model_name, model_path=self.model_path, allow_download=False)
            else:
                print("Using default GPT4All model cache directory")
                print("This may take a few minutes on first run as the model downloads...")
                self.model = GPT4All(self.model_name)
            
            print("Model loaded successfully!")
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt with available tools"""
        tools_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])
        
        return f"""You are a helpful QMS (Quality Management System) assistant. You have access to the following tools to query QMS data:

{tools_desc}

When a user asks about projects, tasks, or users, you should use the appropriate tool to get the information.

To use a tool, respond in this JSON format:
{{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}

After receiving tool results, provide a helpful, natural language response to the user.

Always be concise and helpful. Focus on answering the user's specific question."""
    
    def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:

        # Try to find JSON in the response
        try:
            # Look for JSON patterns
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                tool_call = json.loads(json_str)
                if 'tool' in tool_call:
                    return tool_call
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool_info = self.tools[tool_name]
        try:
            # Filter parameters to only include valid ones
            valid_params = {
                k: v for k, v in parameters.items()
                if k in tool_info['parameters']
            }
            result = tool_info['function'](**valid_params)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def chat(self, user_message: str, max_iterations: int = 3) -> str:

        if self.model is None:
            self.load_model()
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Create prompt with system instructions and conversation history
        prompt = self._create_system_prompt() + "\n\n"
        prompt += "Conversation:\n"
        for msg in self.conversation_history[-5:]:  # Last 5 messages
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "assistant: "
        
        # Generate response with potential tool usage
        iterations = 0
        final_response = ""
        
        while iterations < max_iterations:
            # Generate LLM response
            response = self.model.generate(prompt, max_tokens=500, temp=0.7)
            
            # Check if response contains a tool call
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                # Execute the tool
                tool_name = tool_call.get('tool')
                parameters = tool_call.get('parameters', {})
                
                print(f"[Tool Call] {tool_name}({parameters})")
                tool_result = self._execute_tool(tool_name, parameters)
                
                # Add tool result to prompt for next iteration
                prompt += f"{response}\n\nTool Result:\n{json.dumps(tool_result, indent=2)}\n\nassistant: "
                iterations += 1
            else:
                # No tool call, this is the final response
                final_response = response
                break
        
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": final_response})
        
        return final_response
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def ask_about_projects(self, query: str = "Show me all active projects") -> str:
        """Quick method to ask about projects"""
        return self.chat(query)
    
    def ask_about_tasks(self, query: str = "What tasks are in progress?") -> str:
        """Quick method to ask about tasks"""
        return self.chat(query)
    
    def ask_for_summary(self, query: str = "Give me a summary of the QMS system") -> str:
        """Quick method to ask for system summary"""
        return self.chat(query)


def simple_chat_loop():
    """
    Simple command-line chat interface
    """
    print("=" * 60)
    print("QMS Assistant - Local GPT4All Integration")
    print("=" * 60)
    print()
    print("Initializing assistant...")
    
    try:
        assistant = QMSAssistant()
        assistant.load_model()
        
        print("\nAssistant ready! Type 'quit' to exit, 'reset' to clear history.")
        print("\nExample questions:")
        print("  - Show me all active projects")
        print("  - What's the status of project ID 6?")
        print("  - List all in-progress tasks")
        print("  - Give me a system summary")
        print()
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_input.lower() == 'reset':
                assistant.reset_conversation()
                print("Conversation history cleared.")
                continue
            
            if not user_input:
                continue
            
            print("\nAssistant: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
    
    except ImportError as e:
        print(f"\nError: {e}")
        print("\nTo use GPT4All, install it with:")
        print("  pip install gpt4all")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    simple_chat_loop()
