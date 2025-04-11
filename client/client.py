"""
Universal MCP Client that supports multiple LLM providers.

This client can connect to any MCP server and interact with it using
either Claude (Anthropic) or GPT (OpenAI) models.
"""
import asyncio
import json
import os
import sys
import logging
from typing import Optional, Dict, Any, List, Tuple, Literal, Union
from enum import Enum
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import LLM providers
from anthropic import Anthropic
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("universal-mcp")

# Load environment variables
load_dotenv()

# Define model providers as an enum
class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

# Define available models
ANTHROPIC_MODELS = {
    "claude-3-opus": "claude-3-opus-latest",
    "claude-3-sonnet": "claude-3-7-sonnet-latest",
    "claude-3-haiku": "claude-3-5-haiku-latest",
}

OPENAI_MODELS = {
    "gpt-4-turbo": "gpt-4-turbo",
    "gpt-4": "gpt-4o",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
}

class UniversalMCPClient:
    """Universal MCP client supporting multiple LLM providers."""
    
    def __init__(self, 
                 provider: ModelProvider = ModelProvider.ANTHROPIC,
                 model_name: Optional[str] = None):
        """
        Initialize the Universal MCP client.
        
        Args:
            provider: LLM provider (anthropic or openai)
            model_name: Specific model name (if None, uses default for provider)
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._server_path = None
        
        # Set provider and model
        self.provider = provider
        self.model_name = model_name
        
        # Initialize LLM clients based on provider
        if provider == ModelProvider.ANTHROPIC:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment or .env file")
            
            self.anthropic = Anthropic(api_key=api_key)
            
            # Set default model if none provided
            if not self.model_name:
                self.model_name = "claude-3-sonnet"
            
            # Validate and map model name
            if self.model_name in ANTHROPIC_MODELS:
                self.full_model_name = ANTHROPIC_MODELS[self.model_name]
            else:
                self.full_model_name = self.model_name  # Use as-is
            
            # Initialize OpenAI to None
            self.openai = None
            
        elif provider == ModelProvider.OPENAI:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment or .env file")
            
            self.openai = OpenAI(api_key=api_key)
            
            # Set default model if none provided
            if not self.model_name:
                self.model_name = "gpt-4-turbo"
            
            # Validate and map model name
            if self.model_name in OPENAI_MODELS:
                self.full_model_name = OPENAI_MODELS[self.model_name]
            else:
                self.full_model_name = self.model_name  # Use as-is
            
            # Initialize Anthropic to None
            self.anthropic = None
            
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Initialized client with {provider} using model {self.full_model_name}")

    async def connect_to_server(self, server_script_path: str):
        """
        Connect to an MCP server.
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        # Store the server path for reconnection
        self._server_path = server_script_path
        
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        logger.info(f"Connecting to server: {server_script_path}")
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"Connected to server with tools: {[tool.name for tool in tools]}")
        
        return tools

    async def process_query(self, query: str) -> str:
        """
        Process a query using the configured LLM and available tools.
        
        Args:
            query: User query
            
        Returns:
            Response from LLM
        """
        if not self.session:
            raise ValueError("Not connected to a server. Call connect_to_server() first.")
        
        logger.info(f"Processing query: {query}")
        
        # Get available tools from the server
        tool_response = await self.session.list_tools()
        
        if self.provider == ModelProvider.ANTHROPIC:
            return await self._process_anthropic_query(query, tool_response.tools)
        else:  # OPENAI
            return await self._process_openai_query(query, tool_response.tools)

    async def _process_anthropic_query(self, query: str, tools: List[Any]) -> str:
        """Process query using Anthropic's Claude."""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # Format tools for Anthropic API
        available_tools = [{
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema
        } for tool in tools]

        # Initial Claude API call
        try:
            response = self.anthropic.messages.create(
                model=self.full_model_name,
                max_tokens=1000,
                messages=messages,
                tools=available_tools
            )
        except Exception as e:
            logger.error(f"Error in Anthropic API call: {str(e)}")
            raise

        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                try:
                    logger.info(f"Calling tool {tool_name} with args {tool_args}")
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_result_text = "\n".join(c.text for c in result.content if hasattr(c, 'text'))
                    final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                    final_text.append(f"[Tool result: {tool_result_text}]")
                except Exception as e:
                    logger.error(f"Error calling tool {tool_name}: {str(e)}")
                    final_text.append(f"[Error calling tool {tool_name}: {str(e)}]")
                    continue

                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": tool_result_text
                        }
                    ]
                })

                # Get next response from Claude
                try:
                    response = self.anthropic.messages.create(
                        model=self.full_model_name,
                        max_tokens=1000,
                        messages=messages,
                        tools=available_tools
                    )
                    
                    if response.content and response.content[0].type == 'text':
                        final_text.append(response.content[0].text)
                except Exception as e:
                    logger.error(f"Error in follow-up Anthropic API call: {str(e)}")
                    final_text.append(f"[Error getting response after tool call: {str(e)}]")

        return "\n".join(final_text)

    async def _process_openai_query(self, query: str, tools: List[Any]) -> str:
        """Process query using OpenAI's GPT."""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # Format tools for OpenAI API
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema
            }
        } for tool in tools]

        # Initial OpenAI API call
        try:
            response = self.openai.chat.completions.create(
                model=self.full_model_name,
                messages=messages,
                tools=available_tools,
                max_tokens=1000
            )
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {str(e)}")
            raise

        # Process response and handle tool calls
        final_text = []

        # Handle the message and any tool calls
        message = response.choices[0].message
        content = message.content or ""
        if content:
            final_text.append(content)
        
        # Process tool calls if present
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    # Parse the JSON arguments
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    logger.error(f"Failed to parse arguments for {tool_name}: {tool_call.function.arguments}")
                    final_text.append(f"[Error: Could not parse arguments for {tool_name}]")
                    continue
                
                # Execute tool call
                try:
                    logger.info(f"Calling tool {tool_name} with args {tool_args}")
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_result_text = "\n".join(content.text for content in result.content if hasattr(content, 'text'))
                    final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                    final_text.append(f"[Tool result: {tool_result_text}]")
                except Exception as e:
                    logger.error(f"Error calling tool {tool_name}: {str(e)}")
                    final_text.append(f"[Error calling tool {tool_name}: {str(e)}]")
                    continue
                
                # Add assistant's message with the tool call
                messages.append({
                    "role": "assistant", 
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                    ]
                })
                
                # Add tool result back to the conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_text
                })
                
                # Get next response from OpenAI
                try:
                    response = self.openai.chat.completions.create(
                        model=self.full_model_name,
                        messages=messages,
                        max_tokens=1000
                    )
                    
                    if response.choices and hasattr(response.choices[0], 'message'):
                        final_text.append(response.choices[0].message.content or "")
                except Exception as e:
                    logger.error(f"Error in follow-up OpenAI API call: {str(e)}")
                    final_text.append(f"[Error getting response after tool call: {str(e)}]")

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop."""
        print("\nUniversal MCP Client Started!")
        print(f"Using {self.provider} with model {self.full_model_name}")
        print("\nType your queries or 'quit' to exit.")
        print("You can also switch models with 'use openai' or 'use anthropic',")
        print("or specify a model with 'use openai:gpt-4-turbo' or 'use anthropic:claude-3-opus'")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break
                    
                # Handle model switching commands
                if query.lower().startswith('use '):
                    parts = query[4:].strip().split(':')
                    provider_str = parts[0].strip().lower()
                    
                    # Check if provider is valid
                    if provider_str not in ['openai', 'anthropic']:
                        print(f"Unsupported provider: {provider_str}. Use 'openai' or 'anthropic'.")
                        continue
                    
                    new_provider = ModelProvider.OPENAI if provider_str == 'openai' else ModelProvider.ANTHROPIC
                    
                    # Check if model is specified
                    new_model = None
                    if len(parts) > 1:
                        new_model = parts[1].strip()
                    
                    # Check if we need to reinitialize
                    if new_provider != self.provider or (new_model and new_model != self.model_name):
                        try:
                            # Create a new client with the new provider/model
                            new_client = UniversalMCPClient(provider=new_provider, model_name=new_model)
                            # If initialization is successful, replace current client
                            self.provider = new_provider
                            self.model_name = new_model
                            
                            # Update full model name based on provider
                            if self.provider == ModelProvider.ANTHROPIC:
                                self.full_model_name = ANTHROPIC_MODELS.get(self.model_name, self.model_name)
                                self.anthropic = new_client.anthropic
                                self.openai = None
                            else:  # OPENAI
                                self.full_model_name = OPENAI_MODELS.get(self.model_name, self.model_name)
                                self.openai = new_client.openai
                                self.anthropic = None
                                
                            print(f"Switched to {self.provider} with model {self.full_model_name}")
                        except Exception as e:
                            print(f"Error switching model: {str(e)}")
                        continue
                
                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()

async def main():
    """Main entry point for the client."""
    # Handle command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Universal MCP Client")
    parser.add_argument("server_script", help="Path to the MCP server script (.py or .js)")
    parser.add_argument("--provider", "-p", type=str, choices=["anthropic", "openai"], 
                      default="anthropic", help="LLM provider (default: anthropic)")
    parser.add_argument("--model", "-m", type=str, help="Model name to use")
    
    args = parser.parse_args()
    
    provider = ModelProvider.ANTHROPIC if args.provider == "anthropic" else ModelProvider.OPENAI
    
    try:
        client = UniversalMCPClient(provider=provider, model_name=args.model)
        await client.connect_to_server(args.server_script)
        await client.chat_loop()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())