"""
Example: Using standard OpenAI SDK with the Free AI Gateway ($0.00 Cost)
Any project that uses `openai` can point to http://127.0.0.1:4097/v1 without changes!
"""

from openai import OpenAI

# Connect to the local gateway
client = OpenAI(
    base_url="http://127.0.0.1:4097/v1",
    api_key="free",  # Dummy key required by OpenAI client format
)

# 1. List available models
models = client.models.list()
print("Available Models:")
for m in models.data:
    print(f" - {m.id}")

# 2. Generate a completion with DeepSeek reasoning
print("\nAsking a question...")
response = client.chat.completions.create(
    model="deepseek-v4.1-flash-free",
    messages=[
        {"role": "system", "content": "You are a concise engineering assistant."},
        {"role": "user", "content": "Explain what WebAssembly is in exactly 2 bullet points."},
    ],
)

print("\nResponse:")
print(response.choices[0].message.content)
