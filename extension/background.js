const API_URL = "http://localhost:8000/analyze";

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
  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Backend indisponible (${response.status})`);
  }

  return response.json();
}
