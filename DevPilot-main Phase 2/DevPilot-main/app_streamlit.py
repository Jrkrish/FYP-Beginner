import argparse
import subprocess
import sys
from dotenv import load_dotenv
import os
from src.dev_pilot.ui.streamlit_ui.streamlit_app import load_app

if __name__ == "__main__":
     # Load environment variables from a .env file (if present)
     load_dotenv()

     # Debug print to verify BACKEND_URL is loaded
     print("DEBUG >>> BACKEND_URL =", os.getenv("BACKEND_URL"))

     load_app()