"""
Script to start the Universal MCP UI.

Example usage:
    python run_ui.py
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the Streamlit UI for Universal MCP."""
    # Get the absolute path to the UI app
    ui_path = os.path.join(Path(__file__).parent.absolute(), "ui", "app.py")
    
    
    # Ensure file exists
    if not os.path.exists(ui_path):
        print(f"Error: UI file not found at {ui_path}")
        sys.exit(1)
    
    # Run Streamlit
    try:
        print(f"Starting Universal MCP UI at {ui_path}...")
        subprocess.run(["streamlit", "run", str(ui_path)], check=True)
    except KeyboardInterrupt:
        print("\nShutting down UI...")
    except Exception as e:
        print(f"Error starting UI: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()