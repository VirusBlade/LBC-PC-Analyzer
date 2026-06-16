type Env = { DB: D1Database };

type AnalyzeRequest = { title?: string; price?: string | number | null; description?: string; url?: string | null };
type ParsedListing = {
  brand: string | null; model: string | null; cpu: string | null; gpu: string | null;
  ram_gb: number | null; ram_type: string | null; ram_speed_mhz: number | null;
  storage_type: string | null; storage_gb: number | null; storage_label: string | null;
  price: number | null; raw: { title: string; description: string };
};

const CUSTOM_PC_BRAND = "PC Custom";
const BRANDS = ["Beelink", "Minisforum", "GMKtec", "Geekom", "Chuwi", "Lenovo", "HP", "Dell", "Shuttle", "NiPoGi", "Acemagic", "Ace Magician", "Intel", "MSI", "Schneider", "Asus", "Acer"];
const CPU_SCORES: Record<string, { score: number; cpu_mark?: number; single_thread?: number; tier?: string; year?: number }> = {
  "Ryzen 7 H255": { score: 98, tier: "high", year: 2025 }, "Ryzen 7 8745HS": { score: 98, tier: "high", year: 2024 }, "Ryzen 7 8700G": { score: 96, tier: "high", year: 2024 },
  "Ryzen 7 7735HS": { score: 92, tier: "high", year: 2023 }, "Ryzen 9 6900HX": { score: 91, tier: "high", year: 2022 }, "Ryzen 7 6800U": { score: 88, tier: "high", year: 2022 },
  "Ryzen 7 5800H": { score: 84, tier: "high", year: 2021 }, "Ryzen 7 5800U": { score: 79, cpu_mark: 18800, single_thread: 3050, tier: "good", year: 2021 },
  "Ryzen 7 5700U": { score: 76, tier: "good", year: 2021 }, "Ryzen 7 5700X": { score: 86, cpu_mark: 26700, single_thread: 3350, tier: "high", year: 2022 }, "Ryzen 5 5650GE": { score: 72, tier: "good", year: 2021 }, "Ryzen 5 7430U": { score: 70, tier: "good", year: 2024 },
  "Ryzen 5 5500U": { score: 66, tier: "good", year: 2021 }, "Ryzen 5 unknown": { score: 55, tier: "estimated" }, "Ryzen 7 unknown": { score: 65, tier: "estimated" },
  "Ryzen 9 unknown": { score: 75, tier: "estimated" }, "Intel i5-12400": { score: 82, tier: "good", year: 2022 }, "Intel i5-1250P": { score: 78, tier: "good", year: 2022 },
  "Intel i5-1235U": { score: 74, tier: "good", year: 2022 }, "Intel i5-1135G7": { score: 62, tier: "office", year: 2020 }, "Intel i7-6700HQ": { score: 54, tier: "old", year: 2015 },
  "Intel i5-9500": { score: 52, tier: "old", year: 2019 }, "Intel i5-7500": { score: 45, tier: "old", year: 2017 }, "Intel i5-8500T": { score: 43, tier: "old_low_power", year: 2018 },
  "Intel i3-10th gen": { score: 40, tier: "estimated", year: 2020 }, "Intel i5-10th gen": { score: 48, tier: "estimated", year: 2020 }, "Intel i7-10th gen": { score: 56, tier: "estimated", year: 2020 },
  "Intel i5-6500T": { score: 35, tier: "old_low_power", year: 2015 }, "Intel i3-7th gen": { score: 24, tier: "estimated_old", year: 2017 }, "Intel N150": { score: 34, tier: "low_power", year: 2025 },
  "Intel N100": { score: 30, tier: "low_power", year: 2023 }, "Intel N4000": { score: 12, tier: "avoid", year: 2017 }, "Intel G630": { score: 8, tier: "avoid", year: 2011 }, "AMD A10": { score: 15, tier: "avoid", year: 2012 }
};
const GPU_SCORES: Record<string, { score: number; tier: string }> = {
  "RTX 5090": { score: 100, tier: "extreme" }, "RTX 5080": { score: 98, tier: "extreme" }, "RTX 5070": { score: 92, tier: "high" }, "RTX 4070": { score: 82, tier: "high" },
  "RTX 4060": { score: 68, tier: "mid" }, "RTX 3090": { score: 86, tier: "high" }, "RTX 3080": { score: 80, tier: "high" }, "RTX 3070": { score: 70, tier: "mid" },
  "RTX 3060": { score: 58, tier: "mid" }, "GTX 1660 SUPER": { score: 38, tier: "entry" }, "GTX 1660": { score: 34, tier: "entry" }, "GTX 1650": { score: 24, tier: "old" }, "GTX 1060": { score: 22, tier: "old" },
  "RX 7900 XTX": { score: 90, tier: "high" }, "RX 7800 XT": { score: 78, tier: "high" }, "RX 7700 XT": { score: 70, tier: "mid" }, "RX 7600": { score: 55, tier: "mid" },
  "RX 6800 XT": { score: 76, tier: "high" }, "RX 6750 XT": { score: 66, tier: "mid" }, "RX 6700 XT": { score: 62, tier: "mid" }, "RX 6600": { score: 42, tier: "entry" }, "RX 5700 XT": { score: 46, tier: "entry" }, "Radeon 780M": { score: 26, tier: "integrated" },
  "Intel Arc A770": { score: 58, tier: "mid" }, "Intel Arc A750": { score: 52, tier: "mid" }
};
const BRAND_ADJUSTMENTS: Record<string, [number, string]> = { "PC Custom": [0, "configuration assemblee"], Lenovo: [5, "marque pro fiable"], HP: [5, "marque pro fiable"], Dell: [5, "marque pro fiable"], Shuttle: [5, "marque pro fiable"], Minisforum: [4, "bonne marque PC compact"], Beelink: [4, "bonne marque PC compact"], Geekom: [3, "bonne marque PC compact"], GMKtec: [2, "marque PC compact correcte"], MSI: [3, "bonne marque PC"], Asus: [3, "bonne marque PC"], Acer: [1, "marque correcte"], Intel: [3, "NUC / plateforme reconnue"], Chuwi: [-2, "marque entree de gamme"], NiPoGi: [-3, "marque a verifier"], Acemagic: [-2, "marque a verifier"] };
const PENALIZED_CPUS = new Set(["Intel N100", "Intel N150", "Intel N4000", "Intel G630", "AMD A10", "Intel i5-8500T", "Intel i5-6500T", "Intel i3-7th gen"]);

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    if (request.method === "OPTIONS") return cors(new Response(null, { status: 204 }));
    const url = new URL(request.url);
    try {
      if (url.pathname === "/health") return json({ status: "ok" });
      if (url.pathname === "/analyze" && request.method === "POST") return analyze(request, env);
      if (url.pathname === "/learning/stats") return json(await learningStats(env));
      if (url.pathname === "/learning/examples") return json(await learningExamples(env, url.searchParams.get("flag"), Number(url.searchParams.get("limit") || 30)));
      if (url.pathname === "/learning/rules") return json(await learningRules(env));
      if (url.pathname === "/learning/auto-runs") return json(await learningRuns(env));
      if (url.pathname === "/learning/auto-run" && ["GET", "POST"].includes(request.method)) return json(await runAutoLearn(env));
      return json({ error: "Not found" }, 404);
    } catch (error) {
      return json({ error: error instanceof Error ? error.message : "Internal error" }, 500);
    }
  },
  async scheduled(_controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(runAutoLearn(env));
  },
};
async function analyze(request: Request, env: Env): Promise<Response> { const payload = await request.json<AnalyzeRequest>(); let parsed = parseListing(payload.title || "", payload.price ?? null, payload.description || ""); parsed = await applyLearnedRules(env, parsed, `${payload.title || ""} ${payload.description || ""}`); const result = scoreListing(parsed, await learnedScores(env)); const full = { ...parsed, ...result }; await recordObservation(env, payload, full, payload.url || null); return json(full); }
function parseListing(title: string, price: string | number | null, description: string): ParsedListing { const text = normalize(`${title} ${typeof price === "string" ? price : ""} ${description}`); const brand = extractBrand(text); const cpu = extractCpu(text); const gpu = extractGpu(text); const ram_gb = extractRamGb(text); const ram = extractRamDetails(text); const storage = extractStorage(text); return { brand, model: null, cpu, gpu, ram_gb, ...ram, ...storage, price: parsePrice(price, text), raw: { title, description } }; }
function normalize(value: string): string { return value.replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim(); }
function parsePrice(value: string | number | null, text: string): number | null { if (typeof value === "number") return Math.round(value); const match = normalize(`${value || ""} ${text}`).match(/(\d[\d\s.,]{0,8})\s*(?:EUR|€|euros?)/i); return match ? Number(match[1].replace(/\D/g, "")) : null; }
function looksLikeCustomPc(text: string): boolean { return [/\bPC\s*(?:custom|gamer|gaming|fixe|monte|mont[ée]|assemble|assembl[ée])\b/i, /\b(?:tour|config|configuration)\s*(?:gamer|gaming|custom|montee|mont[ée]e|assemblee|assembl[ée]e)?\b/i, /\bcarte\s+(?:mere|m[èe]re|graphique)\b/i, /\b(?:boitier|alimentation|watercooling|ventirad)\b/i].some((pattern) => pattern.test(text)) && !/\b(Beelink|Minisforum|GMKtec|Geekom|Chuwi|Lenovo|HP|Dell|Shuttle|NiPoGi|Acemagic|Ace\s+Magician)\b/i.test(text); }
function extractBrand(text: string): string | null { if (looksLikeCustomPc(text)) return CUSTOM_PC_BRAND; for (const brand of BRANDS) if (new RegExp(`\\b${escapeRe(brand)}\\b`, "i").test(text)) return brand === "Ace Magician" ? "Acemagic" : brand; return null; }
function extractCpu(text: string): string | null { const upper = text.toUpperCase().replace(/[-_/]+/g, " ").replace(/\s+/g, " "); const aliases: Record<string, string> = { "RYZEN 7 5800U": "Ryzen 7 5800U", "RYZEN 7 5800H": "Ryzen 7 5800H", "RYZEN 7 5700U": "Ryzen 7 5700U", "RYZEN 7 5700X": "Ryzen 7 5700X", "RYZEN 7 8700G": "Ryzen 7 8700G", "RYZEN 7 H255": "Ryzen 7 H255", "RYZEN 7 8745HS": "Ryzen 7 8745HS", "RYZEN 9 6900HX": "Ryzen 9 6900HX", "RYZEN 5 5500U": "Ryzen 5 5500U", "I5 12400": "Intel i5-12400", "I5 1235U": "Intel i5-1235U", "I5 7500": "Intel i5-7500", "I5 6500T": "Intel i5-6500T", "N100": "Intel N100", "N150": "Intel N150", "N4000": "Intel N4000" }; for (const [key, label] of Object.entries(aliases)) if (new RegExp(`\\b${escapeRe(key)}\\b`).test(upper)) return label; if (/\b8745HS\b/.test(upper)) return "Ryzen 7 8745HS"; const ryzen = upper.match(/\bRYZEN\s*([3579])\s*((?:\d{4}|H\s*\d{3})[A-Z]{0,2})\b/); if (ryzen) return `Ryzen ${ryzen[1]} ${ryzen[2].replace(/\s/g, "")}`; const ryzenFamily = upper.match(/\bRYZEN\s*([3579])\b/); if (ryzenFamily) return `Ryzen ${ryzenFamily[1]} unknown`; const intelGen = upper.match(/\b(?:INTEL\s*)?I([357])\s*(\d{1,2})(?:TH)?\s*(?:GEN)?\b/); if (intelGen && Number(intelGen[2]) <= 14) return `Intel i${intelGen[1]}-${intelGen[2]}th gen`; const intelCore = upper.match(/\b(?:INTEL\s*)?I\s*\.?\s*([357])\s*(\d{4,5}[A-Z]{0,2})\b/); if (intelCore) return `Intel i${intelCore[1]}-${intelCore[2]}`; const n = upper.match(/\b(?:INTEL\s*)?N(100|150|4000)\b/); return n ? `Intel N${n[1]}` : null; }
function extractGpu(text: string): string | null { const upper = text.toUpperCase(); const patterns: Array<[RegExp, string]> = [[/\bRTX\s*(5090|5080|5070|4070|4060|3090|3080|3070|3060|2080|2070|2060)\b/i, "RTX {}"], [/\bGTX\s*(1660\s*SUPER|1660|1650|1060|1050\s*TI)\b/i, "GTX {}"], [/\bRX\s*(7900\s*XTX|7800\s*XT|7700\s*XT|7600|6800\s*XT|6750\s*XT|6700\s*XT|6600|5700\s*XT)\b/i, "RX {}"], [/\bRADEON\s*(780M)\b/i, "Radeon {}"], [/\bARC\s*(A770|A750)\b/i, "Intel Arc {}"]]; for (const [regex, template] of patterns) { const match = upper.match(regex); if (match) return template.replace("{}", match[1].replace(/\s+/g, " ").trim().replace(/^(\d{4})(XT|XTX)$/, "$1 $2")); } return null; }
function extractRamGb(text: string): number | null { const values: number[] = []; const storageWords = "SSD|NVME|HDD|STOCKAGE|DISQUE|STORAGE|ROM|EMMC|SATA|M\\.2|M2|DD"; for (const m of text.matchAll(/\b(\d{1,2})\s*x\s*(\d{1,2})\b/gi)) values.push(Number(m[1]) * Number(m[2])); for (const m of text.matchAll(/\b(\d{1,3})\s*(?:GO|GB)\b/gi)) { const gb = Number(m[1]); const before = text.slice(Math.max(0, m.index! - 42), m.index); const after = text.slice(m.index! + m[0].length, m.index! + m[0].length + 28); const context = `${before} ${m[0]} ${after}`; const ramContext = /\b(RAM|DDR\d?|MEMOIRE|MÉMOIRE|MEMORY|BARRETTE|SO\s*DIMM|SODIMM)\b/i.test(context); const storageContext = new RegExp(storageWords, "i").test(context); if (new RegExp(`\\b(${storageWords})\\s*(?::|de|d'|avec|en)?\\s*$`, "i").test(before) || (gb >= 64 && (/^\s*(SSD|NVME|HDD|ROM|EMMC|SATA|M\.2|M2|DD)\b/i.test(after) || (storageContext && !ramContext)))) continue; if (gb >= 2 && gb <= 128) values.push(gb); } return values.length ? Math.max(...values) : null; }
function extractRamDetails(text: string): { ram_type: string | null; ram_speed_mhz: number | null } { const type = text.match(/\b(DDR[345])\b/i)?.[1].toUpperCase() || null; const speed = text.match(/\b(?:DDR[345][-\s]*)?(\d{4,5})\s*MHZ\b/i)?.[1] || text.match(/\bDDR[345][-\s]*(\d{4,5})\b/i)?.[1]; return { ram_type: type, ram_speed_mhz: speed ? Number(speed) : null }; }
function extractStorage(text: string): { storage_type: string | null; storage_gb: number | null; storage_label: string | null } { const candidates: Array<{ type: string; size: number; confidence: number }> = []; const storageWords = "SSD|NVME|NVM\\s*E|M\\.2|M2|HDD|EMMC|SATA|STOCKAGE|DISQUE|STORAGE|ROM|FLASH|DRIVE|DD"; for (const m of text.matchAll(/\b(\d+(?:[,.]\d+)?)\s*(TO|TB|GO|GB)\b/gi)) { const size = sizeToGb(m[1], m[2]); if (size < 32 || size > 8192) continue; const before = text.slice(Math.max(0, m.index! - 40), m.index); const after = text.slice(m.index! + m[0].length, m.index! + m[0].length + 28); const context = `${before} ${after}`; const b = before.match(new RegExp(`\\b(${storageWords})\\s*(?::|de|d'|avec|en)?\\s*$`, "i")); const a = after.match(new RegExp(`^\\s*(?:[:/+-]\\s*)?(${storageWords})\\b`, "i")); if (!b && !a && size < 128) continue; let kind = storageKind((b?.[1] || a?.[1] || "SSD").toUpperCase().replace(/\s/g, "")); let confidence = b || a ? 3 : 1; if (/\b(NVME|NVM\s*E|M\.2|M2)\b/i.test(context)) { if (kind === "SSD") kind = "NVMe"; confidence += 1; } candidates.push({ type: kind, size, confidence }); } if (!candidates.length) return { storage_type: null, storage_gb: null, storage_label: null }; const best = candidates.sort((a, b) => b.size - a.size || b.confidence - a.confidence)[0]; const labelSize = best.size >= 1024 && best.size % 1024 === 0 ? `${best.size / 1024} To` : `${best.size} Go`; return { storage_type: best.type, storage_gb: best.size, storage_label: `${best.type} ${labelSize}` }; }
function sizeToGb(value: string, unit: string): number { const n = Number(value.replace(",", ".")); return /^T/i.test(unit) ? Math.round(n * 1024) : Math.round(n); }
function storageKind(token: string): string { if (["NVME", "M.2", "M2"].includes(token)) return "NVMe"; if (token === "SATA") return "SATA SSD"; if (["HDD", "DD"].includes(token)) return "HDD"; if (token === "EMMC") return "eMMC"; return "SSD"; }
async function applyLearnedRules(env: Env, parsed: ParsedListing, text: string): Promise<ParsedListing> {
  const upper = text.toUpperCase();
  const next = { ...parsed };

  if (!next.cpu) {
    const rows = ((await env.DB.prepare("SELECT pattern, label FROM learned_cpu ORDER BY seen_count DESC").all()).results || []) as any[];
    for (const row of rows) {
      if (upper.includes(row.pattern)) {
        next.cpu = row.label;
        break;
      }
    }
  }

  if (!next.gpu) {
    const rows = ((await env.DB.prepare("SELECT pattern, label FROM learned_gpu ORDER BY seen_count DESC").all()).results || []) as any[];
    for (const row of rows) {
      if (upper.includes(row.pattern)) {
        next.gpu = row.label;
        break;
      }
    }
  }

  if (!next.brand) {
    const rows = ((await env.DB.prepare("SELECT pattern, label FROM learned_brand ORDER BY seen_count DESC").all()).results || []) as any[];
    for (const row of rows) {
      if (upper.includes(row.pattern)) {
        next.brand = row.label;
        break;
      }
    }
  }

  return next;
}

