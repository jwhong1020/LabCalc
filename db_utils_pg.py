from __future__ import annotations

import uuid
from typing import Tuple, List, Dict, Any, Optional

import streamlit as st
import pandas as pd
from psycopg2.pool import SimpleConnectionPool

# =================================================
# Connection pool (singleton)
# =================================================

_pool: Optional[SimpleConnectionPool] = None


def get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        cfg = st.secrets["db"]
        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            host=cfg["host"],
            port=cfg["port"],
            dbname=cfg["name"],
            user=cfg["user"],
            password=cfg["password"],
        )
    return _pool


# =================================================
# Low-level DB helpers (NO conn argument)
# =================================================

def execute(sql: str, params: tuple | None = None) -> None:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    finally:
        pool.putconn(conn)


def fetchone(sql: str, params: tuple | None = None):
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        pool.putconn(conn)


def fetchall(sql: str, params: tuple | None = None):
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        pool.putconn(conn)


# =================================================
# epsilon DB
# =================================================

def get_eps_db(conn=None) -> pd.DataFrame:
    rows = fetchall(
        "SELECT name, wavelength, epsilon, note FROM epsilon_db"
    )
    return pd.DataFrame(
        rows,
        columns=["name", "wavelength", "epsilon", "note"]
    )


def upsert_epsilon(
    conn,
    name: str,
    wavelength: int,
    epsilon: float,
    note: Optional[str] = None,
) -> None:
    execute(
        """
        INSERT INTO epsilon_db (name, wavelength, epsilon, note)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name, wavelength)
        DO UPDATE SET
            epsilon = EXCLUDED.epsilon,
            note = EXCLUDED.note
        """,
        (name, wavelength, epsilon, note),
    )

def delete_epsilon(name: str, wavelength: int) -> None:
    execute(
        """
        DELETE FROM epsilon_db
        WHERE name = %s AND wavelength = %s
        """,
        (name, wavelength),
    )

def get_epsilon_value(
    conn,
    name: str,
    wavelength: int
) -> Optional[Dict[str, float]]:
    row = fetchone(
        """
        SELECT epsilon
        FROM epsilon_db
        WHERE name = %s AND wavelength = %s
        """,
        (name, wavelength),
    )
    if row:
        return {"epsilon": float(row[0])}
    return None


# =================================================
# correction factor DB
# =================================================

def get_cf(
    conn,
    dye_name: str,
    target_wavelength: int
) -> Optional[float]:
    row = fetchone(
        """
        SELECT factor
        FROM correction_factor_db
        WHERE dye_name = %s AND target_wavelength = %s
        """,
        (dye_name, target_wavelength),
    )
    return float(row[0]) if row else None

def upsert_cf(
    conn,
    dye_name: str,
    target_wavelength: int,
    factor: float,
    note: Optional[str] = None,
) -> None:
    # 1️⃣ 먼저 UPDATE 시도
    execute(
        """
        UPDATE correction_factor_db
        SET factor = %s, note = %s
        WHERE dye_name = %s AND target_wavelength = %s
        """,
        (factor, note, dye_name, target_wavelength),
    )

    # 2️⃣ 없으면 INSERT
    execute(
        """
        INSERT INTO correction_factor_db (dye_name, target_wavelength, factor, note)
        SELECT %s, %s, %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM correction_factor_db
            WHERE dye_name = %s AND target_wavelength = %s
        )
        """,
        (dye_name, target_wavelength, factor, note,
         dye_name, target_wavelength),
    )

def delete_cf(dye_name: str, target_wavelength: int) -> None:
    execute(
        """
        DELETE FROM correction_factor_db
        WHERE dye_name = %s AND target_wavelength = %s
        """,
        (dye_name, target_wavelength),
    )


def get_cf_db(conn=None) -> pd.DataFrame:
    rows = fetchall(
        """
        SELECT dye_name, target_wavelength, factor, note
        FROM correction_factor_db
        ORDER BY dye_name, target_wavelength
        """
    )
    return pd.DataFrame(
        rows,
        columns=["dye_name", "target_wavelength", "factor", "note"]
    )


# =================================================
# stocks
# =================================================

