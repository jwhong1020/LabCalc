# db_init.py
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "labcalc.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- Stocks
CREATE TABLE IF NOT EXISTS stocks (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  stock_conc   REAL NOT NULL,
  stock_unit   TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  notes        TEXT,
  UNIQUE(name, stock_conc, stock_unit)
);

-- Templates (reaction types)
CREATE TABLE IF NOT EXISTS templates (
  template_id  TEXT PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  description  TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS template_items (
  template_id        TEXT NOT NULL,
  stock_id           TEXT NOT NULL,
  example_target     REAL,
  example_target_unit TEXT,
  example_volume     REAL,
  example_volume_unit TEXT,
  example_amount     REAL,
  example_amount_unit TEXT,
  item_note          TEXT,
  PRIMARY KEY (template_id, stock_id),
  FOREIGN KEY (template_id) REFERENCES templates(template_id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE RESTRICT
);

-- Reactions
CREATE TABLE IF NOT EXISTS reactions (
  reaction_id  TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  category     TEXT NOT NULL,
  created_by   TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  final_volume REAL,
  final_volume_unit TEXT
);

CREATE TABLE IF NOT EXISTS reaction_items (
  reaction_id       TEXT NOT NULL,
  line_no           INTEGER NOT NULL,
  stock_id          TEXT,
  custom_name       TEXT,
  stock_conc        REAL,
  stock_unit        TEXT,

  target_conc       REAL,
  target_conc_unit  TEXT,

  volume            REAL,
  volume_unit       TEXT,

  amount            REAL,
  amount_unit       TEXT,

  note              TEXT,

  PRIMARY KEY (reaction_id, line_no),
  FOREIGN KEY (reaction_id) REFERENCES reactions(reaction_id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE SET NULL
);
"""

def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        # WAL: 안정성/동시성 향상
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at: {DB_PATH}")
