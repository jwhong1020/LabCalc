# db_cache.py
from __future__ import annotations

import streamlit as st
import pandas as pd

from db_utils_pg import (
    load_stocks,
    load_plans,
    load_templates,
    load_template_items,
    get_eps_db,
    get_cf_db,
)

# =================================================
# cache policy
# - DB connection ❌
# - DataFrame만 cache
# =================================================

@st.cache_data
def cached_load_stocks() -> pd.DataFrame:
    return load_stocks(None)

@st.cache_data
def cached_load_plans() -> pd.DataFrame:
    return load_plans(None)

@st.cache_data
def cached_load_templates() -> pd.DataFrame:
    return load_templates(None)

@st.cache_data
def cached_load_template_items(template_id: str) -> pd.DataFrame:
    return load_template_items(None, template_id)

@st.cache_data
def cached_eps_db() -> pd.DataFrame:
    return get_eps_db(None)

@st.cache_data
def cached_cf_db() -> pd.DataFrame:
    return get_cf_db(None)

@st.cache_data
def cached_reactions_in_plan(plan_id: str) -> pd.DataFrame:
    from db_utils_pg import fetchall

    rows = fetchall(
        """
        SELECT
            r.reaction_id,
            r.title,
            r.category,
            r.created_by,
            r.final_volume,
            r.final_volume_unit,
            r.created_at
        FROM reactions r
        WHERE r.plan_id = %s
        ORDER BY r.created_at
        """,
        (plan_id,),
    )

    # ✅ SELECT 컬럼 수(7개) == columns 길이(7개) 맞춰야 함
    return pd.DataFrame(
        rows,
        columns=[
            "reaction_id",
            "title",
            "category",
            "created_by",
            "final_volume",
            "final_volume_unit",
            "created_at",
        ],
    )

@st.cache_data
def cached_labeling_records() -> pd.DataFrame:
    from db_utils_pg import fetchall

    rows = fetchall(
        """
        SELECT
            title,
            created_at,
            created_by,
            target_name,
            dye_name,
            labeling_ratio,
            etoh_efficiency,
            uv_purity,
            note
        FROM labeling_records
        ORDER BY created_at DESC
        """
    )

    return pd.DataFrame(
        rows,
        columns=[
            "title",
            "created_at",
            "created_by",
            "target_name",
            "dye_name",
            "labeling_ratio",
            "etoh_efficiency",
            "uv_purity",
            "note",
        ],
    )
