(function () {
  const API_URL = "http://localhost:8000/analyze";
  const ROOT_ID = "lbc-pc-analyzer";
  const HISTORY_KEY = "lbcmp_history";
  const FAVORITES_KEY = "lbcmp_favorites";
  const MAX_HISTORY = 20;
  const MAX_SEARCH_BADGES = 12;
  const COMPUTER_HINTS = [
    "ordinateur",
    "informatique",
    "mini pc",
    "minipc",
    "pc de bureau",
    "pc portable",
    "hardware",
    "processeur",
    "ryzen",
    "intel",
    "ssd",
    "ram",
  ];

  if (document.getElementById(ROOT_ID)) {
    return;
  }

  let currentItem = null;
  let lastSignature = "";
  let scanTimer = null;
  const scoredCards = new WeakSet();
  let activePanel = "history";

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
    clearTimeout(scanTimer);
    scanTimer = setTimeout(scanCurrentPage, 700);
  }

  async function scanCurrentPage() {
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
      status.textContent = "Backend local indisponible sur localhost:8000.";
      resultBox.innerHTML = `<p>${escapeHtml(error.message || "Lance le backend puis recharge la page.")}</p>`;
      resultBox.hidden = false;
      actions.hidden = true;
    }
  }

  async function analyzePayload(payload) {
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

  function isAdPage() {
    return /\/(ad|offre)\//.test(location.pathname) && Boolean(document.querySelector('h1, [data-qa-id="adview_price"], [data-qa-id="adview_description_container"]'));
  }

  function scanSearchResults() {
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
      badge.textContent = "API";
      badge.title = "Backend local indisponible sur localhost:8000";
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
    const parts = [data.verdict, data.cpu, data.gpu, ramLabel, data.storage_label, data.reason];
    if (data.details) {
      parts.push(formatScoreDetails(data.details));
    }
    return parts.filter(Boolean).join(" | ");
  }

  function formatScoreDetails(details) {
    return `CPU ${details.cpu_score}/100 · RAM ${details.ram_score}/100 · Disque ${details.storage_score}/100 · Prix ${details.price_score}/100`;
  }

  function looksLikeComputerListing(text) {
    const lower = text.toLowerCase();
    return COMPUTER_HINTS.some((hint) => lower.includes(hint));
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
      chrome.storage.local.get({ [key]: [] }, (data) => resolve(Array.isArray(data[key]) ? data[key] : []));
    });
  }

  function saveList(key, value) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [key]: value }, resolve);
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

  function renderResult(data) {
    const rows = [
      ["Marque", data.brand || "Inconnue"],
      ["Modele", data.model || "Inconnu"],
      ["CPU", data.cpu || "Inconnu"],
      ["GPU", data.gpu || "Aucun / inconnu"],
      ["RAM", data.ram_gb ? `${data.ram_gb} Go${data.ram_type ? ` ${data.ram_type}` : ""}${data.ram_speed_mhz ? ` ${data.ram_speed_mhz}MHz` : ""}` : "Inconnue"],
      ["Disque", data.storage_label || "Inconnu"],
      ["Score", `${data.score}/100`],
      ["Verdict", data.verdict],
    ];

    resultBox.innerHTML = `
      <div class="lbcmp-score">${escapeHtml(data.score)}/100</div>
      <dl>
        ${rows
          .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`)
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