type LearnBucketItem = { value: string; count: number };
type ObservationRow = { title?: string; description?: string; parsed_json?: string; flags?: string };
type ParsedObservation = { cpu?: string | null; gpu?: string | null; brand?: string | null; raw?: { title?: string; description?: string }; details?: { cpu_score?: number; gpu_score?: number } };

const MIN_CPU_OCCURRENCES = 2;
const MIN_GPU_OCCURRENCES = 2;

async function runAutoLearn(env: Env) {
  try {
    const result = await autoLearn(env);
    await recordAutoLearnRun(env, result.scanned, result.written, null, result);
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown auto-learn error";
    await recordAutoLearnRun(env, 0, 0, message, null);
    throw error;
  }
}

async function autoLearn(env: Env) {
  const rows = ((await env.DB.prepare("SELECT title, description, parsed_json, flags FROM observations ORDER BY id DESC LIMIT 300").all()).results || []) as ObservationRow[];
  const cpuBucket = new Map<string, number>();
  const gpuBucket = new Map<string, number>();
  const brandBucket = new Map<string, number>();

  for (const row of rows) {
    const parsed = safeJson<ParsedObservation>(row.parsed_json || "{}") || {};
    const flags = safeJson<string[]>(row.flags || "[]") || [];
    const text = normalize(`${row.title || ""} ${row.description || ""} ${parsed.raw?.title || ""} ${parsed.raw?.description || ""} ${parsed.cpu || ""} ${parsed.gpu || ""} ${parsed.brand || ""}`);

    if (flags.includes("missing_cpu") || flags.includes("unknown_cpu_score") || parsed.details?.cpu_score === 35) {
      for (const candidate of candidateCpus(text)) bump(cpuBucket, candidate);
      if (parsed.cpu && parsed.details?.cpu_score === 35) bump(cpuBucket, parsed.cpu);
    }
    if (flags.includes("unknown_gpu_score") || !parsed.gpu) {
      for (const candidate of candidateGpus(text)) bump(gpuBucket, candidate);
    }
    // Brand learning is intentionally disabled for now: free-text Leboncoin cards
    // mostly surface cities, seller labels, categories, and component names.
  }

  const learned = { cpu: [] as Array<Record<string, unknown>>, gpu: [] as Array<Record<string, unknown>>, brand: [] as Array<Record<string, unknown>> };
  const statements: D1PreparedStatement[] = [];

  for (const item of topCandidates(cpuBucket, 50)) {
    if (item.count < MIN_CPU_OCCURRENCES) continue;
    const label = normalizeCpuLabel(item.value);
    const score = label ? estimateCpuScore(label) : null;
    if (!label || score === null || CPU_SCORES[label]) continue;
    statements.push(env.DB.prepare("INSERT INTO learned_cpu (pattern, label, score, seen_count) VALUES (?, ?, ?, ?) ON CONFLICT(pattern) DO UPDATE SET label = excluded.label, score = excluded.score, seen_count = excluded.seen_count, updated_at = CURRENT_TIMESTAMP").bind(item.value.toUpperCase(), label, score, item.count));
    learned.cpu.push({ pattern: item.value.toUpperCase(), label, score, count: item.count });
  }

  for (const item of topCandidates(gpuBucket, 50)) {
    if (item.count < MIN_GPU_OCCURRENCES) continue;
    const label = normalizeGpuLabel(item.value);
    const score = label ? estimateGpuScore(label) : null;
    if (!label || score === null || GPU_SCORES[label]) continue;
    statements.push(env.DB.prepare("INSERT INTO learned_gpu (pattern, label, score, seen_count) VALUES (?, ?, ?, ?) ON CONFLICT(pattern) DO UPDATE SET label = excluded.label, score = excluded.score, seen_count = excluded.seen_count, updated_at = CURRENT_TIMESTAMP").bind(item.value.toUpperCase(), label, score, item.count));
    learned.gpu.push({ pattern: item.value.toUpperCase(), label, score, count: item.count });
  }

  const candidates = {
    cpu: topCandidates(cpuBucket, 10),
    gpu: topCandidates(gpuBucket, 10),
    brand: [],
  };

  if (statements.length) await env.DB.batch(statements);
  return { scanned: rows.length, written: statements.length, candidates, learned };
}

