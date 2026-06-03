const { onRequest } = require("firebase-functions/v2/https");
const { defineString } = require("firebase-functions/params");
const { initializeApp, getApps } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");

const deepseekApiKeyParam = defineString("DEEPSEEK_API_KEY");
const DEEPSEEK_URL = "https://api.deepseek.com/chat/completions";
const ALLOWED_MODELS = new Set(["deepseek-v4-flash", "deepseek-v4-pro"]);
const MAX_MESSAGES = 12;
const MAX_TOTAL_CHARS = 48000;

const FIRESTORE_KEY_PATHS = [
  "config/deepseek",
  "settings/deepseek",
  "config/api",
  "settings/api",
];

function ensureAdmin() {
  if (!getApps().length) initializeApp();
}

function setCors(req, res) {
  const origin = req.get("Origin");
  if (origin) {
    res.set("Access-Control-Allow-Origin", origin);
    res.set("Vary", "Origin");
  }
  res.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.set("Access-Control-Allow-Headers", "Content-Type");
}

function validateMessages(messages) {
  if (!Array.isArray(messages) || messages.length === 0 || messages.length > MAX_MESSAGES) {
    return "messages must be a non-empty array (max 12 items)";
  }
  let total = 0;
  for (const m of messages) {
    if (!m || typeof m !== "object") return "invalid message item";
    if (!["system", "user", "assistant"].includes(m.role)) return "invalid message role";
    if (typeof m.content !== "string" || !m.content.trim()) return "invalid message content";
    total += m.content.length;
    if (total > MAX_TOTAL_CHARS) return "messages too long";
  }
  return null;
}

function pickKeyFromData(data) {
  if (!data || typeof data !== "object") return "";
  return (
    data.apiKey ||
    data.api_key ||
    data.key ||
    data.DEEPSEEK_API_KEY ||
    data.deepseekApiKey ||
    ""
  ).trim();
}

async function resolveApiKey() {
  const fromParam = (deepseekApiKeyParam.value() || "").trim();
  if (fromParam) return fromParam;

  ensureAdmin();
  const db = getFirestore();
  for (const path of FIRESTORE_KEY_PATHS) {
    try {
      const snap = await db.doc(path).get();
      if (!snap.exists) continue;
      const key = pickKeyFromData(snap.data());
      if (key) return key;
    } catch (e) {
      console.warn("Firestore key lookup failed for", path, e.message);
    }
  }
  return "";
}

exports.chat = onRequest(
  {
    region: "asia-east1",
    timeoutSeconds: 120,
    memory: "256MiB",
    maxInstances: 20,
  },
  async (req, res) => {
    setCors(req, res);
    if (req.method === "OPTIONS") {
      res.status(204).send("");
      return;
    }
    if (req.method !== "POST") {
      res.status(405).json({ error: "Method not allowed" });
      return;
    }

    const model = req.body?.model || "deepseek-v4-flash";
    const messages = req.body?.messages;
    if (!ALLOWED_MODELS.has(model)) {
      res.status(400).json({ error: "Unsupported model" });
      return;
    }
    const msgErr = validateMessages(messages);
    if (msgErr) {
      res.status(400).json({ error: msgErr });
      return;
    }

    const apiKey = await resolveApiKey();
    if (!apiKey) {
      res.status(500).json({
        error: "DEEPSEEK_API_KEY not configured. Set functions/.env or Firestore config/deepseek.",
      });
      return;
    }

    try {
      const upstream = await fetch(DEEPSEEK_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages,
          stream: true,
          temperature: 0.3,
          max_tokens: 2048,
          thinking: { type: "disabled" },
        }),
      });

      if (!upstream.ok) {
        const errText = await upstream.text();
        let message = `DeepSeek API error ${upstream.status}`;
        try {
          const parsed = JSON.parse(errText);
          if (parsed?.error?.message) message = parsed.error.message;
        } catch (_) {
          if (errText) message = errText.slice(0, 500);
        }
        res.status(upstream.status).json({ error: message });
        return;
      }

      res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
      res.setHeader("Cache-Control", "no-cache, no-transform");
      res.setHeader("Connection", "keep-alive");
      res.setHeader("X-Accel-Buffering", "no");
      if (typeof res.flushHeaders === "function") res.flushHeaders();

      const reader = upstream.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(decoder.decode(value, { stream: true }));
      }
      res.end();
    } catch (err) {
      console.error("chat proxy error", err);
      if (!res.headersSent) {
        res.status(500).json({ error: "Chat proxy failed" });
      } else {
        res.end();
      }
    }
  },
);