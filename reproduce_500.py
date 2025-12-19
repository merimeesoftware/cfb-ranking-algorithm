
import os
import sys
import traceback
from dotenv import load_dotenv

# Load env vars first
load_dotenv()

try:
    print("Importing app...")
    from app import calculate_rankings_logic
    
    print("Calling calculate_rankings_logic...")
    # Simulate request args
    class MockArgs:
        def get(self, key, default=None):
            return default

    # Run for 2024 Week 1
    data = calculate_rankings_logic(2024, 1, MockArgs())
    print("Success!")
    
except Exception:
    print("Caught exception:")
    traceback.print_exc()
