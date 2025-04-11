# Universal MCP Client & Server

A powerful, production-ready implementation of the Model Context Protocol (MCP) that works with multiple LLM providers including OpenAI and Anthropic.

![MCP Demo](output/output.gif)

## Features

- **Universal MCP Client**: Supports both OpenAI and Anthropic models
- **Modern Web UI**: Beautiful Streamlit-based interface for easy interaction
- **Dynamic model switching**: Switch between models during a session
- **Feature-rich MCP Server**: Includes multiple useful tools with free API integrations
- **Professional implementation**: Follows best practices and production-ready code standards

## Available Tools

Our MCP server includes several useful tools powered by free APIs:

- **Weather information**: Get current weather conditions for any city
- **Cryptocurrency data**: Check prices of cryptocurrencies
- **News headlines**: Fetch top news by topic or country
- **Web search**: Search the web for information
- **Dictionary lookups**: Get definitions of words
- **Random jokes**: Fetch jokes by category
- **Current time**: Get the current time in different timezones

## Prerequisites

- Python 3.10 or higher
- API keys for the LLMs you want to use (OpenAI and/or Anthropic)
- Optional: Free API keys for enhanced tool functionality

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/affanrasheed/universal-mcp.git
   cd universal-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys (use `.env.example` as a template):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Running the Server Directly

If you prefer, you can start just the MCP server:

```bash
python server/server.py
```

The server will run in the foreground and handle incoming MCP connections.

## Running the Command-Line Client

Connect to the server using the Universal MCP command-line client:

```bash
python client/client.py server/server.py
```

### Command Line Options

The client supports several command line options:

```bash
python client/client.py server/server.py --provider openai --model gpt-4-turbo
```

- `--provider` or `-p`: LLM provider to use (`anthropic` or `openai`, default: `anthropic`)
- `--model` or `-m`: Specific model to use (depends on provider)

### Runtime Model Switching

While the client is running, you can switch between models by typing:

```
use openai
use anthropic
use openai:gpt-4-turbo
use anthropic:claude-3-opus
```

## Available Models

### Anthropic Models

- `claude-3-opus`
- `claude-3-sonnet`
- `claude-3-haiku`
- `claude-2`

### OpenAI Models

- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`

## Integration with Claude Desktop

You can also use this server with Claude Desktop by following these steps:

1. Install Claude Desktop from [claude.ai/download](https://claude.ai/download)
2. Create or edit the Claude Desktop configuration file:
   - On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - On Windows: `%APPDATA%\Claude\claude_desktop_config.json`

3. Add your MCP server to the configuration:
   ```json
   {
     "mcpServers": {
       "universal-mcp": {
         "command": "python",
         "args": [
           "/absolute/path/to/universal-mcp/server/server.py"
         ],
         "env": {
           "OPENWEATHER_API_KEY": "your_key_here",
           "NEWSAPI_KEY": "your_key_here",
           "SERPAPI_KEY": "your_key_here"
         }
       }
     }
   }
   ```

4. Restart Claude Desktop

## API Key Setup

### LLM API Keys

- **Anthropic API Key**: Get it from [console.anthropic.com](https://console.anthropic.com/)
- **OpenAI API Key**: Get it from [platform.openai.com](https://platform.openai.com/api-keys)

### Tool API Keys (Optional)

While all tools will work without API keys (returning placeholder data or error messages), for full functionality:

- **OpenWeatherMap API**: Free tier from [openweathermap.org](https://openweathermap.org/api)
- **NewsAPI**: Free tier from [newsapi.org](https://newsapi.org/)
- **SerpAPI**: Free tier from [serpapi.com](https://serpapi.com/)

## Project Structure

```
universal-mcp/
├── .env.example              # Example environment variables
├── .gitignore                # Git ignore file
├── LICENSE                   # MIT License
├── README.md                 # Main documentation
├── requirements.txt          # Python dependencies
├── setup.py                  # Package installation script
├── client/                   # Client implementation
│   ├── __init__.py           # Package initialization
│   ├── client.py             # Universal MCP client supporting multiple LLMs
├── server/                   # Server implementation
│   ├── __init__.py           # Package initialization
│   ├── server.py             # MCP server with various tools
└── examples/                 # Example code
    └── basic_usage.py        # Basic usage examples
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.