# db_utils.py
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import pandas as pd


# ---------------- DB connection ----------------
def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ---------------- epsilon DB ----------------
def get_eps_db(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM epsilon_db", conn)


def ensure_epsilon_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS epsilon_db (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            wavelength INTEGER,
            epsilon REAL NOT NULL,
            unit TEXT DEFAULT 'M-1cm-1',
            note TEXT
            )
        """
    )

    # UNIQUE (name, wavelength)
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_epsilon_unique
        ON epsilon_db(name, wavelength)
        """
    )

    conn.commit()


# ---------------- stocks ----------------
def load_stocks(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            id, name,
            stock_conc, stock_unit,
            notes, created_at
        FROM stocks
        ORDER BY name
        """,
        conn,
    )


def insert_stock(
    conn: sqlite3.Connection,
    stock_id: str,
    name: str,
    conc: float,
    unit: str,
    notes: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT INTO stocks(id, name, stock_conc, stock_unit, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (stock_id, name, float(conc), unit, notes or None),
    )
    conn.commit()


def update_stock(
    conn: sqlite3.Connection,
    stock_id: str,
    name: str,
    conc: float,
    unit: str,
    notes: Optional[str],
) -> None:
    conn.execute(
        """
        UPDATE stocks
        SET name = ?, stock_conc = ?, stock_unit = ?, notes = ?
        WHERE id = ?
        """,
        (name, float(conc), unit, notes or None, stock_id),
    )
    conn.commit()


def delete_stock(conn: sqlite3.Connection, stock_id: str) -> None:
    conn.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))
    conn.commit()


# ---------------- plans ----------------
def ensure_plans_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            plan_id     TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            category    TEXT,
            created_by  TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            notes       TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_reactions_plan_id
        ON reactions(plan_id)
        """
    )

    conn.commit()


def load_plans(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            plan_id, title, category,
            created_by, created_at, notes
        FROM plans
        ORDER BY created_at DESC
        """,
        conn,
    )


# ---------------- labeling records ----------------
def ensure_labeling_records_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS labeling_records (
            record_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,

            title TEXT,

            target_name TEXT,
            target_epsilon REAL,
            A_target REAL,

            dye_name TEXT,
            dye_epsilon REAL,
            A_dye REAL,

            target_uM REAL,
            dye_uM REAL,

            labeling_ratio REAL,
            purity REAL,

            A260 REAL,
            A280 REAL,
            uv_purity REAL,

            note TEXT
        )
        """
    )
    conn.commit()


# ---------------- templates ----------------
def load_templates(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            template_id,
            name,
            description,
            created_at
        FROM templates
        ORDER BY created_at DESC
        """,
        conn,
    )


def load_template_items(
    conn: sqlite3.Connection,
    template_id: str
) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            stock_id,
            example_target,
            example_target_unit,
            example_volume,
            example_volume_unit,
            example_amount,
            example_amount_unit,
            item_note
        FROM template_items
        WHERE template_id = ?
        ORDER BY stock_id
        """,
        conn,
        params=(template_id,),
    )


def delete_template(conn: sqlite3.Connection, template_id: str) -> None:
    conn.execute(
        "DELETE FROM template_items WHERE template_id = ?",
        (template_id,),
    )
    conn.execute(
        "DELETE FROM templates WHERE template_id = ?",
        (template_id,),
    )
    conn.commit()


def update_template_meta(
    conn: sqlite3.Connection,
    template_id: str,
    name: str,
    description: Optional[str],
) -> None:
    conn.execute(
        """
        UPDATE templates
        SET name = ?, description = ?
        WHERE template_id = ?
        """,
        (name, description or None, template_id),
    )
    conn.commit()