async function recordAutoLearnRun(env: Env, scanned: number, written: number, error: string | null, result: unknown): Promise<void> {
  await env.DB.prepare("INSERT INTO auto_learn_runs (scanned, written, error, result_json) VALUES (?, ?, ?, ?)").bind(scanned, written, error, result ? JSON.stringify(result).slice(0, 4000) : null).run();
}

async function learningRuns(env: Env) {
  const runs = await env.DB.prepare("SELECT id, scanned, written, error, result_json, created_at FROM auto_learn_runs ORDER BY id DESC LIMIT 20").all();
  return { runs: runs.results || [] };
}

function candidateCpus(text: string): string[] {
  const upper = text.toUpperCase().replace(/[._/-]+/g, " ").replace(/\s+/g, " ");
  const patterns = [/\bRYZEN\s+[3579]\s+(?:\d{4}|H\s*\d{3})[A-Z]{0,2}\b/g, /\bI[3579]\s*\d{4,5}[A-Z]{0,2}\b/g, /\bINTEL\s+I[3579]\s*\d{4,5}[A-Z]{0,2}\b/g, /\bI[3579]\s*\d{1,2}(?:TH)?\s*GEN\b/g, /\bN\d{3,4}\b/g, /\b(?:CELERON|PENTIUM)\s+[A-Z]?\d{3,5}\b/g];
  return collectMatches(upper, patterns);
}

