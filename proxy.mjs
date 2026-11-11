import http from "node:http";

const OPENCODE_URL = "http://127.0.0.1:4096";
const PORT = 4097;

async function httpPostJson(urlStr, data) {
  const res = await fetch(urlStr, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return await res.json();
}

async function httpDelete(urlStr) {
  try {
    await fetch(urlStr, { method: "DELETE" });
  } catch {}
}

async function createSession() {
  const data = await httpPostJson(`${OPENCODE_URL}/session`, {
    directory: ".",
  });
  return data.id;
}

async function deleteSession(sid) {
  if (!sid) return;
  await httpDelete(`${OPENCODE_URL}/session/${sid}`);
}

const FALLBACK_MODELS = [
  "deepseek-v4.1-flash-free",
  "glm-5.3-flash-free",
  "nemotron-3.5-lightning-free",
  "mimo-v2.6-flash-free",
];

async function queryOpenCode(prompt, preferredModel = "deepseek-v4.1-flash-free") {
  const modelsToTry = [preferredModel, ...FALLBACK_MODELS.filter((m) => m !== preferredModel)];
  let lastError = null;

  for (const model of modelsToTry) {
    let sid = null;
    try {
      sid = await createSession();
      const payload = {
        model: {
          providerID: "opencode",
          modelID: model,
        },
        parts: [
          {
            type: "text",
            text: prompt,
          },
        ],
      };

      const data = await httpPostJson(`${OPENCODE_URL}/session/${sid}/message`, payload);
      const textParts = [];
      const reasoningParts = [];

      for (const part of data.parts || []) {
        if (part.type === "text" && part.text) textParts.push(part.text);
        if (part.type === "reasoning" && part.text) reasoningParts.push(part.text);
      }

      if (textParts.length === 0 && reasoningParts.length === 0) {
        throw new Error(`Empty response from model ${model}`);
      }

      const tokens = data.info?.tokens || {};
      return {
        model,
        content: textParts.join("\n").trim(),
        reasoning: reasoningParts.join("\n").trim(),
        promptTokens: tokens.input || 0,
        completionTokens: tokens.output || 0,
        totalTokens: tokens.total || 0,
      };
    } catch (err) {
      lastError = err;
      console.warn(`Model ${model} failed: ${err.message}. Trying next candidate...`);
    } finally {
      if (sid) await deleteSession(sid);
    }
  }

  throw lastError || new Error("All free AI models exhausted");
}

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "*");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`);

  if (url.pathname === "/health" || url.pathname === "/v1/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", backend: OPENCODE_URL }));
    return;
  }

  if (url.pathname === "/v1/models") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        data: [
          { id: "deepseek-v4.1-flash-free", object: "model" },
          { id: "nemotron-3.5-super-vl-free", object: "model" },
          { id: "glm-5.3-flash-free", object: "model" },
          { id: "gpt-4o", object: "model" },
        ],
      })
    );
    return;
  }

  if (url.pathname === "/v1/chat/completions" && req.method === "POST") {
    let bodyText = "";
    for await (const chunk of req) {
      bodyText += chunk;
    }

    try {
      const body = JSON.parse(bodyText);
      const isStream = Boolean(body.stream);
      const targetModel = body.model || "nemotron-3.5-lightning-free";

      // Convert messages to prompt string
      const promptLines = [];
      for (const m of body.messages || []) {
        const role = m.role || "user";
        let content = m.content;
        if (Array.isArray(content)) {
          content = content
            .filter((p) => p.type === "text")
            .map((p) => p.text)
            .join(" ");
        }
        promptLines.push(`${role.toUpperCase()}:\n${content || ""}`);
      }
      const fullPrompt = promptLines.join("\n\n");

      const result = await queryOpenCode(fullPrompt, targetModel);
      const reqId = `chatcmpl-${Date.now()}`;

      if (!isStream) {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            id: reqId,
            object: "chat.completion",
            created: Math.floor(Date.now() / 1000),
            model: targetModel,
            choices: [
              {
                index: 0,
                message: {
                  role: "assistant",
                  content: result.content,
                },
                finish_reason: "stop",
              },
            ],
            usage: {
              prompt_tokens: result.promptTokens,
              completion_tokens: result.completionTokens,
              total_tokens: result.totalTokens,
            },
          })
        );
      } else {
        res.writeHead(200, {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        });

        // 1. Role delta
        res.write(
          `data: ${JSON.stringify({
            id: reqId,
            object: "chat.completion.chunk",
            created: Math.floor(Date.now() / 1000),
            model: targetModel,
            choices: [{ index: 0, delta: { role: "assistant" } }],
          })}\n\n`
        );

        // 2. Content chunks
        const text = result.content;
        const chunkSize = 20;
        for (let i = 0; i < text.length; i += chunkSize) {
          const slice = text.slice(i, i + chunkSize);
          res.write(
            `data: ${JSON.stringify({
              id: reqId,
              object: "chat.completion.chunk",
              created: Math.floor(Date.now() / 1000),
              model: targetModel,
              choices: [{ index: 0, delta: { content: slice } }],
            })}\n\n`
          );
        }

        // 3. Stop finish chunk
        res.write(
          `data: ${JSON.stringify({
            id: reqId,
            object: "chat.completion.chunk",
            created: Math.floor(Date.now() / 1000),
            model: targetModel,
            choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
            usage: {
              prompt_tokens: result.promptTokens,
              completion_tokens: result.completionTokens,
              total_tokens: result.totalTokens,
            },
          })}\n\n`
        );
        res.write("data: [DONE]\n\n");
        res.end();
      }
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: { message: err.message } }));
    }
    return;
  }

  res.writeHead(404);
  res.end();
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Free AI Gateway listening on http://127.0.0.1:${PORT}`);
});
