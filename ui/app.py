"""
Streamlit UI for the Universal MCP Client.

This web interface provides a user-friendly way to interact with MCP servers
using either OpenAI or Anthropic models.
"""
import os
import sys
import asyncio
import threading
import queue
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from client.client import UniversalMCPClient, ModelProvider, ANTHROPIC_MODELS, OPENAI_MODELS

# Set page configuration
st.set_page_config(
    page_title="Universal MCP Client",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }
    .model-select {
        margin-bottom: 1.5rem !important;
    }
    .server-path {
        margin-bottom: 1rem !important;
    }
    .tools-header {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    .stTextInput>div>div>input {
        border-radius: 0.5rem !important;
    }
    .stButton>button {
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        position: relative;
    }
    .user-message {
        background-color: #e6f7ff;
        border-left: 4px solid #1890ff;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #52c41a;
    }
    .tool-message {
        background-color: #fffbe6;
        border-left: 4px solid #faad14;
        font-family: monospace;
    }
    .message-content {
        margin-left: 0.5rem;
    }
    .spinner {
        margin-top: 1rem;
        margin-bottom: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions for UI rendering
def render_chat_message(message: Dict[str, Any]) -> None:
    """Render a chat message with appropriate styling."""
    role = message.get("role", "")
    content = message.get("content", "")
    
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <div><strong>You:</strong></div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    elif role == "assistant":
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <div><strong>Assistant:</strong></div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    elif role == "tool":
        st.markdown(f"""
        <div class="chat-message tool-message">
            <div><strong>Tool Result:</strong></div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)

def initialize_session_state() -> None:
    """Initialize session state variables if they don't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "is_connected" not in st.session_state:
        st.session_state.is_connected = False
    
    if "client" not in st.session_state:
        st.session_state.client = None
    
    if "available_tools" not in st.session_state:
        st.session_state.available_tools = []
        
    if "processing" not in st.session_state:
        st.session_state.processing = False
        
    if "connection_error" not in st.session_state:
        st.session_state.connection_error = None

def connect_to_server(server_path: str, provider: str, model_name: str) -> None:
    """Connect to the MCP server (non-async version)."""
    try:
        # Set to processing while connecting
        st.session_state.processing = True
        
        # Convert provider string to enum
        provider_enum = ModelProvider.ANTHROPIC if provider == "anthropic" else ModelProvider.OPENAI
        
        # Create a new client instance
        client = UniversalMCPClient(provider=provider_enum, model_name=model_name)
        
        # Run the async connection in a new thread
        def run_async_connection():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Connect to the server
                tools = loop.run_until_complete(client.connect_to_server(server_path))
                
                # Update session state
                st.session_state.client = client
                st.session_state.is_connected = True
                st.session_state.available_tools = tools
                st.session_state.connection_error = None
                
                # Add the list of available tools as a system message
                tool_names = [tool.name for tool in tools]
                tool_message = {
                    "role": "assistant",
                    "content": f"Connected to server with tools: {', '.join(tool_names)}"
                }
                st.session_state.messages.append(tool_message)
                
            except Exception as e:
                st.session_state.connection_error = str(e)
                st.session_state.is_connected = False
                st.session_state.client = None
                st.session_state.available_tools = []
                
                # Add error message
                error_message = {
                    "role": "assistant",
                    "content": f"Error connecting to server: {str(e)}"
                }
                st.session_state.messages.append(error_message)
            finally:
                # Clear processing flag
                st.session_state.processing = False
                loop.close()
        
        # Start the thread
        connection_thread = threading.Thread(target=run_async_connection)
        connection_thread.daemon = True
        connection_thread.start()
        
    except Exception as e:
        # Update session state for unexpected errors
        st.session_state.processing = False
        st.session_state.is_connected = False
        st.session_state.client = None
        st.session_state.available_tools = []
        st.session_state.connection_error = str(e)
        
        # Add error message
        error_message = {
            "role": "assistant",
            "content": f"Unexpected error: {str(e)}"
        }
        st.session_state.messages.append(error_message)

def process_query(query: str) -> None:
    """Process a query using the MCP client (non-async version)."""
    try:
        # Add user message to chat history
        user_message = {"role": "user", "content": query}
        st.session_state.messages.append(user_message)
        
        # Set processing flag
        st.session_state.processing = True
        
        # Get the client
        client = st.session_state.client
        
        if not client:
            raise ValueError("Not connected to a server")
        
        # Process the query in a separate thread
        def run_async_query():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Process the query
                response = loop.run_until_complete(client.process_query(query))
                
                # Add assistant response to chat history
                assistant_message = {"role": "assistant", "content": response}
                st.session_state.messages.append(assistant_message)
                
            except Exception as e:
                # Add error message
                error_message = {"role": "assistant", "content": f"Error: {str(e)}"}
                st.session_state.messages.append(error_message)
            finally:
                # Clear processing flag
                st.session_state.processing = False
                loop.close()
        
        # Start the thread
        query_thread = threading.Thread(target=run_async_query)
        query_thread.daemon = True
        query_thread.start()
        
    except Exception as e:
        # Handle unexpected errors
        st.session_state.processing = False
        error_message = {"role": "assistant", "content": f"Unexpected error: {str(e)}"}
        st.session_state.messages.append(error_message)

def switch_model(provider: str, model_name: str) -> None:
    """Switch the active model (non-async version)."""
    try:
        # Set processing flag
        st.session_state.processing = True
        
        # Convert provider string to enum
        provider_enum = ModelProvider.ANTHROPIC if provider == "anthropic" else ModelProvider.OPENAI
        
        # Get the client and server path
        if not st.session_state.client or not hasattr(st.session_state.client, '_server_path'):
            raise ValueError("Not connected to a server")
            
        server_path = st.session_state.client._server_path
        
        # Run the model switch in a separate thread
        def run_async_switch():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Clean up the existing client
                if st.session_state.client:
                    loop.run_until_complete(st.session_state.client.cleanup())
                
                # Create a new client
                client = UniversalMCPClient(provider=provider_enum, model_name=model_name)
                
                # Connect to the server
                tools = loop.run_until_complete(client.connect_to_server(server_path))
                
                # Update session state
                st.session_state.client = client
                
                # Add message to chat history
                model_message = {
                    "role": "assistant",
                    "content": f"Switched to {provider} with model {model_name}"
                }
                st.session_state.messages.append(model_message)
                
            except Exception as e:
                # Add error message
                error_message = {
                    "role": "assistant",
                    "content": f"Error switching model: {str(e)}"
                }
                st.session_state.messages.append(error_message)
            finally:
                # Clear processing flag
                st.session_state.processing = False
                loop.close()
        
        # Start the thread
        switch_thread = threading.Thread(target=run_async_switch)
        switch_thread.daemon = True
        switch_thread.start()
        
    except Exception as e:
        # Handle unexpected errors
        st.session_state.processing = False
        error_message = {"role": "assistant", "content": f"Unexpected error: {str(e)}"}
        st.session_state.messages.append(error_message)

# Initialize session state
initialize_session_state()

# UI Layout
st.markdown('<h1 class="main-header">Universal MCP Client</h1>', unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.title("Configuration")
    
    # Server path input
    st.markdown('<div class="server-path">', unsafe_allow_html=True)
    server_path = st.text_input(
        "Server Path",
        value=os.path.join(Path(__file__).parent.parent.absolute(), "server", "server.py"),
        help="Path to the MCP server script (.py or .js)"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Model selection
    st.markdown('<div class="model-select">', unsafe_allow_html=True)
    provider_option = st.selectbox(
        "LLM Provider",
        options=["anthropic", "openai"],
        index=0,
        help="Select the LLM provider"
    )
    
    # Show model options based on provider
    if provider_option == "anthropic":
        model_name = st.selectbox(
            "Anthropic Model",
            options=list(ANTHROPIC_MODELS.keys()),
            index=list(ANTHROPIC_MODELS.keys()).index("claude-3-sonnet") if "claude-3-sonnet" in ANTHROPIC_MODELS else 0,
            help="Select the Anthropic model to use"
        )
    else:  # OpenAI
        model_name = st.selectbox(
            "OpenAI Model",
            options=list(OPENAI_MODELS.keys()),
            index=list(OPENAI_MODELS.keys()).index("gpt-4-turbo") if "gpt-4-turbo" in OPENAI_MODELS else 0,
            help="Select the OpenAI model to use"
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Connection status indicator
    if st.session_state.is_connected:
        st.success("Connected to server")
    elif st.session_state.connection_error:
        st.error(f"Connection failed: {st.session_state.connection_error}")
    
    # Connect button
    connect_button = st.button(
        "Connect to Server",
        disabled=st.session_state.processing,
        use_container_width=True
    )
    
    if connect_button:
        # Clear any previous connection error
        st.session_state.connection_error = None
        # Connect to server
        connect_to_server(server_path, provider_option, model_name)
    
    # Model switching (only if connected)
    if st.session_state.is_connected:
        st.markdown("---")
        st.subheader("Switch Model")
        
        switch_provider_option = st.selectbox(
            "Switch Provider",
            options=["anthropic", "openai"],
            index=0 if provider_option == "anthropic" else 1,
            key="switch_provider"
        )
        
        # Show model options based on provider
        if switch_provider_option == "anthropic":
            switch_model_name = st.selectbox(
                "Anthropic Model",
                options=list(ANTHROPIC_MODELS.keys()),
                index=list(ANTHROPIC_MODELS.keys()).index("claude-3-sonnet") if "claude-3-sonnet" in ANTHROPIC_MODELS else 0,
                key="switch_anthropic_model"
            )
        else:  # OpenAI
            switch_model_name = st.selectbox(
                "OpenAI Model",
                options=list(OPENAI_MODELS.keys()),
                index=list(OPENAI_MODELS.keys()).index("gpt-4-turbo") if "gpt-4-turbo" in OPENAI_MODELS else 0,
                key="switch_openai_model"
            )
        
        # Switch model button
        switch_button = st.button(
            "Switch Model",
            disabled=st.session_state.processing,
            use_container_width=True
        )
        
        if switch_button:
            # Switch model
            switch_model(switch_provider_option, switch_model_name)
    
    # Show available tools
    if st.session_state.is_connected and st.session_state.available_tools:
        st.markdown("---")
        st.markdown('<div class="tools-header">Available Tools:</div>', unsafe_allow_html=True)
        
        for tool in st.session_state.available_tools:
            with st.expander(tool.name):
                st.markdown(f"**Description:** {tool.description or 'No description provided'}")
                st.markdown("**Input Schema:**")
                st.json(tool.inputSchema)

# Main chat area
main_container = st.container()

with main_container:
    # Display chat history
    for message in st.session_state.messages:
        render_chat_message(message)
    
    # Show chat input only if connected
    if st.session_state.is_connected:
        with st.container():
            # Create two columns for input and button
            col1, col2 = st.columns([5, 1])
            
            with col1:
                user_input = st.text_input(
                    "Message",
                    key="user_input",
                    disabled=st.session_state.processing,
                    placeholder="Type your message here...",
                    label_visibility="collapsed"
                )
            
            with col2:
                send_button = st.button(
                    "Send",
                    key="send_button",
                    disabled=st.session_state.processing or not user_input,
                    use_container_width=True
                )
        
        # Process new message
        if send_button and user_input:
            # Process the query
            process_query(user_input)
            
            # Clear the input box (will happen on next rerun)
            st.session_state.user_input = ""
    else:
        st.info("Please connect to an MCP server using the sidebar options to start chatting.")

# Display processing indicator
if st.session_state.processing:
    with st.container():
        st.markdown("""
        <div class="spinner">
            <p>Processing your request...</p>
        </div>
        """, unsafe_allow_html=True)
        
# Force page refresh periodically during processing 
# This helps update the UI without relying on complex event callbacks
if st.session_state.processing:
    time.sleep(0.1)  # Small delay to avoid excessive refreshing
    st.rerun()