function candidateGpus(text: string): string[] {
  const upper = text.toUpperCase().replace(/[._/-]+/g, " ").replace(/\s+/g, " ");
  const patterns = [/\bRTX\s*(?:PRO\s*)?\d{4}(?:\s*SUPER|\s*TI)?\b/g, /\bGTX\s*\d{4}(?:\s*SUPER|\s*TI)?\b/g, /\bRX\s*\d{4}(?:\s*XT|\s*XTX)?\b/g, /\bRADEON\s*\d{3,4}M\b/g, /\bARC\s*A\d{3,4}\b/g];
  return collectMatches(upper, patterns);
}

function candidateBrands(text: string): string[] {
  const found = text.match(/\b[A-Z][A-Za-z0-9]{2,}(?:\s+[A-Z][A-Za-z0-9]{1,}){0,2}\b/g) || [];
  const stop = new Set(["Prix", "France", "Windows", "Livraison", "Annonce", "Ordinateurs", "Categorie", "Catégorie", "Deja Vu", "Déjà Vu", "Tres bon", "Très bon"]);
  return found.map((item) => item.trim()).filter((item) => !stop.has(item) && !/\d/.test(item)).slice(0, 20);
}

function collectMatches(text: string, patterns: RegExp[]): string[] {
  const found = new Set<string>();
  for (const pattern of patterns) for (const match of text.matchAll(pattern)) found.add(match[0].replace(/\s+/g, " ").trim());
  return [...found];
}

