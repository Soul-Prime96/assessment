"""
Data Tools — ingestion, KPI computation, trend analysis, anomaly detection.

All functions are designed to be registered as AGY agent tools.
They operate purely on data structures (dicts/lists) for portability.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_csv(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath, parse_dates=["date"])
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


def _load_json(filepath: str) -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def load_data(filepath: str) -> dict[str, Any]:
    """Load business data from a CSV or JSON file and return a summary dict.

    Args:
        filepath: Absolute or relative path to the data file (.csv or .json).

    Returns:
        A dict containing raw records, column info, and basic stats.
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            df = _load_csv(filepath)
        elif ext == ".json":
            records = _load_json(filepath)
            df = pd.DataFrame(records)
        else:
            return {"error": f"Unsupported format: {ext}. Use .csv or .json"}

        result: dict[str, Any] = {
            "source_file": filepath,
            "records_count": len(df),
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        }

        # Date range detection
        date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        if date_cols:
            dc = date_cols[0]
            result["date_range"] = f"{df[dc].min().date()} to {df[dc].max().date()}"
            result["date_column"] = dc
        else:
            result["date_range"] = "N/A"
            result["date_column"] = None

        # Numeric column stats
        numeric = df.select_dtypes(include=["number"])
        result["numeric_columns"] = numeric.columns.tolist()
        result["column_stats"] = {
            col: {
                "mean": round(numeric[col].mean(), 2),
                "std": round(numeric[col].std(), 2),
                "min": round(numeric[col].min(), 2),
                "max": round(numeric[col].max(), 2),
                "sum": round(numeric[col].sum(), 2),
            }
            for col in numeric.columns
        }

        # Categorical column value counts
        categorical = df.select_dtypes(include=["object", "category"])
        result["categorical_columns"] = categorical.columns.tolist()
        result["category_counts"] = {
            col: df[col].value_counts().head(10).to_dict()
            for col in categorical.columns
        }

        # Store serialisable records for downstream tools
        result["records"] = df.to_dict(orient="records")
        return result

    except Exception as exc:
        return {"error": str(exc)}


def compute_kpis(data_summary: dict[str, Any]) -> dict[str, Any]:
    """Compute business KPIs from a loaded data summary.

    Expects the data to have columns: revenue, units_sold, cost, region, product.

    Args:
        data_summary: Output dict from load_data().

    Returns:
        A dict of computed KPI values and period-over-period comparisons.
    """
    if "error" in data_summary:
        return {"error": data_summary["error"]}

    records = data_summary.get("records", [])
    if not records:
        return {"error": "No records to compute KPIs from"}

    df = pd.DataFrame(records)

    # Normalise column names
    col_map = {c: c.lower().replace(" ", "_") for c in df.columns}
    df.rename(columns=col_map, inplace=True)

    kpis: dict[str, Any] = {}

    # --- Revenue & profit ---
    if "revenue" in df.columns:
        total_rev = df["revenue"].sum()
        kpis["total_revenue"] = {"value": round(total_rev, 2), "unit": "$"}

        # Period split: first half vs second half
        mid = len(df) // 2
        prev_rev = df.iloc[:mid]["revenue"].sum()
        curr_rev = df.iloc[mid:]["revenue"].sum()
        change_pct = ((curr_rev - prev_rev) / prev_rev * 100) if prev_rev else 0
        kpis["revenue_growth_pct"] = {
            "value": round(change_pct, 2),
            "unit": "%",
            "previous": round(prev_rev, 2),
            "current": round(curr_rev, 2),
        }

    if "cost" in df.columns and "revenue" in df.columns:
        total_cost = df["cost"].sum()
        total_rev = df["revenue"].sum()
        gross_profit = total_rev - total_cost
        margin = (gross_profit / total_rev * 100) if total_rev else 0
        kpis["gross_profit"] = {"value": round(gross_profit, 2), "unit": "$"}
        kpis["gross_margin_pct"] = {"value": round(margin, 2), "unit": "%"}

    # --- Units & volume ---
    if "units_sold" in df.columns:
        kpis["total_units_sold"] = {
            "value": int(df["units_sold"].sum()),
            "unit": "units",
        }
        if "revenue" in df.columns and df["units_sold"].sum() > 0:
            kpis["avg_revenue_per_unit"] = {
                "value": round(df["revenue"].sum() / df["units_sold"].sum(), 2),
                "unit": "$/unit",
            }

    # --- Refund rate ---
    if "refunds" in df.columns and "units_sold" in df.columns:
        total_refunds = df["refunds"].sum()
        total_units = df["units_sold"].sum()
        refund_rate = (total_refunds / total_units * 100) if total_units else 0
        kpis["refund_rate_pct"] = {"value": round(refund_rate, 2), "unit": "%"}

    # --- Top/bottom performers by revenue ---
    if "product" in df.columns and "revenue" in df.columns:
        by_product = df.groupby("product")["revenue"].sum().sort_values(ascending=False)
        kpis["revenue_by_product"] = {k: round(v, 2) for k, v in by_product.items()}
        kpis["top_product"] = by_product.index[0] if len(by_product) > 0 else "N/A"
        kpis["bottom_product"] = by_product.index[-1] if len(by_product) > 0 else "N/A"

    if "region" in df.columns and "revenue" in df.columns:
        by_region = df.groupby("region")["revenue"].sum().sort_values(ascending=False)
        kpis["revenue_by_region"] = {k: round(v, 2) for k, v in by_region.items()}
        kpis["top_region"] = by_region.index[0] if len(by_region) > 0 else "N/A"

    # --- Inventory days (if present) ---
    if "inventory_days" in df.columns:
        avg_inv = df["inventory_days"].mean()
        kpis["avg_inventory_days"] = {"value": round(avg_inv, 1), "unit": "days"}

    return kpis


