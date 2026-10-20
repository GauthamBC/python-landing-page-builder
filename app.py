"""Landing Page Studio v3: one self-contained JSON blueprint in, two HTML pages out.

Deploy on Streamlit Community Cloud alongside landing_engine.py and requirements.txt.
No spreadsheet upload or AI API is required at runtime.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
import re
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st
import streamlit.components.v1 as components

from landing_engine import BRANDS, jid, normalize, render, validate, n

st.set_page_config(page_title="Landing Page Studio", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.8rem;max-width:1380px}
h1,h2,h3{letter-spacing:-.025em}
.stDownloadButton button{font-weight:700;border-radius:5px}
</style>""", unsafe_allow_html=True)

st.title("Landing Page Studio")
st.caption("Upload or paste one complete ChatGPT JSON blueprint. Both interactive HTML pages generate automatically.")


def parse_blueprint(source_text: str) -> dict:
    """Strict JSON only, with optional removal of Markdown code fences."""
    source_text = source_text.lstrip("\ufeff").strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", source_text, flags=re.I | re.S)
    if fence:
        source_text = fence.group(1).strip()
    try:
        result = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}") from exc
    if not isinstance(result, dict):
        raise ValueError("The blueprint must be a single JSON object, not an array or plain text.")
    return result


def brand_from_blueprint(raw: dict) -> tuple[str, bool]:
    """Use an explicit brand first; fall back to clearly identifiable source links."""
    specified = str(raw.get("brand") or raw.get("publication_brand") or "").strip()
    for candidate in BRANDS:
        if specified.casefold() == candidate.casefold():
            return candidate, True
    aliases = {
        "actionnetwork": "Action Network",
        "vegasinsider": "VegasInsider",
        "rotogrinders": "RotoGrinders",
        "canadasportsbetting": "Canada Sports Betting",
    }
    simple = re.sub(r"[^a-z]", "", specified.casefold())
    if simple in aliases:
        return aliases[simple], True
    # Existing v2 blueprints did not have brand; infer ONLY from linked publisher domains.
    for item in (raw.get("methodology") or {}).get("sources", []):
        url = item.get("url", "") if isinstance(item, dict) else ""
        url = str(url).casefold()
        for domain, candidate in (
            ("canadasportsbetting.ca/", "Canada Sports Betting"),
            ("actionnetwork.com/", "Action Network"),
            ("vegasinsider.com/", "VegasInsider"),
            ("rotogrinders.com/", "RotoGrinders"),
        ):
            if domain in url:
                return candidate, True
    return "Action Network", False


def ensure_embedded_rows(raw: dict) -> None:
    """Never render an attractive but misleading empty ranking."""
    rows = raw.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "This blueprint has no embedded research rows (it contains 'rows': [] or is missing 'rows'). "
            "Your older ChatGPT instructions deliberately omitted the dataset. "
            "Ask ChatGPT to regenerate the JSON with ALL rows from your uploaded spreadsheet inside the 'rows' array. "
            "You do not need to upload the spreadsheet to Streamlit."
        )
    if any(not isinstance(r, dict) for r in rows):
        raise ValueError("Every entry in 'rows' must be a JSON object containing column names and values.")
    if not any(any(n(v) is not None for v in row.values()) for row in rows):
        raise ValueError("The embedded 'rows' need at least one numeric research column to build charts.")
    if len(json.dumps(rows)) > 20_000_000:
        raise ValueError("The embedded dataset exceeds the supported 20 MB limit; create a smaller publication dataset in ChatGPT.")


reminder = (
    "Please regenerate the SAME blueprint as a single, self-contained JSON file. "
    "Keep the existing editorial copy, accurate findings, methodology, sources and widget sections. "
    "Include every actual record from the primary uploaded Excel/CSV research sheet inside the top-level 'rows' array, "
    "using the exact original column names, with numbers as JSON numbers (not formatted strings). "
    "Do not leave 'rows' empty, do not use ellipses or sample/placeholder data, and do not invent missing values. "
    "Set the top-level 'brand' to the correct publication brand. "
    "Ensure the values align with 'entity_key', 'primary_metric', 'columns', and all detailed widget metric keys. "
    "Return valid JSON only, with no Markdown fences. Do not ask me to upload the spreadsheet to Streamlit."
)

