# ⚡ Free AI Gateway & Python SDK ($0.00 / No API Keys)

A drop-in **OpenAI-compatible HTTP proxy gateway** and standalone **Python library** powered by the local OpenCode daemon. Provides free access to state-of-the-art reasoning and vision models with **zero API keys, zero token fees, and zero account logins**.

---

## 🌟 Available Free Models

| Model ID | Provider | Type | Context | Cost |
| :--- | :--- | :--- | :--- | :--- |
| `deepseek-v4.1-flash-free` | DeepSeek | Reasoning, Code & General Chat | 128k | **$0.00** |
| `nemotron-3.5-super-vl-free` | NVIDIA | Multimodal & Vision-Language | 64k | **$0.00** |
| `opencode/free` | OpenCode | Default Alias | 128k | **$0.00** |

---

## 🚀 Quickstart

### Method 1: Start the OpenAI Proxy Server
Run the local gateway on port `4097`:
```bash
python -m free_ai serve --port 4097
```

Now **ANY** library, framework, or UI that speaks the OpenAI protocol can point to:
```
Base URL: http://127.0.0.1:4097/v1
API Key:  free (or any dummy string)
```

#### Python (`openai` SDK):
```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:4097/v1", api_key="free")

response = client.chat.completions.create(
    model="deepseek-v4.1-flash-free",
    messages=[
        {"role": "user", "content": "Explain async/await in Python with an example."}
    ],
)
print(response.choices[0].message.content)
```

#### Node.js / TypeScript (`openai` npm):
```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://127.0.0.1:4097/v1",
  apiKey: "free",
});

const response = await client.chat.completions.create({
  model: "deepseek-v4.1-flash-free",
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(response.choices[0].message.content);
```

#### cURL:
```bash
curl http://127.0.0.1:4097/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4.1-flash-free",
    "messages": [{"role": "user", "content": "Hi!"}]
  }'
```

---

### Method 2: Direct Python Library (No Server Needed)
Import `free_ai` directly in your code:

```python
import free_ai

# Simple one-liner
response = free_ai.chat("Summarize the benefits of microservices.")
print(response.content)

# Access DeepSeek's internal chain-of-thought
if response.reasoning:
    print("Reasoning:", response.reasoning)

# Real-time token streaming
for chunk in free_ai.stream("Write a short poem about coding"):
    print(chunk, end="", flush=True)
```

---

## 🛠️ Architecture

```
[ Your Future Project / OpenAI SDK / LangChain / cURL ]
                      │ (Standard OpenAI /v1 format)
                      ▼
         [ Free AI Gateway Proxy ] (Port 4097)
                      │ (FastAPI + JSON transformer)
                      ▼
        [ OpenCode Local Daemon ] (Port 4096)
                      │ (Auto-spawned if offline)
                      ▼
  [ Free Cloud Model Tier: deepseek-v4.1-flash-free ]
```

1. **Auto-Supervisor**: The gateway checks `GET http://127.0.0.1:4096/global/health`. If OpenCode is offline, it auto-spawns `opencode serve --port 4096` in the background silently.
2. **Reasoning Extraction**: DeepSeek's `part.type == "reasoning"` is extracted and mapped to `message.reasoning_content` (matching DeepSeek / OpenAI reasoning specs).
3. **CORS Enabled**: Call the gateway directly from your browser single-page applications without CORS issues.
