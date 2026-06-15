const DEFAULT_API_BASE = "http://localhost:8000";
const API_BASE_KEY = "lbcmp_api_base";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "LBCPC_ANALYZE") {
    return false;
  }

  analyze(message.payload)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => {
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : "Backend local indisponible",
      });
    });

  return true;
});

async function analyze(payload) {
  const apiBase = await getApiBase();
  const response = await fetch(`${apiBase}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Backend indisponible (${response.status})`);
  }

  return response.json();
}

function getApiBase() {
  return new Promise((resolve) => {
    chrome.storage.local.get({ [API_BASE_KEY]: DEFAULT_API_BASE }, (data) => {
      resolve(String(data[API_BASE_KEY] || DEFAULT_API_BASE).replace(/\/+$/, ""));
    });
  });
}