def load_stocks(conn=None) -> pd.DataFrame:
    rows = fetchall(
        """
        SELECT
            id, name,
            stock_conc, stock_unit,
            notes, created_at
        FROM stocks
        ORDER BY name
        """
    )
    return pd.DataFrame(
        rows,
        columns=[
            "id", "name",
            "stock_conc", "stock_unit",
            "notes", "created_at",
        ],
    )


def insert_stock(
    conn,
    stock_id: str,
    name: str,
    conc: float,
    unit: str,
    notes: Optional[str],
) -> None:
    execute(
        """
        INSERT INTO stocks(id, name, stock_conc, stock_unit, notes)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (stock_id, name, float(conc), unit, notes or None),
    )


def update_stock(
    conn,
    stock_id: str,
    name: str,
    conc: float,
    unit: str,
    notes: Optional[str],
) -> None:
    execute(
        """
        UPDATE stocks
        SET name = %s, stock_conc = %s, stock_unit = %s, notes = %s
        WHERE id = %s
        """,
        (name, float(conc), unit, notes or None, stock_id),
    )


def delete_stock(conn, stock_id: str) -> None:
    execute(
        "DELETE FROM stocks WHERE id = %s",
        (stock_id,),
    )


# =================================================
# plans / templates
# =================================================

def load_plans(conn=None) -> pd.DataFrame:
    rows = fetchall(
        """
        SELECT
            plan_id, title, category,
            created_by, created_at, notes
        FROM plans
        ORDER BY created_at DESC
        """
    )
    return pd.DataFrame(
        rows,
        columns=[
            "plan_id", "title", "category",
            "created_by", "created_at", "notes",
        ],
    )


def load_templates(conn):
    rows = fetchall(
        """
        SELECT
            template_id,
            name,
            description,
            final_volume,
            final_volume_unit
        FROM templates
        ORDER BY name
        """,
        ()
    )

    return pd.DataFrame(
        rows,
        columns=[
            "template_id",
            "name",
            "description",
            "final_volume",
            "final_volume_unit",
        ],
    )



def load_template_items(conn, template_id: str) -> pd.DataFrame:
    rows = fetchall(
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
        WHERE template_id = %s
        ORDER BY stock_id
        """,
        (template_id,),
    )
    return pd.DataFrame(
        rows,
        columns=[
            "stock_id",
            "example_target",
            "example_target_unit",
            "example_volume",
            "example_volume_unit",
            "example_amount",
            "example_amount_unit",
            "item_note",
        ],
    )


def delete_template(conn, template_id: str) -> None:
    execute(
        "DELETE FROM template_items WHERE template_id = %s",
        (template_id,),
    )
    execute(
        "DELETE FROM templates WHERE template_id = %s",
        (template_id,),
    )


def update_template_meta(
    conn,
    template_id,
    name,
    description,
    final_volume=None,
    final_volume_unit=None,
):
    execute(
        """
        UPDATE templates
        SET
            name = %s,
            description = %s,
            final_volume = COALESCE(%s, final_volume),
            final_volume_unit = COALESCE(%s, final_volume_unit)
        WHERE template_id = %s
        """,
        (
            name,
            description,
            final_volume,
            final_volume_unit,
            template_id,
        )
    )




def save_template_from_computed(
    conn,
    tmpl_name: str,
    tmpl_desc: Optional[str],
    computed: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    name = (tmpl_name or "").strip()
    if not name:
        return False, "Template name이 필요합니다."

    if any(it.get("stock_id") is None for it in computed):
        return False, "템플릿 저장은 DB stock만 가능합니다."

    template_id = str(uuid.uuid4())

    execute(
        """
        INSERT INTO templates(template_id, name, description)
        VALUES (%s, %s, %s)
        """,
        (template_id, name, tmpl_desc or None),
    )

    for it in computed:
        execute(
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                template_id,
                it["stock_id"],
                it.get("target_conc") or None,
                it.get("target_unit") or None,
                it.get("volume") or None,
                it.get("volume_unit") or None,
                float(it.get("amount") or 0.0),
                it.get("amount_unit") or "nmol",
                it.get("note") or None,
            ),
        )

    return True, f"Saved template: {name}"
