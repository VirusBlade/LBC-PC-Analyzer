CREATE TABLE IF NOT EXISTS auto_learn_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scanned INTEGER NOT NULL DEFAULT 0,
  written INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  result_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auto_learn_runs_created_at ON auto_learn_runs(created_at);
