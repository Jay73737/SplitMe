#!/usr/bin/env python3
"""
SplitMe - AI Audio Stem Separation Tool
Entry point for the application
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for SplitMe application"""
    try:
        # Import and start the UI
        from ui.main_window import main as start_ui
        start_ui()
    except ImportError as e:
        print(f"Error importing UI modules: {e}")
        print("Falling back to API server mode...")
        
        # Start API server as fallback
        try:
            import uvicorn
            from api.server import app
            
            print("🚀 Starting SplitMe API Server...")
            print("🌐 Open http://localhost:8000 in your browser")
            print("📱 Use the frontend app to connect to this server")
            
            uvicorn.run(app, host="0.0.0.0", port=8000)
        except ImportError as e:
            print(f"Error starting API server: {e}")
            print("Please install requirements: pip install -r requirements.txt")
            sys.exit(1)

if __name__ == "__main__":
    main()
    