def detect_trends(data_summary: dict[str, Any]) -> dict[str, Any]:
    """Analyse time-series trends using moving averages and direction detection.

    Args:
        data_summary: Output dict from load_data().

    Returns:
        A dict with trend direction and 7-day / 30-day moving averages.
    """
    if "error" in data_summary:
        return {"error": data_summary["error"]}

    records = data_summary.get("records", [])
    date_col = data_summary.get("date_column")

    if not records or not date_col:
        return {"error": "No date column found for trend analysis"}

    df = pd.DataFrame(records)
    df[date_col] = pd.to_datetime(df[date_col])
    df.sort_values(date_col, inplace=True)

    trends: dict[str, Any] = {}

    numeric_cols = [c for c in df.select_dtypes(include="number").columns]

    for col in numeric_cols:
        series = df.set_index(date_col)[col].resample("D").sum().fillna(0)

        ma7 = series.rolling(7).mean().dropna()
        ma30 = series.rolling(30).mean().dropna()

        if len(ma7) >= 2:
            direction = "UP" if ma7.iloc[-1] > ma7.iloc[-7] else (
                "DOWN" if ma7.iloc[-1] < ma7.iloc[-7] else "STABLE"
            )
        else:
            direction = "STABLE"

        trends[col] = {
            "direction": direction,
            "latest_7d_avg": round(float(ma7.iloc[-1]), 2) if len(ma7) > 0 else None,
            "latest_30d_avg": round(float(ma30.iloc[-1]), 2) if len(ma30) > 0 else None,
            "total_days": int(len(series)),
        }

    return {"trends": trends}


def detect_anomalies(data_summary: dict[str, Any], z_threshold: float = 2.5) -> dict[str, Any]:
    """Detect statistical outliers using Z-score analysis.

    Args:
        data_summary: Output dict from load_data().
        z_threshold: Z-score above which a value is considered anomalous (default 2.5).

    Returns:
        A dict listing any detected anomalies per numeric column.
    """
    if "error" in data_summary:
        return {"error": data_summary["error"]}

    col_stats = data_summary.get("column_stats", {})
    records = data_summary.get("records", [])

    if not records:
        return {"anomalies": []}

    df = pd.DataFrame(records)
    numeric_cols = data_summary.get("numeric_columns", [])
    anomalies: list[dict] = []

    for col in numeric_cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) < 5:
            continue

        mean_val = series.mean()
        std_val = series.std()
        if std_val == 0:
            continue

        z_scores = np.abs((series - mean_val) / std_val)
        outlier_indices = z_scores[z_scores > z_threshold].index

        for idx in outlier_indices:
            val = float(df.loc[idx, col])
            z = float(z_scores[idx])
            lo = round(mean_val - z_threshold * std_val, 2)
            hi = round(mean_val + z_threshold * std_val, 2)

            # Try to get a row descriptor
            descriptor_cols = ["product", "region", "date", "category"]
            descriptor = {}
            for dc in descriptor_cols:
                if dc in df.columns:
                    raw = df.loc[idx, dc]
                    descriptor[dc] = str(raw)

            anomalies.append({
                "metric": col,
                "row_index": int(idx),
                "descriptor": descriptor,
                "value": round(val, 2),
                "expected_range": (lo, hi),
                "z_score": round(z, 2),
                "description": (
                    f"{col} value {val:.2f} is {z:.1f}σ from mean "
                    f"(expected {lo:.2f}–{hi:.2f})"
                ),
            })

    return {"anomalies": anomalies, "total_found": len(anomalies)}
