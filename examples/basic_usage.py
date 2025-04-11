"""
Basic usage example of the Universal MCP Client.

This example demonstrates how to connect to an MCP server
and interact with it using either OpenAI or Anthropic models.
"""
import asyncio
import os
import sys

# Add parent directory to path to import from client/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.client import UniversalMCPClient, ModelProvider

async def main():
    """Run a basic example using the Universal MCP Client."""
    
    # Example of connecting to a server and running a chat with Anthropic's Claude
    print("=== Example 1: Using Anthropic's Claude ===")
    claude_client = UniversalMCPClient(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-sonnet"
    )
    
    # Connect to the server (replace with your server path)
    server_path = "../server/server.py"
    
    try:
        await claude_client.connect_to_server(server_path)
        
        # Example queries
        queries = [
            "What's the weather in New York?",
            "Tell me a joke about programming",
            "What's the current price of Bitcoin?"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            response = await claude_client.process_query(query)
            print(f"Response: {response}")
        
    finally:
        await claude_client.cleanup()
    
    print("\n\n")
    
    # Example of using OpenAI's GPT
    print("=== Example 2: Using OpenAI's GPT ===")
    gpt_client = UniversalMCPClient(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4"
    )
    
    try:
        await gpt_client.connect_to_server(server_path)
        
        # Example queries
        queries = [
            "Can you search for the latest news about AI?",
            "What's the definition of 'serendipity'?",
            "What time is it right now?"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            response = await gpt_client.process_query(query)
            print(f"Response: {response}")
        
    finally:
        await gpt_client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())