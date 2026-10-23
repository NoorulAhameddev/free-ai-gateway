"""
Example: Real-time token streaming using free_ai.stream()
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import free_ai

print("Streaming poem response:\n")
for chunk in free_ai.stream("Write a short 4-line poem about deep space exploration."):
    print(chunk, end="", flush=True)
print("\n")