function normalizeCpuLabel(value: string): string | null {
  const upper = value.toUpperCase().replace(/[.-]+/g, " ").replace(/\s+/g, " ").trim();
  const ryzen = upper.match(/\bRYZEN\s+([3579])\s+((?:\d{4}|H\s*\d{3})[A-Z]{0,2})\b/);
  if (ryzen) return `Ryzen ${ryzen[1]} ${ryzen[2].replace(/\s/g, "")}`;
  const intelCore = upper.match(/\b(?:INTEL\s*)?I([3579])\s*(\d{4,5}[A-Z]{0,2})\b/);
  if (intelCore) return `Intel i${intelCore[1]}-${intelCore[2]}`;
  const intelGen = upper.match(/\bI([3579])\s*(\d{1,2})(?:TH)?\s*GEN\b/);
  if (intelGen) return `Intel i${intelGen[1]}-${intelGen[2]}th gen`;
  const intelN = upper.match(/\bN(\d{3,4})\b/);
  if (intelN) return `Intel N${intelN[1]}`;
  const celeron = upper.match(/\bCELERON\s+([A-Z]?\d{3,5})\b/);
  if (celeron) return `Intel Celeron ${celeron[1]}`;
  const pentium = upper.match(/\bPENTIUM\s+([A-Z]?\d{3,5})\b/);
  if (pentium) return `Intel Pentium ${pentium[1]}`;
  return null;
}