def save_template_from_computed(
    conn: sqlite3.Connection,
    tmpl_name: str,
    tmpl_desc: Optional[str],
    computed: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    name = (tmpl_name or "").strip()
    if not name:
        return False, "Template name이 필요합니다."

    if any(it.get("stock_id") is None for it in computed):
        return False, "템플릿 저장은 DB stock만 가능합니다. (임시 시약 포함)"

    seen = set()
    for it in computed:
        sid = it["stock_id"]
        if sid in seen:
            return False, f"같은 stock이 2번 포함됨: {sid}"
        seen.add(sid)

    template_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO templates(template_id, name, description)
        VALUES (?, ?, ?)
        """,
        (template_id, name, tmpl_desc or None),
    )

    for it in computed:
        conn.execute(
            """
            INSERT INTO template_items (
                template_id,
                stock_id,
                example_target,
                example_target_unit,
                example_volume,
                example_volume_unit,
                example_amount,
                example_amount_unit,
                item_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                it["stock_id"],
                it["target_conc"] if it.get("target_conc", 0) > 0 else None,
                it["target_unit"] if it.get("target_conc", 0) > 0 else None,
                it["volume"] if it.get("volume", 0) > 0 else None,
                it["volume_unit"] if it.get("volume", 0) > 0 else None,
                float(it.get("amount") or 0.0),
                it.get("amount_unit") or "nmol",
                it.get("note") or None,
            ),
        )

    conn.commit()
    return True, f"Saved template: {name}"

# ---------------- epsilon CRUD ----------------
def upsert_epsilon(
    conn: sqlite3.Connection,
    name: str,
    wavelength: int,
    epsilon: float,
    note: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO epsilon_db (name, wavelength, epsilon, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name, wavelength)
        DO UPDATE SET
            epsilon = excluded.epsilon,
            note = excluded.note
        """,
        (name, wavelength, epsilon, note),
    )
    conn.commit()


# ---------------- labeling records ----------------
def insert_labeling_record(
    conn: sqlite3.Connection,
    record: Dict[str, Any],
) -> None:
    """
    record dict keys:
    record_id, created_by,
    target_name, target_epsilon, A_target,
    dye_name, dye_epsilon, A_dye,
    target_uM, dye_uM,
    labeling_ratio, purity,
    A260, A280, uv_purity,
    note
    """
    conn.execute(
        """
        INSERT INTO labeling_records (
            record_id, created_by,
            target_name, target_epsilon, A_target,
            dye_name, dye_epsilon, A_dye,
            target_uM, dye_uM,
            labeling_ratio, purity,
            A260, A280, uv_purity,
            note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["record_id"],
            record["created_by"],
            record["target_name"],
            record["target_epsilon"],
            record["A_target"],
            record["dye_name"],
            record["dye_epsilon"],
            record["A_dye"],
            record["target_uM"],
            record["dye_uM"],
            record["labeling_ratio"],
            record["purity"],
            record.get("A260"),
            record.get("A280"),
            record.get("uv_purity"),
            record.get("note"),
        ),
    )
    conn.commit()
# CF와 epsilon 호출
def get_epsilon_value(
    conn: sqlite3.Connection,
    name: str,
    wavelength: int
) -> Optional[Dict[str, float]]:
    row = conn.execute(
        """
        SELECT epsilon
        FROM epsilon_db
        WHERE name = ? AND wavelength = ?

        """,
        (name, wavelength)
    ).fetchone()

    if row:
        return {
            "epsilon": float(row[0])
        }
    return None

## Correction factor CRUD
# ---------------- correction factor ----------------
def get_cf(
    conn: sqlite3.Connection,
    dye_name: str,
    target_wavelength: int
) -> Optional[float]:
    row = conn.execute(
        """
        SELECT factor
        FROM correction_factor_db
        WHERE dye_name = ? AND target_wavelength = ?
        """,
        (dye_name, target_wavelength)
    ).fetchone()

    return float(row[0]) if row else None


def upsert_cf(
    conn: sqlite3.Connection,
    dye_name: str,
    target_wavelength: int,
    factor: float,
    note: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO correction_factor_db (
            dye_name, target_wavelength, factor, note
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(dye_name, target_wavelength)
        DO UPDATE SET
            factor = excluded.factor,
            note = excluded.note
        """,
        (dye_name, target_wavelength, factor, note),
    )
    conn.commit()

# CF DB 로딩 함수
def get_cf_db(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            dye_name,
            target_wavelength,
            factor,
            note
        FROM correction_factor_db
        ORDER BY dye_name, target_wavelength
        """,
        conn
    )
