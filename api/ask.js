// Ask panel backend (Vercel function, POST /api/ask): sends the reader's question, with this tracker's data,
// to Google's Gemini API on the free tier and returns a short answer. The key lives only in Vercel's
// environment (GEMINI_API_KEY); without it the panel says the assistant is not connected.
"use strict";

const DATA = { reta: require("../reta_data.json"), cagri: require("../cagri_data.json") };
// 3.6 Flash answered in seconds at launch while 3.8 Flash was often overloaded or slow; the others are tried in turn
const MODELS = [process.env.GEMINI_MODEL || "gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"];
const LIMITS = { question: 600, turns: 6, turnText: 1500, perMinute: 8, wait: 15000 };

// English only: the Korean copies would double the tokens without adding facts
function english(o) {
  if (Array.isArray(o)) return o.map(english);
  if (o && typeof o === "object") {
    const keys = Object.keys(o);
    if (keys.length && keys.every((k) => k === "en" || k === "ko")) return o.en;
    return Object.fromEntries(keys.map((k) => [k, english(o[k])]));
  }
  return o;
}
const CONTEXT = Object.entries(DATA)
  .map(([key, d]) => `### ${d.meta.name.en} (${key}), data as of ${d.asOf}\n${JSON.stringify(english(d))}`)
  .join("\n\n");

const RULES = `You answer questions from readers of "Incretin LAI Radar", a tracker of companies developing
long-acting (monthly or longer) injectable versions of retatrutide (Lilly) and CagriSema (Novo Nordisk).
Readers are pharmaceutical formulation and business-development staff.

Rules:
- Answer from the tracker data below. For standard scientific, pharmacokinetic, patent or regulatory terms
  (for example Cmax, AUC, rBA, burst release, PTE, SPC) you may give the usual textbook definition.
- If the tracker does not hold the answer, say so plainly. Never guess, and never invent numbers, dates,
  companies, trial or patent numbers.
- Say where in the tracker the facts come from: the page (Competitors, Patents, the originator's timeline,
  PK data, News) and the card or row name.
- Reply in the language of the question (Korean or English).
- Keep it under 150 words. Plain text: short paragraphs or lines starting with "- ". No tables, no headings.
  Use **bold** sparingly for the key term or number.
- The data is the tracker's own JSON: "cards" are competitor programmes, "estate" the originator's patents,
  "plan" the originator's timeline, "pk" the PK page, "news" the news list. kind "figure" means read from a
  chart, "simulated" a model simulation, "calc" calculated by the tracker from published numbers.
- Never show JSON field names (like pk.judge or estate) to the reader. Name what they see instead: the page,
  the card or row name, and on the PK page the sections "How long the level holds" (chart and by-day table)
  and "Against the weekly product" (comparison with approved products).`;

// a rough per-instance limit; the free quota is the real ceiling, and running out only pauses the panel
const recent = new Map();
function tooMany(ip) {
  const now = Date.now(), list = (recent.get(ip) || []).filter((t) => now - t < 60000);
  list.push(now);
  recent.set(ip, list);
  return list.length > LIMITS.perMinute;
}

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") return send(res, 405, { error: "method" });
  // only this site's own pages may call it
  const origin = req.headers.origin;
  if (origin && new URL(origin).host !== req.headers.host) return send(res, 403, { error: "origin" });
  if (!process.env.GEMINI_API_KEY) return send(res, 503, { error: "not_configured" });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = null; } }
  const q = body && typeof body.q === "string" ? body.q.trim() : "";
  if (!q || q.length > LIMITS.question) return send(res, 400, { error: "question" });
  const ip = String(req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "").split(",")[0].trim();
  if (tooMany(ip)) return send(res, 429, { error: "busy" });

  const drug = DATA[body.drug] ? body.drug : "reta";
  const page = typeof body.page === "string" ? body.page.slice(0, 20) : "";
  const history = (Array.isArray(body.history) ? body.history : [])
    .filter((t) => t && (t.role === "user" || t.role === "model") && typeof t.text === "string")
    .slice(-LIMITS.turns)
    .map((t) => ({ role: t.role, parts: [{ text: t.text.slice(0, LIMITS.turnText) }] }));

  const payload = {
    systemInstruction: { parts: [{ text: `${RULES}\n\nThe reader is viewing the ${DATA[drug].meta.name.en} side${page ? `, ${page} page` : ""}.\n\n${CONTEXT}` }] },
    contents: [...history, { role: "user", parts: [{ text: q }] }],
    // short answers to look-up questions need little reasoning; low thinking keeps replies to seconds
    generationConfig: { maxOutputTokens: 2048, thinkingConfig: { thinkingLevel: "low" } },
  };
  let r = { status: 504 }, j = {}, model;
  for (model of MODELS) {
    try {
      r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": process.env.GEMINI_API_KEY },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(LIMITS.wait),
      });
      j = await r.json().catch(() => ({}));
    } catch (e) {
      // a model that has not answered in time is treated as overloaded
      r = { status: e.name === "TimeoutError" ? 504 : 502 };
      if (r.status === 502) return send(res, 502, { error: "unreachable" });
    }
    // overloaded, too slow, or this model's free allowance is used up: try the next model
    if (![429, 500, 503, 504].includes(r.status)) break;
  }
  if (r.status === 429) return send(res, 429, { error: "quota" });
  if ([500, 503, 504].includes(r.status)) return send(res, 503, { error: "overloaded" });
  if (!r.ok) {
    console.error("gemini", r.status, j && j.error && j.error.message);
    // Google's short status (e.g. NOT_FOUND, INVALID_ARGUMENT) tells a wrong model name from a bad key without exposing either
    return send(res, 502, { error: "failed", detail: `${r.status} ${(j && j.error && j.error.status) || ""}`.trim() });
  }
  if (j.promptFeedback && j.promptFeedback.blockReason) return send(res, 200, { error: "blocked" });
  const cand = (j.candidates || [])[0] || {};
  const answer = ((cand.content && cand.content.parts) || []).filter((p) => !p.thought && p.text).map((p) => p.text).join("").trim();
  if (!answer) return send(res, 200, { error: cand.finishReason === "MAX_TOKENS" ? "too_long" : "blocked" });
  return send(res, 200, { answer, model });
};
