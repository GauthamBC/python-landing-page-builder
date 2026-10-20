"""Landing Page Studio v4: brand-neutral JSON in, two brand-themed HTML pages out.

Deploy on Streamlit Community Cloud alongside landing_engine.py and requirements.txt.
No spreadsheet upload or AI API is required at runtime.
"""
from __future__ import annotations

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
st.caption("Upload one brand-neutral JSON blueprint. Choose the publication in the sidebar; both HTML pages update automatically.")


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
    "Do not specify a brand, hex colors, logos or CSS; choose the publication only inside Streamlit. "
    "Ensure the values align with 'entity_key', 'primary_metric', 'columns', and all detailed widget metric keys. "
    "Return valid JSON only, with no Markdown fences. Do not ask me to upload the spreadsheet to Streamlit."
)

st.subheader("1 · Upload your final JSON")
upload_tab, paste_tab = st.tabs(["Upload JSON", "Paste JSON"])
with upload_tab:
    uploaded = st.file_uploader(
        "Complete ChatGPT blueprint (.json or .txt)",
        type=["json", "txt"],
        help="One complete JSON containing editorial copy, methodology and all the ranking records inside 'rows'.",
    )
with paste_tab:
    pasted = st.text_area(
        "Or paste the full JSON",
        height=145,
        placeholder='{\n  "title": "...",\n  "visual_style": "editorial",\n  "rows": [{"Team": "...", "Score": 1.23}]\n}',
    )

# A neutral blueprint is reusable across all brands. A JSON upload must NEVER
# infer, reset, or override the user's publication choice (including from URLs).
# Session state persists when the input document changes.
source_bytes = uploaded.getvalue() if uploaded is not None else pasted.encode("utf-8")
if uploaded is not None and pasted.strip():
    st.caption("Using the uploaded file. Remove it to use pasted JSON instead.")

raw = None
parse_error = None
if source_bytes.strip():
    try:
        raw = parse_blueprint(source_bytes.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        parse_error = str(exc)

if "studio_brand" not in st.session_state:
    st.session_state["studio_brand"] = "Action Network"

with st.sidebar:
    st.header("Campaign Settings")
    brand = st.selectbox(
        "Publication Brand",
        list(BRANDS),
        key="studio_brand",
        help="The selected brand alone sets the page palette and lockup. Source URLs or old brand fields in JSON cannot change it.",
    )
    theme = BRANDS[brand]
    st.markdown(
        f'<div style="display:flex;gap:5px;margin:6px 0 12px">'
        + ''.join(f'<span style="width:46px;height:11px;background:{theme[k]};border-radius:3px"></span>' for k in ("primary", "bright", "navy"))
        + '</div>', unsafe_allow_html=True,
    )
    st.caption("Brand selection stays the same when you upload a different blueprint.")
    st.caption("Palette status: " + theme["note"])
    show_previews = st.toggle("Show HTML previews", value=True)
    with st.expander("Available widgets", expanded=False):
        st.markdown("**Implemented now:** ranking chart ↔ sortable table, heatmap table, two-metric comparison, scatterplot, numeric cards, point map (latitude/longitude), editorial callout.")
        st.caption("Specialized illustrated maps, advanced animated scenes, route diagrams and other designs from the HTML references have not all been ported to the engine.")

if not source_bytes.strip():
    st.info("Upload or paste one **self-contained JSON**. No spreadsheet or Build command is required.")
    st.stop()
if parse_error:
    st.error("Could not read the JSON: " + parse_error)
    st.stop()

st.subheader("2 · Your automatically generated landing pages")
st.caption(f"Campaign: **{raw.get('title') or 'Untitled'}** · Publication selected in Streamlit: **{brand}**")
legacy_brand_fields = {"brand", "publication_brand", "theme", "palette", "colors", "primary_color", "secondary_color", "accent_color", "brand_colors", "logo", "logo_url"}
if any(k in raw for k in legacy_brand_fields):
    st.info("This JSON has older branding fields. They are ignored. Only the Streamlit Publication Brand dropdown controls the page colors and brand lockup.")
try:
    ensure_embedded_rows(raw)
    spec = normalize(raw)
    if not spec.get("primary_metric"):
        raise ValueError("The blueprint has no 'primary_metric'. ChatGPT needs to specify the ranking metric.")
    metric = spec["primary_metric"]
    if not any(n(row.get(metric)) is not None for row in spec["rows"]):
        raise ValueError(f"The primary_metric '{metric}' has no numeric research values in 'rows'.")
    if not any(str(row.get(spec["entity_key"], "")).strip() for row in spec["rows"]):
        raise ValueError(f"There are no values for the entity_key '{spec['entity_key']}' in 'rows'.")
    warnings = validate(spec)
except (ValueError, UnicodeDecodeError, TypeError, KeyError) as exc:
    if raw.get("rows") == [] or "rows" not in raw:
        st.warning("Your JSON **is recognized** and its editorial content is readable. But it has **0 research rows**, so the generator cannot build the rankings or tables yet. This is a missing-data issue, not an upload issue.")
    st.error(str(exc))
    st.markdown("**One-time fix:** In the same ChatGPT Project conversation that has your research spreadsheet, paste this request, then upload the newly generated complete JSON here:")
    st.code(reminder, language=None)
    st.stop()

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

st.success(f"Generated both HTML pages from {len(spec['rows']):,} embedded records · {brand}.")
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
