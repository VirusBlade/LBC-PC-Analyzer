(function () {
  const ROOT_ID = "lbc-pc-analyzer";
  const HISTORY_KEY = "lbcmp_history";
  const FAVORITES_KEY = "lbcmp_favorites";
  const MAX_HISTORY = 20;
  const MAX_SEARCH_BADGES = 12;
  const PC_LISTING_PATTERNS = [
    /\bmini\s*-?\s*pc\b/i,
    /\bmini\s*-?\s*ordinateur\b/i,
    /\bminipc\b/i,
    /\bpc\s+(?:gamer|gaming|fixe|bureau|de\s+bureau|custom|assemble|assembl[ée]|mont[ée])\b/i,
    /\bordinateur\s+(?:fixe|de\s+bureau|gamer|gaming)\b/i,
    /\b(?:tour|config|configuration)\s+(?:pc|gamer|gaming|fixe|compl[èe]te|complete)\b/i,
    /\b(?:nuc|optiplex|thinkcentre|prodesk|elitedesk|minisforum|beelink|geekom|gmktec|acemagic)\b/i,
  ];
  const PC_CONTEXT_PATTERNS = [
    /\b(?:ryzen|intel\s+core|i[3579][\s-]?\d{4,5}|n100|n150)\b/i,
    /\b(?:rtx|gtx|radeon\s+rx|rx\s*\d{4}|intel\s+arc)\b/i,
    /\b\d{1,3}\s*(?:go|gb)\s+(?:ram|ddr[345])\b/i,
    /\b(?:ssd|nvme|hdd)\b/i,
  ];
  const ACCESSORY_ONLY_PATTERNS = [
    /\b(?:clavier|souris|[ée]cran|moniteur|enceinte|haut[ -]?parleur|casque|webcam|micro|tapis)\b/i,
    /\b(?:chargeur|alimentation|cable|câble|adaptateur|hub|dock|station\s+d'accueil)\b/i,
    /\b(?:carte\s+m[èe]re|processeur|cpu|carte\s+graphique|gpu|barrette|ram|ssd|nvme|hdd|disque\s+dur)\s+(?:seul|seule|uniquement|occasion|neuf|neuve)?\b/i,
  ];
  const LAPTOP_PATTERNS = [
    /\b(?:pc|ordinateur)\s+portable\b/i,
    /\b(?:portable|laptop|notebook|ultrabook|chromebook|macbook)\b/i,
    /\b(?:thinkpad|ideapad|vivobook|zenbook|elitebook|probook|latitude|precision|inspiron|xps|surface\s+book|surface\s+laptop)\b/i,
  ];

  if (document.getElementById(ROOT_ID)) {
    return;
  }

  let currentItem = null;
  let lastSignature = "";
  let scanTimer = null;
  const scoredCards = new WeakSet();
  let activePanel = "history";
  let extensionContextAlive = true;

  const root = document.createElement("aside");
  root.id = ROOT_ID;
  root.hidden = true;
  root.innerHTML = `
    <div class="lbcmp-header">
      <strong>Analyse PC</strong>
      <span class="lbcmp-pill">Auto</span>
    </div>
    <div class="lbcmp-status">Detection de l'annonce...</div>
    <div class="lbcmp-result" hidden></div>
    <div class="lbcmp-actions" hidden>
      <button class="lbcmp-fav" type="button">Ajouter aux favoris</button>
    </div>
    <div class="lbcmp-tabs" hidden>
      <button class="is-active" data-panel="history" type="button">Historique</button>
      <button data-panel="favorites" type="button">Favoris</button>
    </div>
    <div class="lbcmp-list" hidden></div>
  `;
  document.documentElement.appendChild(root);

  const status = root.querySelector(".lbcmp-status");
  const resultBox = root.querySelector(".lbcmp-result");
  const actions = root.querySelector(".lbcmp-actions");
  const favoriteButton = root.querySelector(".lbcmp-fav");
  const tabs = root.querySelector(".lbcmp-tabs");
  const listBox = root.querySelector(".lbcmp-list");

  favoriteButton.addEventListener("click", toggleFavorite);
  tabs.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-panel]");
    if (!button) return;
    activePanel = button.dataset.panel;
    updateTabs();
    renderStoredList();
  });

  scheduleScan();

  const observer = new MutationObserver(scheduleScan);
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.addEventListener("popstate", scheduleScan);
  window.addEventListener("hashchange", scheduleScan);

  function scheduleScan() {
    if (!extensionContextAlive) return;
    clearTimeout(scanTimer);
    scanTimer = setTimeout(scanCurrentPage, 700);
  }

  async function scanCurrentPage() {
    if (!extensionContextAlive) {
      return;
    }

    if (!isAdPage()) {
      root.hidden = true;
      scanSearchResults();
      return;
    }

    const payload = extractListing();
    const pageText = clean(`${payload.title} ${payload.description} ${location.href}`);
    const signature = `${location.href}|${payload.title}|${payload.price}`;

    if (!looksLikeComputerListing(pageText)) {
      root.hidden = true;
      return;
    }

    root.hidden = false;
    tabs.hidden = false;
    listBox.hidden = false;
    renderStoredList();

    if (signature === lastSignature) {
      return;
    }
    lastSignature = signature;

    status.textContent = "Analyse locale en cours...";
    resultBox.hidden = true;
    actions.hidden = true;

    try {
      const data = await analyzePayload(payload);
      currentItem = buildStoredItem(payload, data);
      await upsertHistory(currentItem);
      renderResult(data);
      await updateFavoriteButton();
      renderStoredList();
      status.textContent = "Analyse auto terminee.";
      actions.hidden = false;
    } catch (error) {
      currentItem = null;
      status.textContent = "API non joignable.";
      resultBox.innerHTML = `<p>${escapeHtml(apiErrorMessage(error))}</p>`;
      resultBox.hidden = false;
      actions.hidden = true;
    }
  }

  async function analyzePayload(payload) {
    if (!isExtensionContextReady()) {
      throw new Error("Extension non disponible. Recharge l'extension Chrome.");
    }

    const response = await new Promise((resolve, reject) => {
      try {
        chrome.runtime.sendMessage({ type: "LBCPC_ANALYZE", payload }, (reply) => {
          const runtimeError = chrome.runtime.lastError;
          if (runtimeError) {
            reject(extensionError(runtimeError.message));
            return;
          }
          resolve(reply);
        });
      } catch (error) {
        if (isExtensionContextError(error)) {
          markExtensionContextInvalid();
        }
        reject(error);
      }
    });

    if (!response?.ok) {
      throw new Error(response?.error || "API indisponible");
    }

    return response.data;
  }

  function isExtensionContextReady() {
    try {
      return extensionContextAlive && Boolean(chrome?.runtime?.id && chrome?.runtime?.sendMessage && chrome?.storage?.local);
    } catch (_error) {
      markExtensionContextInvalid();
      return false;
    }
  }

  function extensionError(message) {
    const error = new Error(message || "Extension non disponible. Recharge l'extension Chrome.");
    if (isExtensionContextError(error)) {
      markExtensionContextInvalid();
    }
    return error;
  }

  function isExtensionContextError(error) {
    return /extension context invalidated|context invalidated|message port closed|receiving end does not exist/i.test(String(error?.message || error || ""));
  }

  function markExtensionContextInvalid() {
    if (!extensionContextAlive) return;
    extensionContextAlive = false;
    clearTimeout(scanTimer);
    observer.disconnect();
    status.textContent = "Extension rechargee. Recharge la page Leboncoin.";
    resultBox.innerHTML = "<p>Chrome a recharge l'extension. Recharge cette page pour reinjecter l'analyse.</p>";
    resultBox.hidden = false;
    actions.hidden = true;
  }

  function isAdPage() {
    return /\/(ad|offre)\//.test(location.pathname) && Boolean(document.querySelector('h1, [data-qa-id="adview_price"], [data-qa-id="adview_description_container"]'));
  }

  function scanSearchResults() {
    if (!isComputerCategoryPage()) {
      return;
    }

    const cards = findSearchCards().slice(0, MAX_SEARCH_BADGES);
    cards.forEach((card) => {
      if (scoredCards.has(card) || card.querySelector(".lbcmp-search-badge")) {
        return;
      }
      scoredCards.add(card);
      injectSearchBadge(card);
    });
  }

  function findSearchCards() {
    const links = Array.from(document.querySelectorAll('a[href*="/ad/"], a[href*="/offre/"]'));
    const cards = [];
    const seen = new Set();

    links.forEach((link) => {
      const card = findCardContainer(link);
      if (!card || seen.has(card) || clean(card.innerText).length < 20) {
        return;
      }
      seen.add(card);
      cards.push(card);
    });

    return cards;
  }

  function isComputerCategoryPage() {
    return /\/c\/ordinateurs(?:\/|$)/.test(location.pathname);
  }

  function findCardContainer(link) {
    const preferred = link.closest('article, li, [data-test-id*="ad"], [data-test-id*="listing"], [data-qa-id*="ad"], [data-qa-id*="listing"]');
    if (preferred) {
      return preferred;
    }

    let node = link;
    for (let depth = 0; depth < 4 && node.parentElement; depth += 1) {
      node = node.parentElement;
      const text = clean(node.innerText);
      if (/€|eur/i.test(text) && text.length >= 20 && text.length <= 1500) {
        return node;
      }
    }

    return link;
  }

  async function injectSearchBadge(card) {
    const badge = document.createElement("span");
    badge.className = "lbcmp-search-badge is-loading";
    badge.textContent = "...";
    badge.title = "Analyse PC en cours";

    const host = card;
    host.classList.add("lbcmp-search-host");
    host.appendChild(badge);

    try {
      const payload = extractCardListing(card);
      if (!looksLikeComputerListing(`${payload.title} ${payload.description}`)) {
        badge.remove();
        return;
      }
      const data = await analyzePayload(payload);
      badge.classList.remove("is-loading");
      badge.classList.add(scoreClass(data.score));
      badge.textContent = `${data.score}/100`;
      badge.title = buildTooltip(data);
      badge.dataset.tooltip = buildTooltip(data);
    } catch (_error) {
      badge.classList.remove("is-loading");
      badge.classList.add("is-error");
      badge.textContent = "OFF";
      badge.title = "API non joignable. Verifie la connexion ou l'URL API.";
      badge.dataset.tooltip = badge.title;
    }
  }

  function extractCardListing(card) {
    const text = clean(card.innerText);
    const title = clean(card.querySelector("h2, h3, [data-qa-id*=title], [data-test-id*=title]")?.textContent) || text.split("\n")[0] || text.slice(0, 120);
    const price = text.match(/\b\d[\d\s.,]{1,8}\s*(?:€|EUR|euros?)\b/i)?.[0] || "";
    const link = card.querySelector('a[href*="/ad/"], a[href*="/offre/"]');
    const url = link ? new URL(link.getAttribute("href"), location.origin).toString() : location.href;
    return { title, price, description: text.slice(0, 1200), url };
  }

  function scoreClass(score) {
    if (score >= 82) return "is-great";
    if (score >= 65) return "is-good";
    if (score >= 45) return "is-mid";
    return "is-bad";
  }

  function buildTooltip(data) {
    const ramLabel = data.ram_gb ? `${data.ram_gb} Go RAM${data.ram_type ? ` ${data.ram_type}` : ""}${data.ram_speed_mhz ? ` ${data.ram_speed_mhz}MHz` : ""}` : null;
    const cpuLabel = data.cpu ? `${data.cpu}${data.details?.cpu_year ? ` (${data.details.cpu_year})` : ""}` : null;
    const parts = [data.verdict, cpuLabel, data.gpu, ramLabel, data.storage_label, data.reason];
    if (data.details) {
      parts.push(formatScoreDetails(data.details));
    }
    return parts.filter(Boolean).join(" | ");
  }

  function formatScoreDetails(details) {
    const parts = [`CPU ${details.cpu_score}/100`];
    if (details.gpu_score !== undefined && details.gpu_score !== null && details.gpu_score > 0) {
      parts.push(`GPU ${details.gpu_score}/100`);
    }
    parts.push(`RAM ${details.ram_score}/100`, `Disque ${details.storage_score}/100`, `Prix ${details.price_score}/100`);
    return parts.join(" · ");
  }

  function formatComponentScore(label, score, source) {
    if (score === undefined || score === null) {
      return label;
    }
    const sourceLabel = sourceLabelOf(source);
    return `${label} · ${score}/100${sourceLabel ? ` (${sourceLabel})` : ""}`;
  }

  function sourceLabelOf(source) {
    return source === "learned" ? "appris" : source === "benchmark" ? "benchmark" : source === "manual" ? "manuel" : source === "fallback" ? "estime" : null;
  }

  function toneClass(score) {
    if (score === undefined || score === null) return "is-unknown";
    if (score >= 82) return "is-great";
    if (score >= 65) return "is-good";
    if (score >= 45) return "is-mid";
    return "is-bad";
  }

  function componentScoreHtml(kind, label, score, source, extraMeta) {
    if (!label) {
      return escapeHtml(kind === "gpu" ? "Aucun / inconnu" : "Inconnu");
    }
    const href = benchmarkUrl(kind, label);
    const scoreLabel = score === undefined || score === null ? "Score inconnu" : `${score}/100`;
    const benchmarkLink = href ? `<a class="lbcmp-benchmark-link" href="${escapeAttr(href)}" target="_blank" rel="noopener noreferrer">Bench</a>` : "";
    return `
      <div class="lbcmp-component">
        <div class="lbcmp-component-main">
          <span class="lbcmp-component-name">${escapeHtml(label)}</span>
          <span class="lbcmp-component-score ${toneClass(score)}">${escapeHtml(scoreLabel)}</span>
        </div>
        <div class="lbcmp-component-sub">
          ${extraMeta ? `<span>${escapeHtml(extraMeta)}</span>` : ""}
          ${benchmarkLink}
        </div>
      </div>
    `;
  }

  function metricHtml(value, score) {
    return `<span class="lbcmp-metric ${toneClass(score)}">${escapeHtml(value)}</span>`;
  }

  function benchmarkUrl(kind, label) {
    if (!label || /\bunknown\b/i.test(label)) {
      return null;
    }
    const query = encodeURIComponent(label);
    if (kind === "gpu") {
      return `https://www.videocardbenchmark.net/gpu.php?gpu=${query}`;
    }
    return `https://www.cpubenchmark.net/cpu_lookup.php?cpu=${query}`;
  }

  function looksLikeComputerListing(text) {
    const normalized = clean(text);
    if (LAPTOP_PATTERNS.some((pattern) => pattern.test(normalized))) {
      return false;
    }

    const hasPcSignal = PC_LISTING_PATTERNS.some((pattern) => pattern.test(normalized));
    const contextHits = PC_CONTEXT_PATTERNS.filter((pattern) => pattern.test(normalized)).length;

    if (hasPcSignal) {
      return true;
    }

    if (contextHits >= 3 && /\b(?:windows|wifi|bluetooth|tour|bo[iî]tier|alimentation|ventilo|ventilateur)\b/i.test(normalized)) {
      return true;
    }

    if (ACCESSORY_ONLY_PATTERNS.some((pattern) => pattern.test(normalized)) && contextHits < 3) {
      return false;
    }

    return false;
  }

  function extractListing() {
    const title =
      readMeta("og:title") ||
      document.querySelector("h1")?.textContent?.trim() ||
      document.title;

    const description =
      readMeta("og:description") ||
      document.querySelector('[data-qa-id="adview_description_container"]')?.textContent?.trim() ||
      document.querySelector("main")?.innerText?.slice(0, 6000) ||
      document.body.innerText.slice(0, 6000);

    return {
      title: clean(title),
      price: clean(findPriceText()),
      description: clean(description),
      url: location.href,
    };
  }

  function readMeta(property) {
    return document.querySelector(`meta[property="${property}"]`)?.content?.trim();
  }

  function findPriceText() {
    const candidates = [
      '[data-qa-id="adview_price"]',
      '[data-test-id="price"]',
      '[class*="price"]',
    ];

    for (const selector of candidates) {
      const text = document.querySelector(selector)?.textContent;
      if (text && /€|eur/i.test(text)) {
        return text;
      }
    }

    const bodyMatch = document.body.innerText.match(/\b\d[\d\s.,]{1,8}\s*(?:€|EUR|euros?)\b/i);
    return bodyMatch ? bodyMatch[0] : "";
  }

  function buildStoredItem(payload, data) {
    return {
      id: normalizeUrl(location.href),
      url: location.href,
      title: payload.title || data.model || "Annonce Leboncoin",
      price: data.price || payload.price || null,
      brand: data.brand || null,
      model: data.model || null,
      cpu: data.cpu || null,
      ram_gb: data.ram_gb || null,
      storage_label: data.storage_label || null,
      gpu: data.gpu || null,
      ram_type: data.ram_type || null,
      ram_speed_mhz: data.ram_speed_mhz || null,
      score: data.score,
      verdict: data.verdict,
      reason: data.reason,
      details: data.details || null,
      saved_at: new Date().toISOString(),
    };
  }

  async function upsertHistory(item) {
    const history = await loadList(HISTORY_KEY);
    const next = [item, ...history.filter((entry) => entry.id !== item.id)].slice(0, MAX_HISTORY);
    await saveList(HISTORY_KEY, next);
  }

  async function toggleFavorite() {
    if (!currentItem) return;
    const favorites = await loadList(FAVORITES_KEY);
    const exists = favorites.some((entry) => entry.id === currentItem.id);
    const next = exists
      ? favorites.filter((entry) => entry.id !== currentItem.id)
      : [{ ...currentItem, favorited_at: new Date().toISOString() }, ...favorites];
    await saveList(FAVORITES_KEY, next);
    await updateFavoriteButton();
    renderStoredList();
  }

  async function updateFavoriteButton() {
    if (!currentItem) return;
    const favorites = await loadList(FAVORITES_KEY);
    const exists = favorites.some((entry) => entry.id === currentItem.id);
    favoriteButton.textContent = exists ? "Retirer des favoris" : "Ajouter aux favoris";
    favoriteButton.classList.toggle("is-active", exists);
  }

  async function renderStoredList() {
    updateTabs();
    const key = activePanel === "favorites" ? FAVORITES_KEY : HISTORY_KEY;
    const items = await loadList(key);
    const emptyText = activePanel === "favorites" ? "Aucun favori pour le moment." : "Aucun historique pour le moment.";

    if (!items.length) {
      listBox.innerHTML = `<div class="lbcmp-empty">${emptyText}</div>`;
      return;
    }

    listBox.innerHTML = items
      .slice(0, 6)
      .map(
        (item) => `
          <a class="lbcmp-item" href="${escapeAttr(item.url)}">
            <span class="lbcmp-item-title">${escapeHtml(item.title)}</span>
            <span class="lbcmp-item-meta">${escapeHtml(formatMeta(item))}</span>
          </a>
        `,
      )
      .join("");
  }

  function updateTabs() {
    tabs.querySelectorAll("button[data-panel]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.panel === activePanel);
    });
  }

  function formatMeta(item) {
    const parts = [];
    if (item.score !== undefined && item.score !== null) parts.push(`${item.score}/100`);
    if (item.verdict) parts.push(item.verdict);
    if (item.cpu) parts.push(item.cpu);
    if (item.price) parts.push(`${item.price} €`);
    return parts.join(" · ");
  }

  function loadList(key) {
    return new Promise((resolve) => {
      if (!isExtensionContextReady()) {
        resolve([]);
        return;
      }

      try {
        chrome.storage.local.get({ [key]: [] }, (data) => {
          const runtimeError = chrome.runtime.lastError;
          if (runtimeError) {
            extensionError(runtimeError.message);
            resolve([]);
            return;
          }
          resolve(Array.isArray(data[key]) ? data[key] : []);
        });
      } catch (error) {
        if (isExtensionContextError(error)) {
          markExtensionContextInvalid();
        }
        resolve([]);
      }
    });
  }

  function saveList(key, value) {
    return new Promise((resolve) => {
      if (!isExtensionContextReady()) {
        resolve();
        return;
      }

      try {
        chrome.storage.local.set({ [key]: value }, () => {
          const runtimeError = chrome.runtime.lastError;
          if (runtimeError) {
            extensionError(runtimeError.message);
          }
          resolve();
        });
      } catch (error) {
        if (isExtensionContextError(error)) {
          markExtensionContextInvalid();
        }
        resolve();
      }
    });
  }

  function normalizeUrl(url) {
    try {
      const parsed = new URL(url);
      parsed.hash = "";
      parsed.search = "";
      return parsed.toString();
    } catch (_error) {
      return url;
    }
  }

  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function apiErrorMessage(error) {
    const details = error?.message ? ` (${error.message})` : "";
    return `API non joignable. Verifie la connexion ou l'URL configuree, puis recharge la page${details}.`;
  }

  function renderResult(data) {
    const rows = [
      { label: "Marque", value: data.brand || "Inconnue" },
      { label: "Modele", value: data.model || "Inconnu" },
      { label: "CPU", html: componentScoreHtml("cpu", data.cpu, data.details?.cpu_score, data.details?.cpu_score_source, data.details?.cpu_year ? `${data.details.cpu_year}` : null) },
      { label: "GPU", html: data.gpu ? componentScoreHtml("gpu", data.gpu, data.details?.gpu_score, data.details?.gpu_score_source) : escapeHtml("Aucun / inconnu") },
      { label: "RAM", html: metricHtml(data.ram_gb ? `${data.ram_gb} Go${data.ram_type ? ` ${data.ram_type}` : ""}${data.ram_speed_mhz ? ` ${data.ram_speed_mhz}MHz` : ""}` : "Inconnue", data.details?.ram_score) },
      { label: "Disque", html: metricHtml(data.storage_label || "Inconnu", data.details?.storage_score) },
      { label: "Prix", html: metricHtml(data.price ? `${data.price} €` : "Inconnu", data.details?.price_score) },
      { label: "Score", html: metricHtml(`${data.score}/100`, data.score) },
      { label: "Verdict", html: metricHtml(data.verdict, data.score) },
    ];

    resultBox.innerHTML = `
      <div class="lbcmp-score ${toneClass(data.score)}">${escapeHtml(data.score)}/100</div>
      <dl>
        ${rows
          .map((row) => `<div><dt>${escapeHtml(row.label)}</dt><dd>${row.html || escapeHtml(row.value)}</dd></div>`)
          .join("")}
      </dl>
      ${data.details ? `<div class="lbcmp-breakdown">${escapeHtml(formatScoreDetails(data.details))}</div>` : ""}
      <p>${escapeHtml(data.reason || "")}</p>
    `;
    resultBox.hidden = false;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replaceAll("`", "&#096;");
  }
})();
