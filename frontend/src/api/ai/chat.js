export function getApiBaseUrl() {
  const configuredBase = import.meta.env.VITE_API_BASE_URL;
  const runtimeBase =
    configuredBase !== undefined
      ? configuredBase
      : import.meta.env.DEV
        ? "http://127.0.0.1:5000"
        : "";

  return runtimeBase.replace(/\/$/, "");
}

export function buildEndpoint(path) {
  const baseUrl = getApiBaseUrl();
  return baseUrl ? `${baseUrl}${path}` : path;
}

function getStoredAuthToken() {
  try {
    return localStorage.getItem("cs_token") || "";
  } catch {
    return "";
  }
}

function parseSseEvent(rawChunk) {
  const dataLines = rawChunk
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());

  if (dataLines.length === 0) {
    return null;
  }

  const payloadText = dataLines.join("\n");
  if (!payloadText) {
    return null;
  }

  return JSON.parse(payloadText);
}

function logAiStreamDebug(label, payload = {}) {
  const timestamp =
    typeof performance !== "undefined" && typeof performance.now === "function"
      ? performance.now().toFixed(1)
      : Date.now();
  console.info(`[CarbonSnap AI stream ${timestamp}ms] ${label}`, payload);
}

async function handleStreamResponse(endpoint, payload, handlers = {}, options = {}) {
  const headers = {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  };

  const authToken = options.token ?? getStoredAuthToken();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(buildEndpoint(endpoint), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    const fallbackError = new Error(`Streaming request failed with status ${response.status}`);
    try {
      const data = await response.json();
      throw new Error(data.message || fallbackError.message);
    } catch {
      throw fallbackError;
    }
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const rawChunk = buffer.slice(0, separatorIndex).trim();
      buffer = buffer.slice(separatorIndex + 2);

      if (rawChunk) {
        const event = parseSseEvent(rawChunk);
        if (event) {
          logAiStreamDebug("event received", {
            endpoint,
            type: event.type,
            stream_stage: event.stream_stage,
            stage: event.stage,
            contentLength: String(event.content || "").length,
            questionLength: String(event.data?.question || "").length,
            optionCount: Array.isArray(event.data?.options) ? event.data.options.length : undefined,
            event,
          });
          if (event.type === "meta") {
            handlers.onMeta?.(event);
          } else if (event.type === "stage_start") {
            handlers.onStageStart?.(event);
          } else if (event.type === "stage_payload") {
            handlers.onStagePayload?.(event);
          } else if (event.type === "awaiting_location") {
            handlers.onAwaitingLocation?.(event);
          } else if (event.type === "clarification") {
            if (handlers.onClarification) {
              await handlers.onClarification(event);
            }
          } else if (event.type === "nearby_results") {
            handlers.onNearbyResults?.(event);
          } else if (event.type === "delta") {
            if (handlers.onDelta) {
              await handlers.onDelta(event.content || "", event);
            }
          } else if (event.type === "done") {
            handlers.onDone?.(event);
          } else if (event.type === "error") {
            handlers.onError?.(event);
            throw new Error(event.message || "Unknown streaming error.");
          }
        }
      }

      separatorIndex = buffer.indexOf("\n\n");
    }
  }
}

export async function streamAiChat(payload, handlers = {}) {
  return handleStreamResponse("/api/ai/chat/stream", payload, handlers);
}

export async function streamRecyclingAnalysis(payload, handlers = {}) {
  return handleStreamResponse("/api/ai/analyze-image", payload, handlers);
}

export async function resumeRecyclingAnalysis(payload, handlers = {}) {
  return handleStreamResponse("/api/ai/chat/resume", payload, handlers);
}

export async function streamRecyclingAudit(payload, handlers = {}) {
  return handleStreamResponse("/api/ai/audit-recycling", payload, handlers, {
    token: getStoredAuthToken(),
  });
}

export async function submitLocationContext(payload) {
  const authToken = getStoredAuthToken();
  const headers = {
    "Content-Type": "application/json",
  };
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(buildEndpoint("/api/ai/location-context"), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok || data.code !== 0) {
    throw new Error(data.message || "Location context request failed.");
  }

  return data.data;
}
