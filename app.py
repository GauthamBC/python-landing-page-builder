"""Landing Page Studio v7.3 - Build / Widgets / Outputs.

Drop-in replacement for the existing repository's app.py.
Works with the original landing_engine.py and streamlit>=1.38,<3.

No AI API is called: research is handled externally by ChatGPT/Claude;
this app previews the actual engine's supported widgets and renders three
levels from a completed self-contained research JSON blueprint.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from landing_engine import BRANDS, WIDGET_TYPES, check_selected_page, jid, normalize, render, validate

st.set_page_config(page_title="Landing Page Studio", page_icon="📊", layout="wide")

# The widget gallery mirrors the CURRENT renderer, not hypothetical widgets.
# In particular, stand-alone line charts and donut charts are not yet implemented.
WIDGETS = [
    ("map", "Map", "Geographic pin map. Requires verified latitude and longitude.", "map"),
    ("table_ranking", "Ranking Table", "Sortable, searchable rankings with all source rows.", "ranking table"),
    ("ranking", "Ranking Bar Chart", "Animated ranking bars and a full-table toggle.", "bar chart"),
    ("comparison", "Comparison", "Compare two numeric measures side by side.", "comparison"),
    ("scatter", "Scatterplot", "Explore the relationship between two numeric measures.", "scatter"),
    ("heatmap", "Heatmap", "Highlight numeric patterns across ranked results.", "heatmap"),
    ("metric_cards", "Metric Cards", "Snapshot cards showing relevant numeric measures.", "kpi cards"),
    ("callout", "Editorial Callout", "A prominently styled editorial explanation.", "callout"),
]

# Exact aliases make 'Build (must - ranking table)' and similar instructions easy.
ALIASES = {
    "map": "map", "pin map": "map", "geographic map": "map",
    "ranking table": "table_ranking", "table": "table_ranking", "sortable table": "table_ranking",
    "ranking": "ranking", "ranking chart": "ranking", "ranking bar chart": "ranking",
    "bar chart": "ranking", "bar graph": "ranking",
    "comparison": "comparison", "comparison chart": "comparison",
    "scatter": "scatter", "scatterplot": "scatter", "scatter plot": "scatter",
    "heatmap": "heatmap", "heat map": "heatmap",
    "metric cards": "metric_cards", "metric card": "metric_cards",
    "kpi cards": "metric_cards", "kpi": "metric_cards", "stat cards": "metric_cards",
    "callout": "callout", "editorial callout": "callout",
}


def hex_mix_white(color: str, weight: float) -> str:
    return "#" + "".join(f"{round(int(color[i:i+2], 16) * weight + 255 * (1-weight)):02x}" for i in (1, 3, 5))


def colorized_svg(svg: str, primary: str, secondary: str) -> str:
    # This adapts existing static illustrations, keeping the preview lightweight.
    mapping = {
        "#e55046": primary, "#e95c50": primary, "#e5544e": primary,
        "#df4e49": primary, "#df5752": primary, "#e4554e": primary,
        "#e85f55": primary, "#ed7565": hex_mix_white(primary, .8),
        "#ffe3dc": hex_mix_white(primary, .15),
        "#f7a895": hex_mix_white(primary, .45),
        "#fbcbc0": hex_mix_white(primary, .25),
        "#f4a48f": hex_mix_white(primary, .5),
        "#f6b9aa": hex_mix_white(primary, .35),
        "#ffd5cb": hex_mix_white(primary, .25),
        "#243b53": secondary, "#223e53": secondary,
        "#273e51": secondary, "#263c50": secondary,
        "#456680": secondary, "#416c8a": secondary,
        "#446f8d": secondary, "#486276": secondary,
        "#c3d7e7": hex_mix_white(secondary, .20),
        "#98b4c9": hex_mix_white(secondary, .50),
        "#edf1f6": hex_mix_white(secondary, .08),
    }
    return re.sub(r"#[0-9a-fA-F]{6}", lambda m: mapping.get(m.group(0).lower(), m.group(0)), svg)


# These small SVG illustrations are examples, not fabricated research outputs.
# They're selected from the live renderer's implemented widget types.
ARTWORK = {'map': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f0f5fa"/><path d="M39 29L94 22L110 37L161 26L202 41L265 33L281 55L268 82L234 97L216 121L171 108L152 133L116 116L83 119L62 93L37 82L51 61Z" fill="#c3d7e7" stroke="#98b4c9" stroke-width="2"/><path d="M105 39L104 112M160 30L168 105M221 44L215 98M62 79L268 79" stroke="#ffffff" stroke-width="1.8" opacity=".85"/><g fill="#e55046" stroke="white" stroke-width="2"><circle cx="87" cy="72" r="8"/><circle cx="173" cy="57" r="8"/><circle cx="225" cy="80" r="8"/><circle cx="150" cy="100" r="8"/></g><path d="M228 18l7 3-6 9-10-2-6-8 6-6z" fill="#c3d7e7" opacity=".5"/><rect x="9" y="129" width="91" height="16" rx="6" fill="white"/><text x="17" y="140" font-size="10" font-family="Arial" fill="#486276">Interactive map</text></svg>', 'ranking table': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><rect x="14" y="13" width="292" height="27" rx="4" fill="#243b53"/><g font-family="Arial" font-size="11"><text x="24" y="31" fill="white">Rank</text><text x="91" y="31" fill="white">City</text><text x="262" y="31" fill="white">Score</text></g><g font-family="Arial" font-size="11" fill="#43546b"><rect x="14" y="43" width="292" height="25" rx="3" fill="#edf1f6"/><text x="28" y="60">01</text><text x="91" y="60">Seattle</text><text x="264" y="60">92.4</text><rect x="14" y="70" width="292" height="25" rx="3" fill="white"/><text x="28" y="87">02</text><text x="91" y="87">Denver</text><text x="264" y="87">88.7</text><rect x="14" y="97" width="292" height="25" rx="3" fill="#edf1f6"/><text x="28" y="114">03</text><text x="91" y="114">Boston</text><text x="264" y="114">85.1</text></g><path d="M90 40v82M246 40v82" stroke="#dce4ed"/></svg>', 'bar chart': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><g stroke="#dfe5ec"><path d="M35 28H295M35 56H295M35 84H295M35 112H295"/></g><g fill="#e95c50"><rect x="53" y="59" width="32" height="64" rx="4"/><rect x="102" y="33" width="32" height="90" rx="4"/><rect x="151" y="72" width="32" height="51" rx="4"/><rect x="200" y="45" width="32" height="78" rx="4"/><rect x="249" y="78" width="32" height="45" rx="4"/></g><path d="M35 123H296" stroke="#9cadbc" stroke-width="2"/><g fill="#5a7185" font-family="Arial" font-size="10"><text x="57" y="139">A</text><text x="107" y="139">B</text><text x="155" y="139">C</text><text x="204" y="139">D</text><text x="253" y="139">E</text></g></svg>', 'comparison': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><rect x="15" y="20" width="137" height="116" rx="9" fill="#fff" stroke="#d8e2ec"/><rect x="168" y="20" width="137" height="116" rx="9" fill="#fff" stroke="#d8e2ec"/><text x="31" y="43" font-family="Arial" font-weight="700" font-size="13" fill="#263c50">City A</text><text x="184" y="43" font-family="Arial" font-weight="700" font-size="13" fill="#263c50">City B</text><text x="31" y="74" font-family="Arial" font-size="30" font-weight="700" fill="#e5544e">87</text><text x="184" y="74" font-family="Arial" font-size="30" font-weight="700" fill="#456680">72</text><rect x="31" y="96" width="100" height="9" rx="5" fill="#ebf0f4"/><rect x="31" y="96" width="87" height="9" rx="5" fill="#e5544e"/><rect x="184" y="96" width="100" height="9" rx="5" fill="#ebf0f4"/><rect x="184" y="96" width="72" height="9" rx="5" fill="#456680"/><text x="31" y="121" font-family="Arial" font-size="10" fill="#607286">Compare metrics</text></svg>', 'scatter': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><g stroke="#dfe5ec"><path d="M35 20V123H296M35 91H294M35 59H294M35 27H294"/></g><g fill="#e5544e"><circle cx="55" cy="104" r="6"/><circle cx="84" cy="85" r="6"/><circle cx="116" cy="92" r="6"/><circle cx="149" cy="63" r="6"/><circle cx="183" cy="73" r="6"/><circle cx="223" cy="42" r="6"/><circle cx="270" cy="35" r="6"/></g><path d="M47 112L282 29" stroke="#416c8a" stroke-width="2.5" stroke-dasharray="6 6"/><g font-family="Arial" font-size="11" fill="#456680"><text x="38" y="143">Metric A</text><text x="238" y="143">Metric B</text></g></svg>', 'heatmap': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><g transform="translate(42 18)"><rect x="0" y="0" width="48" height="27" rx="3" fill="#ffe3dc"/><rect x="53" y="0" width="48" height="27" rx="3" fill="#f7a895"/><rect x="106" y="0" width="48" height="27" rx="3" fill="#ed7565"/><rect x="159" y="0" width="48" height="27" rx="3" fill="#fbcbc0"/><rect x="212" y="0" width="48" height="27" rx="3" fill="#df4e49"/><rect x="0" y="32" width="48" height="27" rx="3" fill="#f4a48f"/><rect x="53" y="32" width="48" height="27" rx="3" fill="#ffe3dc"/><rect x="106" y="32" width="48" height="27" rx="3" fill="#e85f55"/><rect x="159" y="32" width="48" height="27" rx="3" fill="#df4e49"/><rect x="212" y="32" width="48" height="27" rx="3" fill="#f6b9aa"/><rect x="0" y="64" width="48" height="27" rx="3" fill="#df4e49"/><rect x="53" y="64" width="48" height="27" rx="3" fill="#ed7565"/><rect x="106" y="64" width="48" height="27" rx="3" fill="#ffd5cb"/><rect x="159" y="64" width="48" height="27" rx="3" fill="#f4a48f"/><rect x="212" y="64" width="48" height="27" rx="3" fill="#f6b9aa"/></g><g font-family="Arial" font-size="10" fill="#667b8a"><text x="45" y="129">Mon</text><text x="99" y="129">Tue</text><text x="152" y="129">Wed</text><text x="204" y="129">Thu</text><text x="257" y="129">Fri</text></g></svg>', 'kpi cards': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><g><rect x="12" y="22" width="93" height="108" rx="8" fill="white" stroke="#dce5ec"/><rect x="113" y="22" width="93" height="108" rx="8" fill="white" stroke="#dce5ec"/><rect x="214" y="22" width="93" height="108" rx="8" fill="white" stroke="#dce5ec"/></g><g font-family="Arial"><text x="24" y="49" font-size="11" fill="#61768a">Cities</text><text x="24" y="84" font-weight="700" font-size="27" fill="#223e53">150</text><text x="125" y="49" font-size="11" fill="#61768a">Growth</text><text x="125" y="84" font-weight="700" font-size="27" fill="#e4554e">+22%</text><text x="225" y="49" font-size="11" fill="#61768a">Highest</text><text x="225" y="84" font-weight="700" font-size="27" fill="#223e53">91.2</text><text x="24" y="109" font-size="10" fill="#71859a">Coverage</text><text x="125" y="109" font-size="10" fill="#71859a">Year on year</text><text x="225" y="109" font-size="10" fill="#71859a">Index score</text></g></svg>', 'callout': '<svg viewBox="0 0 320 154" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="154" rx="9" fill="#f7f9fc"/><rect x="20" y="19" width="280" height="116" rx="9" fill="white" stroke="#d8e2ec"/><rect x="20" y="19" width="6" height="116" rx="3" fill="#e5544e"/><text x="43" y="53" font-family="Arial" font-size="15" font-weight="bold" fill="#243b53">What the numbers mean</text><rect x="43" y="68" width="225" height="7" rx="3" fill="#c3d7e7"/><rect x="43" y="84" width="210" height="7" rx="3" fill="#c3d7e7"/><rect x="43" y="100" width="170" height="7" rx="3" fill="#c3d7e7"/></svg>'}


def require_research_rows(raw: dict) -> None:
    datasets = raw.get("datasets")
    if datasets is not None:
        if not isinstance(datasets, list) or not datasets:
            raise ValueError("'datasets' must contain one or more nonempty research tables.")
        for index, dataset in enumerate(datasets, 1):
            if not isinstance(dataset, dict) or not isinstance(dataset.get("rows"), list) or not dataset["rows"]:
                raise ValueError(f"Dataset {index} has no rows. Include the full research records in the JSON.")
    elif not isinstance(raw.get("rows"), list) or not raw["rows"]:
        raise ValueError("The blueprint must include 'datasets[].rows' or legacy 'rows'.")
    if len(json.dumps(raw, ensure_ascii=False)) > 22_000_000:
        raise ValueError("Research JSON exceeds the existing 22 MB limit.")


def json_from_text(text: str) -> dict:
    text = text.strip().lstrip("\ufeff")
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("The blueprint must be a JSON object, not an array.")
    return parsed


def required_widgets(instruction: str) -> list[str]:
    text = instruction.strip()
    if not text or text.lower() == "build":
        return []
    match = re.fullmatch(r"build\s*\(\s*must\s*[-:]\s*(.*?)\s*\)\s*", text, flags=re.I | re.S)
    if not match:
        raise ValueError("Use 'Build' or 'Build (must - map, ranking table)'. There is no Desired option.")
    terms = [x.strip().lower().replace("_", " ").replace("-", " ") for x in match.group(1).split(",")]
    if not all(terms):
        raise ValueError("Include a widget name after 'must -'.")
    unknown = [x for x in terms if x not in ALIASES]
    if unknown:
        raise ValueError("Unsupported widget: " + ", ".join(unknown) + ". Choose a name from the Widgets tab.")
    return list(dict.fromkeys(ALIASES[x] for x in terms))


def to_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def available_metrics(dataset: dict) -> list[str]:
    rows = dataset["rows"]
    names = list(dict.fromkeys([c["key"] for c in dataset["columns"]] + [key for row in rows for key in row]))
    return [key for key in names if any(to_float(row.get(key)) is not None for row in rows) and key not in ("latitude", "longitude")]


def has_coordinates(dataset: dict) -> bool:
    for row in dataset["rows"]:
        lat, lon = to_float(row.get("latitude")), to_float(row.get("longitude"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            return True
    return False


def new_section(widget: str, dataset: dict, metrics: list[str]) -> dict:
    title = {
        "ranking": dataset["title"] + " Rankings",
        "table_ranking": dataset["title"] + " Full Results",
        "map": "Geographic Results",
        "comparison": "Compare Two Measures",
        "scatter": "How Two Measures Relate",
        "heatmap": "Results Heatmap",
        "metric_cards": "Key Measures",
        "callout": "What the Data Reveals",
    }[widget]
    result = {"type": widget, "dataset_id": dataset["id"], "title": title,
              "metric": dataset["primary_metric"], "limit": 12}
    if widget in ("comparison", "scatter"):
        result["metrics"] = metrics[:2]
    if widget == "metric_cards":
        result["metrics"] = metrics[:3]
    if widget == "callout":
        result["text"] = dataset.get("description") or "See the study findings and methodology for context."
    return result


def feasible(widget: str, dataset: dict, metrics: list[str]) -> bool:
    if widget == "map":
        return has_coordinates(dataset)
    if widget in ("comparison", "scatter"):
        return len(metrics) >= 2
    if widget == "metric_cards":
        return len(metrics) >= 1
    return True


def three_versions(spec: dict, required: list[str]) -> dict[str, dict]:
    """Construct different presentations from ONE verified dataset, no fabricated values.

    v6 engine's 'selected' mode is reused; the outdated template gallery is
    not exposed to the user. No engine change is needed in this UI phase.
    """
    datasets = spec["datasets"]
    primary = datasets[0]
    primary_metrics = available_metrics(primary)
    for widget in required:
        if not feasible(widget, primary, primary_metrics):
            if widget == "map":
                raise ValueError("'Map - Must' requires verified numeric latitude and longitude in the research JSON. No locations will be invented.")
            raise ValueError(f"'{widget}' cannot be built from the available numeric measures. Check the research JSON.")
    variants = {}
    for level in ("Simple", "Standard", "Detailed"):
        page = copy.deepcopy(spec)
        page["visual_style"] = {"Simple": "minimal", "Standard": "editorial", "Detailed": "bold"}[level]
        if level == "Simple":
            page["intro"] = page.get("intro", [])[:1]
            page["key_findings"] = page.get("key_findings", [])[:3]
        elif level == "Standard":
            page["intro"] = page.get("intro", [])[:2]
            page["key_findings"] = page.get("key_findings", [])[:5]
        sections = []
        seen = set()
        def add(widget: str, ds: dict, *, mandatory: bool = False):
            metrics = available_metrics(ds)
            if not feasible(widget, ds, metrics):
                return
            key = (ds["id"], widget)
            if key in seen:
                return
            seen.add(key)
            sections.append(new_section(widget, ds, metrics))
        # One ranking/chart widget per ranked dataset always ensures complete access.
        for dataset in datasets:
            add("ranking", dataset)
        # Must means present in ALL three outputs, where source columns permit it.
        for widget in required:
            add(widget, primary, mandatory=True)
        if level in ("Standard", "Detailed"):
            for widget in ("map", "comparison", "metric_cards", "heatmap"):
                if len(sections) >= (3 if level == "Standard" else 4):
                    break
                add(widget, primary)
        if level == "Detailed":
            for widget in ("heatmap", "scatter", "table_ranking", "metric_cards", "callout"):
                add(widget, primary)
        page["page"] = {"sections": sections}
        page["template"] = {
            "template_id": "custom", "widgets": list(dict.fromkeys(x["type"] for x in sections)),
            "depth": "deep" if level == "Detailed" else "quick", "visual_style": page["visual_style"],
        }
        check_selected_page(page)
        variants[level] = page
    return variants


st.markdown("""<style>
.block-container{max-width:1440px;padding-top:1.8rem}
.stTabs [data-baseweb="tab"]{font-weight:700;font-size:17px}
.brand-bar{border-radius:13px;padding:17px 24px;margin:5px 0 22px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.brand-bar b{font:900 24px Arial,sans-serif;letter-spacing:-.8px}
.brand-bar span{font-size:13px;opacity:.82}
.widget-illustration svg{width:100%;display:block;height:auto;max-height:165px;background:#f7f9fa;border-radius:8px}
.widget-label{font-weight:750;font-size:16px;margin:9px 0 2px}
.widget-description{font-size:13px;color:#627386;min-height:36px}
.sample-command{font:12px monospace;padding:7px 9px;border-radius:5px;display:inline-block;margin-top:3px}
</style>""", unsafe_allow_html=True)

st.title("Landing Page Studio")
st.caption("One research study. Three levels of storytelling. No templates to choose.")

with st.sidebar:
    st.header("Publication Brand")
    brand = st.selectbox("Brand", options=list(BRANDS), label_visibility="collapsed", key="studio_brand")
    theme = BRANDS[brand]
    primary, secondary = theme["primary"], theme["navy"]
    st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:9px">
    <div style="padding:10px;background:white;border:1px solid #dfe5ec;border-radius:9px;color:#273340">
    <div style="height:22px;border-radius:5px;background:{primary}"></div>
    <small>PRIMARY</small><br><b>{primary}</b></div>
    <div style="padding:10px;background:white;border:1px solid #dfe5ec;border-radius:9px;color:#273340">
    <div style="height:22px;border-radius:5px;background:{secondary}"></div>
    <small>SECONDARY</small><br><b>{secondary}</b></div></div>""", unsafe_allow_html=True)
    st.caption("Both the widget gallery and the generated HTML use the selected publication's renderer palette.")
    if brand != "Action Network":
        st.caption("Note: the existing renderer marks this publication's palette as provisional until approved brand assets are supplied.")
    st.divider()
    st.caption("v7.3 · No AI API · Existing landing_engine.py and requirements.txt unchanged")

# Keep Streamlit menus neutral (native Windows menu selection may remain blue).
st.markdown(f"""<div class="brand-bar" style="background:{secondary};color:white;border-bottom:4px solid {primary}">
<b>{escape(theme['wordmark'])}</b><span>Research landing page studio · brand-matched widget previews</span>
</div>""", unsafe_allow_html=True)

build_tab, widgets_tab, output_tab = st.tabs(["Build", "Widgets", "Outputs"])

with build_tab:
    st.subheader("Build your landing pages")
    st.write("No template choice. Just your research and any mandatory widgets.")
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        with st.container(border=True):
            source = st.file_uploader("Research file", type=["csv", "xlsx", "xls", "txt"], key="research_upload")
            command = st.text_input("Build instruction (optional)", value="Build", key="build_instruction",
                                    help="Example: Build (must - map, ranking table)")
            try:
                demanded = required_widgets(command)
                if demanded:
                    st.caption("Required in all versions: " + ", ".join(next(x[1] for x in WIDGETS if x[0] == widget) for widget in demanded))
                else:
                    st.caption("No mandatory widgets. The builder will choose suitable options.")
            except ValueError as error:
                st.error(str(error))
            st.markdown("**Instruction to use in ChatGPT or Claude**")
            st.code(command.strip() or "Build", language="text")
            st.caption("Upload the research file in your AI conversation and use this instruction. Then download the completed research JSON and open Outputs. AI automation is a future stage.")
            if source:
                st.success(f"Selected: {source.name}. This file is not analysed locally in the current no-API version.")
    with right:
        with st.container(border=True):
            st.markdown("#### Your three outputs")
            st.markdown("**Simple**  \nOne main ranking/widget and concise findings. Mandatory widgets are added.")
            st.markdown("**Standard**  \nUsually 2–3 data widgets with more context.")
            st.markdown("**Detailed**  \nMore relevant widgets, deeper breakdowns and expanded findings.")
            st.caption("All levels use the same verified research data. Unsupported mandatory widgets are reported, never silently removed.")

with widgets_tab:
    st.subheader("Explore widgets")
    st.write(f"The examples below use **{brand}** colours. Add any widget name to `Build (must - ...)` if it should appear in every output.")
    for start in range(0, len(WIDGETS), 3):
        columns = st.columns(3, gap="medium")
        for col, (widget_id, title, explanation, art_key) in zip(columns, WIDGETS[start:start+3]):
            with col:
                with st.container(border=True):
                    svg = colorized_svg(ARTWORK[art_key], primary, secondary)
                    st.markdown(f'<div class="widget-illustration">{svg}</div>', unsafe_allow_html=True)
                    st.markdown(f"<div class='widget-label'>{title}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='widget-description'>{explanation}</div>", unsafe_allow_html=True)
                    st.markdown(f'<code class="sample-command" style="background:{hex_mix_white(primary, .12)};color:{secondary}">Build (must - {title.lower()})</code>', unsafe_allow_html=True)
    st.caption("Previews are illustrative. Only widget types implemented in your existing landing_engine.py are offered.")

with output_tab:
    st.subheader("Generate your three versions")
    st.write("Upload the completed self-contained JSON from your AI research conversation. The existing Python engine will render Simple, Standard and Detailed HTML files.")
    uploaded = st.file_uploader("Final research JSON", type=["json", "txt"], key="blueprint_upload")
    pasted = ""
    with st.expander("Or paste JSON instead"):
        pasted = st.text_area("Research JSON", height=170, key="blueprint_paste", label_visibility="collapsed")
    text_json = uploaded.getvalue().decode("utf-8-sig") if uploaded else pasted
    data_signature = hashlib.sha256((text_json + brand + st.session_state.get("build_instruction", "Build")).encode("utf-8")).hexdigest()
    if st.button("Generate 3 Versions", type="primary", use_container_width=True):
        if not text_json.strip():
            st.warning("Upload or paste a completed research JSON first.")
        else:
            try:
                necessary = required_widgets(st.session_state.get("build_instruction", "Build"))
                raw = json_from_text(text_json)
                require_research_rows(raw)
                spec = normalize(raw)
                variants = three_versions(spec, necessary)
                final_html = {name: render(page, brand, mode="selected") for name, page in variants.items()}
                st.session_state["rendered_html"] = final_html
                st.session_state["rendered_signature"] = data_signature
                st.session_state["rendered_slug"] = jid(spec.get("slug") or spec["title"])
                st.session_state["rendered_warnings"] = validate(spec)
            except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
                st.session_state.pop("rendered_html", None)
                st.error(str(exc))
            except Exception as exc:
                st.session_state.pop("rendered_html", None)
                st.error(f"Rendering failed: {type(exc).__name__}: {exc}")
    if st.session_state.get("rendered_signature") == data_signature and "rendered_html" in st.session_state:
        html_by_level = st.session_state["rendered_html"]
        st.success("Three HTML versions generated from your research JSON. Review the figures and sources before publishing.")
        for msg in st.session_state.get("rendered_warnings", []):
            st.warning(msg)
        tabs = st.tabs(["Simple", "Standard", "Detailed"])
        for tab, level in zip(tabs, ("Simple", "Standard", "Detailed")):
            with tab:
                html = html_by_level[level]
                st.download_button(f"Download {level} HTML", data=html,
                                   file_name=f"{st.session_state['rendered_slug']}-{jid(brand)}-{level.lower()}.html",
                                   mime="text/html", type="primary", use_container_width=True,
                                   key=f"download_{level}")
                components.html(html, height=900, scrolling=True)
    else:
        st.info("No current outputs. Upload the completed JSON and click Generate 3 Versions.")
    st.caption("This release does not automatically write AI copy. New instructions/AI connection and deeper renderer upgrades are intentionally postponed.")