st.subheader("Your completed campaign blueprint")
upload_tab, paste_tab = st.tabs(["Upload JSON", "Paste JSON"])
with upload_tab:
    uploaded = st.file_uploader("Final ChatGPT blueprint (.json or .txt)", type=["json", "txt"], help="The file must contain both editorial content and the research rows.")
with paste_tab:
    pasted = st.text_area("Or paste the complete JSON", height=145, placeholder='{\n  "brand": "Action Network",\n  "title": "...",\n  "rows": [{"Team": "...", "Score": 1.23}]\n}')

# Prefer the uploaded file when both channels are populated.
source_bytes = uploaded.getvalue() if uploaded is not None else pasted.encode("utf-8")
if uploaded is not None and pasted.strip():
    st.caption("Using the uploaded file. Remove it if you want to use the pasted JSON instead.")

if not source_bytes.strip():
    st.info("Upload your finished JSON file above, or paste the JSON. No Excel/CSV upload or Build command is required here.")
    st.stop()

try:
    raw = parse_blueprint(source_bytes.decode("utf-8-sig"))
    ensure_embedded_rows(raw)
    spec = normalize(raw)
    if not spec.get("primary_metric"):
        raise ValueError("The blueprint has no primary_metric. Ask ChatGPT to specify the ranking metric.")
    metric = spec["primary_metric"]
    if not any(n(row.get(metric)) is not None for row in spec["rows"]):
        raise ValueError(f"The primary_metric '{metric}' has no numeric data in the embedded rows.")
    if not any(str(row.get(spec["entity_key"], "")).strip() for row in spec["rows"]):
        raise ValueError(f"No row has a value for entity_key '{spec['entity_key']}'.")
    warnings = validate(spec)
except (ValueError, UnicodeDecodeError, TypeError, KeyError) as exc:
    st.error(f"Cannot generate these landing pages: {exc}")
    st.caption("For older JSON blueprints with empty rows, copy the instruction below into the ChatGPT Project that already has your spreadsheet.")
    st.code(reminder, language=None)
    st.stop()

selected_brand, identified = brand_from_blueprint(raw)
with st.expander("Brand and preview settings", expanded=False):
    brand = st.selectbox("Publication brand", list(BRANDS), index=list(BRANDS).index(selected_brand), help="Automatically read from the JSON when provided. You can override it here.")
    show_previews = st.checkbox("Show interactive previews", value=True)
    if not identified:
        st.warning("No recognized publication brand was found in the blueprint. Defaulting to Action Network; choose the correct brand above.")
    if brand != "Action Network":
        st.caption("Non-Action Network colors and text lockups are provisional. Add approved brand assets before publication.")

try:
    quick_html = render(spec, brand, "simple")
    deep_html = render(spec, brand, "detailed")
    base = f"{jid(spec.get('slug') or spec['title'])}-{jid(brand)}"
    package = BytesIO()
    with ZipFile(package, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"{base}-quick-read.html", quick_html)
        archive.writestr(f"{base}-deep-dive.html", deep_html)
        archive.writestr(f"{base}-blueprint.json", json.dumps(spec, ensure_ascii=False, indent=2))
except Exception as exc:
    st.error(f"The renderer could not build this blueprint: {exc}")
    st.stop()

st.success(f"Ready: both HTML pages generated automatically from {len(spec['rows']):,} embedded records. Brand: {brand}.")
for warning in warnings:
    st.warning(warning)

quick_col, deep_col, pack_col = st.columns(3)
with quick_col:
    st.download_button("Download Quick Read HTML", quick_html, file_name=f"{base}-quick-read.html", mime="text/html", use_container_width=True)
with deep_col:
    st.download_button("Download Deep Dive HTML", deep_html, file_name=f"{base}-deep-dive.html", mime="text/html", use_container_width=True)
with pack_col:
    st.download_button("Download Both + JSON", package.getvalue(), file_name=f"{base}-package.zip", mime="application/zip", use_container_width=True)

if show_previews:
    quick_tab, deep_tab = st.tabs(["Quick Read Preview", "Deep Dive Preview"])
    with quick_tab:
        components.html(quick_html, height=750, scrolling=True)
    with deep_tab:
        components.html(deep_html, height=750, scrolling=True)
st.caption("The output is a draft until figures, methodology, sources and mobile presentation are checked. Web fonts and interactive map tiles require internet access.")
