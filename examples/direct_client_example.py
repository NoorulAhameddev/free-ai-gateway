"""
Example: Using the standalone free_ai Python client directly (No server needed)
"""

import sys
from pathlib import Path

# Add project root to path for direct import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import free_ai

print("Sending prompt directly to OpenCode bridge...")
resp = free_ai.chat(
    prompt="What are the top 3 principles of clean code architecture?",
    model="deepseek-v4.1-flash-free",
)

if resp.reasoning:
    print("\n--- Model Internal Reasoning ---")
    print(resp.reasoning[:300] + "...")
    print("--------------------------------\n")

print("--- Output ---")
print(resp.content)
print(f"\nStats: {resp.total_tokens} tokens in {resp.latency_seconds:.2f}s | Cost: ${resp.cost_usd:.4f}")