function estimateCpuScore(label: string): number | null {
  if (label.startsWith("Ryzen")) {
    const model = label.match(/(\d{4})/);
    if (!model) return null;
    const number = Number(model[1]);
    if (number >= 8700) return 95;
    if (number >= 7700) return 90;
    if (number >= 6800) return 86;
    if (number >= 5700) return 78;
    if (number >= 5500) return 66;
    if (number >= 3700) return 60;
    return 55;
  }
  if (label.startsWith("Intel i")) {
    const model = label.match(/-(\d{4,5})/);
    if (model) {
      const raw = model[1];
      const generation = raw.length >= 5 ? Number(raw.slice(0, 2)) : Number(raw[0]);
      if (generation >= 13) return 82;
      if (generation >= 12) return 74;
      if (generation >= 11) return 62;
      if (generation >= 10) return 48;
      if (generation >= 8) return 43;
      return 35;
    }
    const gen = label.match(/-(\d{1,2})th gen/);
    if (gen) return Number(gen[1]) >= 10 ? 48 : 30;
  }
  if (label.startsWith("Intel N")) return ["Intel N100", "Intel N150"].includes(label) ? 30 : 12;
  if (label.includes("Celeron") || label.includes("Pentium")) return 10;
  return null;
}

function normalizeGpuLabel(value: string): string | null {
  const upper = value.toUpperCase().replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim();
  const rtx = upper.match(/\bRTX\s*(?:PRO\s*)?(\d{4})(?:\s*(SUPER|TI))?\b/);
  if (rtx) return `RTX ${rtx[1]}${rtx[2] ? ` ${rtx[2]}` : ""}`;
  const gtx = upper.match(/\bGTX\s*(\d{4})(?:\s*(SUPER|TI))?\b/);
  if (gtx) return `GTX ${gtx[1]}${gtx[2] ? ` ${gtx[2]}` : ""}`;
  const rx = upper.match(/\bRX\s*(\d{4})(?:\s*(XT|XTX))?\b/);
  if (rx) return `RX ${rx[1]}${rx[2] ? ` ${rx[2]}` : ""}`;
  const arc = upper.match(/\bARC\s*(A\d{3,4})\b/);
  if (arc) return `Intel Arc ${arc[1]}`;
  const radeon = upper.match(/\bRADEON\s*(\d{3,4}M)\b/);
  if (radeon) return `Radeon ${radeon[1]}`;
  return null;
}

function estimateGpuScore(label: string): number | null {
  const model = label.match(/(\d{4})/);
  if (!model) return null;
  const number = Number(model[1]);
  if (label.startsWith("RTX")) {
    const generation = Math.floor(number / 1000) * 10;
    const tier = number % 1000;
    const base = ({ 50: 92, 40: 72, 30: 50, 20: 38, 10: 18 } as Record<number, number>)[generation] ?? 35;
    if (tier >= 900) return Math.min(100, base + 18);
    if (tier >= 800) return Math.min(100, base + 12);
    if (tier >= 700) return Math.min(100, base + 5);
    if (tier <= 600) return Math.max(10, base - 8);
    return base;
  }
  if (label.startsWith("GTX")) return number >= 1660 ? 36 : number >= 1650 ? 24 : 16;
  if (label.startsWith("RX")) {
    const generation = Math.floor(number / 1000);
    const tier = number % 1000;
    const base = ({ 7: 58, 6: 45, 5: 25 } as Record<number, number>)[generation] ?? 35;
    if (tier >= 900) return Math.min(100, base + 20);
    if (tier >= 800) return Math.min(100, base + 12);
    if (tier >= 700) return Math.min(100, base + 5);
    return base;
  }
  if (label.includes("Arc")) return 55;
  return null;
}

function normalizeBrandLabel(value: string): string | null {
  const label = value.replace(/\s+/g, " ").trim();
  if (label.length < 3 || label.length > 40 || /\d/.test(label)) return null;
  return label;
}

