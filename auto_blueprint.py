"""Build a factual, clearly labelled draft blueprint directly from CSV/Excel data.

This is rule-based inference, not AI editorial analysis. It never asserts an
original source, sampling methodology, causal finding, or invented composite.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from landing_engine import jid

IGNORED_METRICS = re.compile(r"(^|[ _-])(id|identifier|postcode|zip|year|season|round|rank|ranking|latitude|longitude|lat|lon|lng|date)([ _-]|$)", re.I)
ENTITY_PREFERRED = re.compile(r"(^|[ _-])(team|city|state|country|player|coach|school|stadium|arena|region|province|territory|name|franchise|club|location|market)([ _-]|$)", re.I)
METRIC_PREFERRED = re.compile(r"score|index|overall|total|change|percent|pct|percentage|rate|price|cost|salary|miles|distance|points|minutes|shares|wins|revenue|count|value|average", re.I)


def check_required(instruction: str, filename: str | None) -> str | None:
    """Return a user-facing problem or None. Both entries are mandatory."""
    if not filename:
        return "Upload a CSV, XLS or XLSX research file before generating any landing pages."
    if not instruction or not instruction.strip():
        return "Type Build in the instruction box to enable generation."
    if not re.match(r"^(build|generate)(\b|$)", instruction.strip(), flags=re.I):
        return "Start your instruction with Build (for example: Build landing pages)."
    return None


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("The selected sheet has no data rows. Upload a populated CSV/Excel table.")
    data = df.copy()
    data.columns = [str(col).strip().removeprefix("\ufeff") for col in data.columns]
    if any(not c or c.lower().startswith("unnamed:") for c in data.columns):
        raise ValueError("All columns need descriptive, nonempty headers in the first row.")
    if len(set(c.casefold() for c in data.columns)) != len(data.columns):
        raise ValueError("Duplicate column names found. Give each dataset column a unique header.")
    data = data.dropna(how="all")
    if data.empty:
        raise ValueError("No non-empty data rows were found.")
    if len(data) > 20000:
        raise ValueError("Please upload 20,000 rows or fewer for the current embedded HTML renderer.")
    if len(data.columns) > 80:
        raise ValueError("The file has too many columns for a compact landing page. Keep up to 80 columns.")
    return data


def _numeric_values(series: pd.Series) -> tuple[pd.Series, bool]:
    """Parse consistent numeric columns, including comma, currency and percent strings."""
    if pd.api.types.is_bool_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
        return pd.Series(float("nan"), index=series.index), False
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce"), False
    as_text = series.astype("string").str.strip()
    percent_present = as_text.str.contains("%", regex=False, na=False).any()
    cleaned = (as_text.str.replace(r"^\((.+)\)$", r"-\1", regex=True)
               .str.replace(r"[,£$€%\s]", "", regex=True))
    numeric = pd.to_numeric(cleaned, errors="coerce")
    nonblank = as_text.notna() & as_text.ne("")
    # Do not turn IDs or names that merely contain a few digits into metrics.
    if nonblank.sum() == 0 or numeric.notna().sum() / nonblank.sum() < 0.85:
        return pd.Series(float("nan"), index=series.index), False
    return numeric, bool(percent_present)


def _pretty(header: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", header)).strip().title().replace("Pct", "%")


def _display(value: float, kind: str, prefix: str = "") -> str:
    x = f"{value:,.1f}" if abs(value) < 100 and value != int(value) else f"{value:,.0f}"
    if kind == "percent":
        return x + "%"
    if kind == "currency":
        return prefix + x
    return x


def infer_columns(df: pd.DataFrame):
    data = clean_dataframe(df)
    cols = []
    numeric: dict[str, pd.Series] = {}
    for key in data.columns:
        series = data[key]
        value_series, percent_in_values = _numeric_values(series)
        valid = int(value_series.notna().sum())
        ratio = valid / max(1, int(series.notna().sum()))
        is_number = valid > 0 and ratio >= 0.85 and not bool(re.search(r"(^|_)(id|zip|postcode)(_|$)", str(key), re.I))
        if is_number:
            if percent_in_values or re.search(r"percent|percentage|pct|%", key, re.I):
                kind = "percent"
            elif re.search(r"\b(cost|price|salary|spend|revenue|income|wage|payroll)\b", key.replace("_", " "), re.I) or series.astype("string").str.contains(r"[£$€]", regex=True, na=False).any():
                kind = "currency"
            elif value_series.dropna().mod(1).eq(0).all():
                kind = "integer"
            else:
                kind = "number"
            info = {"key": key, "label": _pretty(key), "type": kind}
            if kind == "currency":
                txt = series.astype("string")
                info["prefix"] = "£" if txt.str.contains("£", regex=False, na=False).any() else ("€" if txt.str.contains("€", regex=False, na=False).any() else "$")
            cols.append(info)
            numeric[key] = value_series
            data[key] = value_series
        else:
            cols.append({"key": key, "label": _pretty(key), "type": "text"})
            data[key] = data[key].map(lambda x: x.isoformat() if isinstance(x, (date, datetime)) else x)
    return data, cols, numeric


def make_blueprint(df: pd.DataFrame, file_name: str, instruction: str = "Build", *, metric_override: str | None = None, entity_override: str | None = None) -> dict:
    if check_required(instruction, file_name):
        raise ValueError(check_required(instruction, file_name))
    data, cols, numeric = infer_columns(df)
    potential = [k for k, s in numeric.items() if s.notna().sum() >= 2 and not IGNORED_METRICS.search(k)]
    if not potential:
        potential = [k for k, s in numeric.items() if s.notna().sum() >= 2]
    if not potential:
        raise ValueError("No usable numeric measure found. Add at least one numeric column with values in two or more rows.")
    potential.sort(key=lambda k: (not bool(METRIC_PREFERRED.search(k)), list(data.columns).index(k)))
    if metric_override:
        if metric_override not in potential:
            raise ValueError(f"Selected metric '{metric_override}' isn't a usable numeric column.")
        primary = metric_override
    else:
        primary = potential[0]
    text_keys = [c["key"] for c in cols if c["type"] == "text" and data[c["key"]].notna().sum() > 0]
    text_keys.sort(key=lambda k: (not bool(ENTITY_PREFERRED.search(k)), list(data.columns).index(k)))
    if entity_override and entity_override not in data.columns:
        raise ValueError("Selected record label does not match a dataset column.")
    entity = entity_override or (text_keys[0] if text_keys else "Record")
    if not text_keys and not entity_override:
        data.insert(0, "Record", [f"Record {i}" for i in range(1, len(data) + 1)])
        cols.insert(0, {"key": "Record", "label": "Record", "type": "text"})
    col_lookup = {c["key"]: c for c in cols}
    main = col_lookup[primary]
    metric_title = main["label"]
    labels = data[entity].fillna("Unlabelled").astype(str)
    values = numeric[primary]
    usable = values.dropna()
    if usable.empty:
        raise ValueError("The selected ranking metric contains no numeric data.")
    high_idx = usable.idxmax()
    low_idx = usable.idxmin()
    best_label = labels.loc[high_idx]
    low_label = labels.loc[low_idx]
    highest = _display(float(values.loc[high_idx]), main["type"], main.get("prefix", ""))
    lowest = _display(float(values.loc[low_idx]), main["type"], main.get("prefix", ""))
    median = _display(float(usable.median()), main["type"], main.get("prefix", ""))
    base = Path(file_name).stem.replace("_", " ").replace("-", " ")
    base = re.sub(r"\b(data|dataset|final|export|copy|sheet\d*)\b", "", base, flags=re.I).strip()
    title = re.sub(r"\s+", " ", base).title() if len(base) >= 7 else f"Ranking {entity.title()} by {metric_title}"
    # A prompt may supply an explicit one-line title but is not treated as NLP by this engine.
    override_title = re.search(r"(?:^|\n)\s*title\s*:\s*(.+)$", instruction, re.I | re.M)
    if override_title:
        title = override_title.group(1).strip()[:160] or title
    notes = (
        "This page is an automatically generated draft based only on the uploaded spreadsheet. "
        "The original sources, collection methods, date range, score definitions and any weightings "
        "were not supplied and must be checked and added before publication."
    )
    findings = [
        {"stat": highest, "headline": f"Highest {metric_title}: {best_label}", "copy": f"{best_label} has the highest recorded {metric_title.lower()} of {highest} in the uploaded dataset."},
        {"stat": lowest, "headline": f"Lowest {metric_title}: {low_label}", "copy": f"{low_label} has the lowest recorded {metric_title.lower()} of {lowest} among rows with numeric values."},
        {"stat": median, "headline": f"Median {metric_title}", "copy": f"The middle value across {len(usable):,} valid records is {median}."},
    ]
    sections = [
        {"type": "ranking", "nav_title": "Rankings", "title": f"{metric_title}: Highest to Lowest", "description": "Compare the recorded values; select Full Table to inspect every row.", "metric": primary, "limit": min(15, len(data)), "direction": "desc"},
        {"type": "metric_cards", "nav_title": "Snapshot", "title": "Numbers at a Glance", "description": "Descriptive summaries calculated directly from the uploaded spreadsheet.", "metrics": potential[:2]},
    ]
    if len(potential) >= 2:
        secondary = potential[1] if potential[0] == primary else potential[0]
        sections.append({"type": "comparison", "nav_title": "Comparison", "title": "How Two Indicators Compare", "description": f"Showing {metric_title} and {col_lookup[secondary]['label']} side by side, each on an independent scale.", "metrics": [primary, secondary], "limit": min(12, len(data))})
        if len(data) >= 7 and usable.nunique() > 1 and numeric[secondary].nunique() > 1:
            sections.append({"type": "scatter", "nav_title": "Relationship", "title": "Explore the Two Measures", "description": "View the distribution of records across the two measures. This chart does not establish causation.", "metrics": [primary, secondary]})
    if all(k in numeric for k in ("latitude", "longitude")):
        lat, lon = numeric["latitude"], numeric["longitude"]
        if (lat.between(-90, 90) & lon.between(-180, 180)).sum() > 0:
            sections.append({"type": "map", "nav_title": "Map", "title": "Geographic Distribution", "description": "Explore the coordinates supplied in the dataset.", "metric": primary})
    sections.append({"type": "heatmap", "nav_title": "Full Data", "title": "Explore Every Record", "description": "Search, sort and examine the complete supplied table.", "metric": primary})
    rows = json.loads(data.to_json(orient="records", date_format="iso", force_ascii=False))
    blueprint = {
        "schema_version": "1.0", "slug": jid(title), "title": title,
        "subtitle": f"An interactive breakdown of {len(data):,} records from the uploaded research file, ranked by {metric_title.lower()}.",
        "kicker": "Spreadsheet Analysis / Draft", "byline": "Research Data Preview",
        "overview_heading": "What the Uploaded Data Shows", "findings_heading": "Key Descriptive Findings",
        "summary": "These descriptive findings come from the uploaded file and require editorial review before publication.",
        "intro": [f"The uploaded dataset contains {len(data):,} records across {len(data.columns)} fields. The primary chart ranks records by {metric_title.lower()}, from highest to lowest.", notes],
        "hero_stats": [{"value": f"{len(data):,}", "label": "Records"}, {"value": f"{len(numeric):,}", "label": "Numeric Measures"}, {"value": highest, "label": f"Highest {metric_title}"}],
        "key_findings": findings,
        "entity_key": entity, "primary_metric": primary, "primary_label": metric_title,
        "columns": cols, "rows": rows,
        "simple": {"widget_title": f"{metric_title}: Full Ranking", "widget_description": "Toggle between ranked bars and the complete searchable data table.", "top_n": min(10, len(data)), "direction": "desc", "closing": "All results reflect the uploaded values. Verify their original sources and intended interpretation before publishing."},
        "detailed": {"sections": sections, "closing": "These visualizations describe patterns in the supplied data; they are not evidence of causation and do not validate the underlying research methods."},
        "methodology": {"summary": notes, "steps": [
            {"title": "Data Input", "text": f"Imported {len(data):,} non-empty rows from the user-uploaded file '{Path(file_name).name}'."},
            {"title": "Sorting & Summaries", "text": f"Ranked valid numerical values for {metric_title}; highest and lowest values and the median were calculated directly from the provided records."},
            {"title": "Editorial Verification", "text": "Before publication, insert the research's actual methodology, primary source links, time period, limitations and metric definitions."},
        ], "notes": ["Automated draft. No independent source verification or calculation-method audit was performed."], "sources": []},
        "review_notes": ["Automatically inferred ranking metric and record label; verify they match your intended story.", "Add documented source URLs and real methodology before publication."],
    }
    return blueprint
