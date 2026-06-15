CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT,
  title TEXT NOT NULL,
  price TEXT,
  description TEXT,
  parsed_json TEXT NOT NULL,
  score INTEGER,
  verdict TEXT,
  flags TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_observations_created_at ON observations(created_at);
CREATE INDEX IF NOT EXISTS idx_observations_score ON observations(score);

CREATE TABLE IF NOT EXISTS learned_cpu (
  pattern TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  score INTEGER NOT NULL,
  seen_count INTEGER NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learned_gpu (
  pattern TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  score INTEGER NOT NULL,
  seen_count INTEGER NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learned_brand (
  pattern TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  seen_count INTEGER NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