function bump(bucket: Map<string, number>, key: string): void {
  if (!key) return;
  bucket.set(key, (bucket.get(key) || 0) + 1);
}

function topCandidates(bucket: Map<string, number>, limit: number): LearnBucketItem[] {
  return [...bucket.entries()].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count).slice(0, limit);
}

function safeJson<T>(value: string): T | null {
  try { return JSON.parse(value) as T; } catch (_error) { return null; }
}

async function learnedScores(env: Env): Promise<{ cpu: Record<string, number>; gpu: Record<string, number> }> { const cpuRows = (await env.DB.prepare("SELECT label, score FROM learned_cpu").all()).results || []; const gpuRows = (await env.DB.prepare("SELECT label, score FROM learned_gpu").all()).results || []; return { cpu: Object.fromEntries(cpuRows.map((r: any) => [r.label, r.score])), gpu: Object.fromEntries(gpuRows.map((r: any) => [r.label, r.score])) }; }
function scoreListing(parsed: ParsedListing, learned: { cpu: Record<string, number>; gpu: Record<string, number> }) { const cpuBench = parsed.cpu ? CPU_SCORES[parsed.cpu] : undefined; const cpuScore = parsed.cpu && learned.cpu[parsed.cpu] ? learned.cpu[parsed.cpu] : (cpuBench?.score ?? 35); const cpuSource = parsed.cpu && learned.cpu[parsed.cpu] ? "learned" : (cpuBench ? "benchmark" : (parsed.cpu ? "fallback" : null)); const gpuBench = parsed.gpu ? GPU_SCORES[parsed.gpu] : undefined; const gpuScore = parsed.gpu && learned.gpu[parsed.gpu] ? learned.gpu[parsed.gpu] : (gpuBench?.score ?? 0); const gpuSource = parsed.gpu && learned.gpu[parsed.gpu] ? "learned" : (gpuBench ? "benchmark" : (parsed.gpu ? "fallback" : null)); const ramScore = ramScoreOf(parsed.ram_gb, parsed.ram_type, parsed.ram_speed_mhz); const storageScore = storageScoreOf(parsed.storage_gb, parsed.storage_type); const priceScore = priceScoreOf(parsed.price, cpuScore + gpuScore * 0.45, parsed.ram_gb, parsed.storage_gb); const desktopGpu = Boolean(parsed.gpu && gpuScore >= 30); let score = desktopGpu ? cpuScore * 0.35 + gpuScore * 0.3 + ramScore * 0.15 + storageScore * 0.1 + priceScore * 0.1 : cpuScore * 0.5 + ramScore * 0.2 + storageScore * 0.1 + priceScore * 0.2; const adjustments: string[] = []; const brandAdjustment = parsed.brand ? BRAND_ADJUSTMENTS[parsed.brand] : undefined; if (parsed.cpu && PENALIZED_CPUS.has(parsed.cpu)) { score -= 8; adjustments.push("CPU peu performant ou ancien"); } if (brandAdjustment) { score += brandAdjustment[0]; adjustments.push(brandAdjustment[1]); } if (parsed.ram_gb && parsed.ram_gb >= 32) { score += 4; adjustments.push("32 Go de RAM ou plus"); } if (parsed.ram_type === "DDR5") { score += 2; adjustments.push("DDR5"); } if (desktopGpu) adjustments.push("GPU dedie"); if (parsed.storage_gb && parsed.storage_gb >= 512 && ["SSD", "NVMe"].includes(parsed.storage_type || "")) { score += 3; adjustments.push("SSD confortable"); } const finalScore = Math.max(0, Math.min(100, Math.round(score))); const verdict = finalScore >= 82 ? "Excellent" : finalScore >= 65 ? "Bon" : finalScore >= 45 ? "Moyen" : "À éviter"; const reason = `${parsed.cpu || "CPU non identifie"}${parsed.gpu ? `, ${parsed.gpu}` : ""}, ${parsed.ram_gb ? `${parsed.ram_gb} Go RAM` : "RAM inconnue"}, ${parsed.storage_label || "stockage inconnu"}: ${priceScore >= 80 ? "prix attractif pour cette configuration" : (adjustments.slice(0, 2).join(", ") || "configuration coherente mais prix a verifier")}.`; return { score: finalScore, verdict, reason, details: { cpu_score: cpuScore, cpu_score_source: cpuSource, cpu_mark: cpuBench?.cpu_mark ?? null, cpu_single_thread: cpuBench?.single_thread ?? null, cpu_tier: cpuBench?.tier ?? null, cpu_year: cpuYear(parsed.cpu, cpuBench), gpu_score: gpuScore, gpu_score_source: gpuSource, gpu_tier: gpuBench?.tier ?? null, scoring_profile: desktopGpu ? "desktop_gpu" : "compact_pc", brand_adjustment: brandAdjustment?.[0] ?? 0, ram_score: ramScore, storage_score: storageScore, price_score: priceScore, adjustments } }; }
function cpuYear(cpu: string | null, bench?: { year?: number }): number | null { if (!cpu) return null; if (bench?.year) return bench.year; if (cpu.startsWith("Ryzen")) { const model = cpu.match(/(\d{4})/); if (!model) return null; const n = Number(model[1]); if (n >= 8700) return 2024; if (n >= 7700) return 2023; if (n >= 6800) return 2022; if (n >= 5500) return 2021; if (n >= 3700) return 2019; return null; } if (cpu.startsWith("Intel i")) { const genLabel = cpu.match(/-(\d{1,2})th gen/); const model = cpu.match(/-(\d{4,5})/); const gen = genLabel ? Number(genLabel[1]) : model ? Number(model[1].length >= 5 ? model[1].slice(0, 2) : model[1][0]) : null; return gen ? ({ 14: 2023, 13: 2022, 12: 2022, 11: 2020, 10: 2020, 9: 2019, 8: 2018, 7: 2017, 6: 2015 } as Record<number, number>)[gen] ?? null : null; } if (cpu === "Intel N150") return 2025; if (cpu === "Intel N100") return 2023; return null; }
function ramScoreOf(gb: number | null, type: string | null, speed: number | null): number { let s = !gb ? 25 : gb >= 64 ? 100 : gb >= 32 ? 92 : gb >= 16 ? 76 : gb >= 8 ? 45 : 20; if (type === "DDR5") s += 5; if (type === "DDR3") s -= 8; if (speed && speed >= 5600) s += 3; if (speed && speed < 2666) s -= 5; return clamp(s); }
function storageScoreOf(gb: number | null, type: string | null): number { let s = !gb ? 30 : gb >= 1024 ? 100 : gb >= 512 ? 86 : 50; if (type === "HDD") s -= 25; if (type === "SATA SSD") s -= 3; if (type === "NVMe") s += 5; return clamp(s); }
function priceScoreOf(price: number | null, perf: number, ram: number | null, storage: number | null): number { if (!price) return 45; const target = 120 + perf * 3.1 + (ram && ram >= 32 ? 55 : ram && ram >= 16 ? 25 : 0) + (storage && storage >= 1024 ? 45 : storage && storage >= 512 ? 25 : 0); const ratio = price / target; return ratio <= 0.65 ? 100 : ratio <= 0.8 ? 88 : ratio <= 1 ? 72 : ratio <= 1.2 ? 50 : ratio <= 1.45 ? 28 : 10; }
function clamp(n: number): number { return Math.max(0, Math.min(100, Math.round(n))); }
function detectFlags(result: any): string[] { const flags: string[] = []; if (!result.cpu) flags.push("missing_cpu"); if (result.cpu && result.details?.cpu_score === 35) flags.push("unknown_cpu_score"); if (result.gpu && result.details?.gpu_score === 0) flags.push("unknown_gpu_score"); if (!result.ram_gb) flags.push("missing_ram"); if (!result.storage_gb) flags.push("missing_storage"); if (!result.brand) flags.push("missing_brand"); return flags; }
async function recordObservation(env: Env, payload: AnalyzeRequest, result: any, url: string | null) { const flags = detectFlags(result); await env.DB.prepare("INSERT INTO observations (url, title, price, description, parsed_json, score, verdict, flags) VALUES (?, ?, ?, ?, ?, ?, ?, ?)").bind(url, payload.title || "", String(payload.price || ""), (payload.description || "").slice(0, 4000), JSON.stringify(result), result.score, result.verdict, JSON.stringify(flags)).run(); }
async function learningStats(env: Env) { const total = await env.DB.prepare("SELECT COUNT(*) AS total FROM observations").first<{ total: number }>(); const recent = await env.DB.prepare("SELECT title, score, verdict, flags, created_at FROM observations ORDER BY id DESC LIMIT 10").all(); return { total: total?.total ?? 0, recent: recent.results || [] }; }
async function learningExamples(env: Env, flag: string | null, limit: number) { const safeLimit = Math.max(1, Math.min(limit || 30, 100)); const stmt = flag ? env.DB.prepare("SELECT id, url, title, price, score, verdict, flags, parsed_json, created_at FROM observations WHERE flags LIKE ? ORDER BY id DESC LIMIT ?").bind(`%\"${flag}\"%`, safeLimit) : env.DB.prepare("SELECT id, url, title, price, score, verdict, flags, parsed_json, created_at FROM observations ORDER BY id DESC LIMIT ?").bind(safeLimit); const rows = await stmt.all(); return { examples: rows.results || [] }; }
async function learningRules(env: Env) { const cpu = await env.DB.prepare("SELECT * FROM learned_cpu ORDER BY seen_count DESC").all(); const gpu = await env.DB.prepare("SELECT * FROM learned_gpu ORDER BY seen_count DESC").all(); const brand = await env.DB.prepare("SELECT * FROM learned_brand ORDER BY seen_count DESC").all(); return { cpu: cpu.results || [], gpu: gpu.results || [], brand: brand.results || [] }; }
function json(data: unknown, status = 200): Response { return cors(new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8" } })); }
function cors(response: Response): Response { const headers = new Headers(response.headers); headers.set("access-control-allow-origin", "*"); headers.set("access-control-allow-methods", "GET,POST,OPTIONS"); headers.set("access-control-allow-headers", "content-type"); return new Response(response.body, { status: response.status, headers }); }
function escapeRe(value: string): string { return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
