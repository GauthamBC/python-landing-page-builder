"""Landing Page Studio v2 — spreadsheet first, instruction required, two HTML outputs."""
from __future__ import annotations

import base64
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yaml

from auto_blueprint import check_required, infer_columns, make_blueprint
from landing_engine import BRANDS, jid, normalize, render, validate

st.set_page_config(page_title="Landing Page Studio", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.8rem;max-width:1440px}h1,h2,h3{letter-spacing:-.025em}
.stDownloadButton button{border-radius:5px;font-weight:700}
</style>""", unsafe_allow_html=True)

st.title("Landing Page Studio")
st.caption("Upload a CSV or Excel spreadsheet + type Build → get two branded interactive HTML pages")

with st.sidebar:
    st.header("Campaign Settings")
    brand = st.selectbox("Publication Brand", list(BRANDS), index=0)
    palette = BRANDS[brand]
    st.markdown(f'<div style="display:flex;gap:5px;margin:5px 0 12px"><span style="background:{palette["primary"]};height:14px;flex:1;border-radius:3px"></span><span style="background:{palette["bright"]};height:14px;flex:1;border-radius:3px"></span><span style="background:{palette["navy"]};height:14px;flex:1;border-radius:3px"></span></div>', unsafe_allow_html=True)
    if brand != "Action Network":
        st.caption("Other-brand palettes and text logos are provisional; replace with approved assets before publishing.")
    logo_file = st.file_uploader("Optional Approved Logo", type=["svg", "png", "webp"])
    show_preview = st.toggle("Show HTML Preview", value=True)
    st.divider()
    st.caption("No AI API or JSON file is needed for the default spreadsheet-only mode. A creative JSON blueprint is optional below.")

left, right = st.columns([1.1, .9], gap="large")
with left:
    st.subheader("1 · Upload your spreadsheet")
    data_file = st.file_uploader("Research file (required)", type=["csv", "xls", "xlsx"], help="CSV, legacy Excel .xls, and Excel .xlsx are supported. A header row and at least one numeric measure are required.")
    sheet_name = None
    if data_file is not None and data_file.name.lower().endswith((".xls", ".xlsx")):
        try:
            excel = pd.ExcelFile(BytesIO(data_file.getvalue()))
            sheet_name = st.selectbox("Choose worksheet", excel.sheet_names)
        except Exception as ex:
            st.error(f"Cannot read the Excel workbook: {ex}. For .xls files, install the xlrd dependency from requirements.txt.")
            st.stop()
    st.subheader("2 · Tell the generator what to do")
    instruction = st.text_area("Instruction (required)", placeholder="Build", height=90, help="Type Build or Build landing pages. Optionally add a second line 'Title: Your campaign headline'.")
    st.caption("Both inputs are required. The Build button stays disabled until a spreadsheet is uploaded and your instruction begins with 'Build' or 'Generate'.")

    with st.expander("Optional · Creative-project JSON blueprint (advanced)"):
        st.caption("For editorial copy written in your ChatGPT/Claude Project, enable this option and supply its JSON output. A spreadsheet is still mandatory.")
        use_custom = st.checkbox("Use creative editorial blueprint instead of automatic spreadsheet copy", value=False)
        blueprint_upload = None
        blueprint_text = ""
        if use_custom:
            blueprint_upload = st.file_uploader("Blueprint (.json, .yaml, .txt)", type=["json", "yaml", "yml", "txt"], key="custom_brief")
            blueprint_text = st.text_area("Or paste the blueprint", placeholder="{\n  \"title\": \"...\"\n}", height=120)

    data = None
    columns = []
    numerical = []
    entity_candidates = []
    upload_error = None
    if data_file is not None:
        try:
            if data_file.name.lower().endswith(".csv"):
                try:
                    data = pd.read_csv(BytesIO(data_file.getvalue()), encoding="utf-8-sig")
                except UnicodeDecodeError:
                    data = pd.read_csv(BytesIO(data_file.getvalue()), encoding="cp1252")
            else:
                data = pd.read_excel(BytesIO(data_file.getvalue()), sheet_name=sheet_name)
            inferred, columns, numeric_map = infer_columns(data)
            numerical = [k for k in numeric_map if numeric_map[k].notna().sum() >= 2]
            entity_candidates = [c["key"] for c in columns if c["type"] == "text"]
            st.success(f"Loaded {len(inferred):,} data rows and {len(inferred.columns):,} columns from {data_file.name}.")
            with st.expander("Dataset Preview · First 8 Rows"):
                st.dataframe(inferred.head(8), use_container_width=True)
        except Exception as ex:
            upload_error = str(ex)
            st.error(f"Spreadsheet problem: {upload_error}")

    with st.expander("Optional · Choose metric and record label"):
        st.caption("Leave both as Auto unless the spreadsheet's most important measure is not obvious.")
        primary_override = st.selectbox("Primary ranking metric", ["Auto"] + numerical) if numerical else "Auto"
        entity_override = st.selectbox("Record label", ["Auto"] + entity_candidates) if entity_candidates else "Auto"

    problem = check_required(instruction, data_file.name if data_file else None)
    if data_file is None:
        st.info("Upload a CSV, XLS or XLSX file to get started.")
    elif not instruction.strip():
        st.info("Now type Build in the instruction box.")
    elif problem:
        st.warning(problem)
    if not numerical and data_file is not None and not upload_error:
        st.warning("This file needs at least one numeric column with values in two or more rows.")
    has_custom = bool(blueprint_upload is not None or blueprint_text.strip()) if use_custom else True
    enabled = problem is None and data is not None and not upload_error and bool(numerical) and has_custom
    generate = st.button("Build Both Landing Pages", type="primary", use_container_width=True, disabled=not enabled)

with right:
    st.subheader("What you'll get")
    st.markdown("**Quick Read** — concise findings, one main chart / full-table toggle, plus methodology.\n\n**Deep Dive** — longer editorial layout with ranking, full data, metrics, and additional charts when relevant columns exist.")
    st.info("**Accuracy note:** Spreadsheet-only mode can identify descriptive results and create visualizations, but it cannot know the actual study's sources, weighting, definitions or editorial angle. Its output is clearly marked as a draft and requires review before publishing.")
    st.markdown("**Tip:** When you want a properly written editorial story, attach the dataset to your ChatGPT Project and ask it to generate a custom blueprint. Paste that output into the optional advanced panel.")

if generate:
    try:
        if use_custom:
            text = blueprint_upload.getvalue().decode("utf-8-sig") if blueprint_upload is not None else blueprint_text
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                raw = yaml.safe_load(text)
            if not isinstance(raw, dict):
                raise ValueError("Your custom blueprint must be one JSON/YAML object.")
            inferred, inferred_columns, _ = infer_columns(data)
            raw["rows"] = json.loads(inferred.to_json(orient="records", date_format="iso", force_ascii=False))
            if not raw.get("columns"):
                raw["columns"] = inferred_columns
        else:
            raw = make_blueprint(data, data_file.name, instruction,
                metric_override=None if primary_override == "Auto" else primary_override,
                entity_override=None if entity_override == "Auto" else entity_override)
        spec = normalize(raw)
        warnings = validate(spec)
        logo_uri = None
        if logo_file is not None:
            ext = logo_file.name.lower().rsplit(".", 1)[-1]
            mime = {"svg": "image/svg+xml", "png": "image/png", "webp": "image/webp"}[ext]
            logo_uri = f"data:{mime};base64,{base64.b64encode(logo_file.getvalue()).decode('ascii')}"
        simple_html = render(spec, brand, "simple", logo_uri)
        detailed_html = render(spec, brand, "detailed", logo_uri)
        base = f"{jid(spec['slug'])}-{jid(brand)}"
        package = BytesIO()
        with ZipFile(package, "w", ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{base}-quick-read.html", simple_html)
            zip_file.writestr(f"{base}-deep-dive.html", detailed_html)
            zip_file.writestr(f"{base}-blueprint.json", json.dumps(spec, indent=2, ensure_ascii=False))
        digest = sha256(data_file.getvalue() + (sheet_name or "").encode() + instruction.encode() + brand.encode() + str(primary_override).encode() + str(entity_override).encode() + (logo_file.getvalue() if logo_file else b"") + (blueprint_upload.getvalue() if use_custom and blueprint_upload else blueprint_text.encode() if use_custom else b"")).hexdigest()
        st.session_state["built"] = dict(digest=digest, base=base, spec=spec, warnings=warnings, quick=simple_html, deep=detailed_html, package=package.getvalue(), brand=brand)
    except Exception as ex:
        st.session_state.pop("built", None)
        st.error(f"Could not build landing pages: {ex}")

result = st.session_state.get("built")
if result is not None and enabled:
    current_digest = sha256(data_file.getvalue() + (sheet_name or "").encode() + instruction.encode() + brand.encode() + str(primary_override).encode() + str(entity_override).encode() + (logo_file.getvalue() if logo_file else b"") + (blueprint_upload.getvalue() if use_custom and blueprint_upload else blueprint_text.encode() if use_custom else b"")).hexdigest()
    if result["digest"] == current_digest:
        st.divider()
        st.success(f"Both versions generated · {len(result['spec']['rows']):,} records · {brand}")
        for warning in result["warnings"]:
            st.warning(warning)
        if not use_custom:
            st.warning("Draft output: source attribution and research methodology need human verification before publication.")
        st.subheader("3 · Preview and download")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("↓ Quick Read HTML", result["quick"], f"{result['base']}-quick-read.html", mime="text/html", use_container_width=True)
        with c2:
            st.download_button("↓ Deep Dive HTML", result["deep"], f"{result['base']}-deep-dive.html", mime="text/html", use_container_width=True)
        with c3:
            st.download_button("↓ Both + Blueprint ZIP", result["package"], f"{result['base']}-package.zip", mime="application/zip", use_container_width=True)
        if show_preview:
            t1, t2 = st.tabs(["Quick Read Preview", "Deep Dive Preview"])
            with t1:
                components.html(result["quick"], height=750, scrolling=True)
            with t2:
                components.html(result["deep"], height=750, scrolling=True)
        st.caption("Pages are standalone HTML. Google Fonts and some optional map/export resources require internet access. Check accuracy and mobile layout before publishing.")
