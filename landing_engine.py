"""Deterministic, brand-aware renderer of brand-neutral research blueprints.

No LLM or server calls in rendering. Every output is self-contained HTML/CSS/JS
except Google Fonts and OpenStreetMap/Leaflet (only required for map widgets).
"""
from __future__ import annotations
import copy
import html
import json
import math
import re
import unicodedata
from urllib.parse import urlparse

BRANDS = {
    # Action Network tokens are taken from the campaign HTML supplied as references.
    "Action Network": dict(primary="#00b67a", bright="#00e09a", dark="#00865b", navy="#101820", navy2="#152630", soft="#e8fff6", wordmark="ACTION NETWORK", note="Theme based on supplied Action Network HTML. Text/vector lockup is not an approved logo asset."),
    # The following are directionally correct starter palettes, NOT an assertion
    # that the exact brand guideline hex codes or official logos are available.
    "VegasInsider": dict(primary="#cf9b31", bright="#f2c45d", dark="#866010", navy="#101214", navy2="#262421", soft="#fff6dd", wordmark="VEGASINSIDER", note="Provisional gold/black theme; replace with approved hex values and actual VegasInsider logo."),
    "RotoGrinders": dict(primary="#258ac8", bright="#64c5f5", dark="#126296", navy="#101c2b", navy2="#20364e", soft="#eaf6ff", wordmark="ROTOGRINDERS", note="Provisional blue theme; replace with approved hex values and actual RotoGrinders logo."),
    "Canada Sports Betting": dict(primary="#d71931", bright="#ff6573", dark="#a10a20", navy="#131516", navy2="#282b2d", soft="#fff0f2", wordmark="CANADA SPORTS BETTING", note="Provisional red/black theme; replace with approved hex values and actual CSB logo."),
}

WIDGET_TYPES = {
    "ranking": "Animated paginated bars with a searchable, sortable full-table toggle",
    "table_ranking": "Searchable sortable paginated ranking table",
    "heatmap": "Searchable sortable full table with metric heatmap",
    "comparison": "Two-metric side-by-side comparison",
    "scatter": "SVG two-metric scatterplot with hover labels",
    "map": "Leaflet geographic pin map (requires latitude and longitude)",
    "metric_cards": "Numeric data snapshot cards",
    "callout": "Editorial narrative/callout",
}


# V6 template gallery. Templates define arrangement, not publication colors.
# Each widget ID is an existing, executable component in this engine.
TEMPLATES = {
    "classic_tables": {"name": "Classic Tables", "description": "Editorial article with a table-first ranking and a heatmap breakdown.", "widgets": ["table_ranking", "heatmap"], "visual_style": "minimal", "depth": "quick"},
    "visual_rankings": {"name": "Visual Rankings", "description": "Animated ranking bars with a table toggle and a metric comparison.", "widgets": ["ranking", "comparison"], "visual_style": "editorial", "depth": "quick"},
    "editorial_deep": {"name": "Editorial Deep Dive", "description": "Long-form report with rankings, comparisons, scatter analysis and full results.", "widgets": ["ranking", "comparison", "scatter", "heatmap"], "visual_style": "bold", "depth": "deep"},
    "geo_explorer": {"name": "Geographic Explorer", "description": "Verified latitude/longitude pin map, linked rankings and searchable results.", "widgets": ["map", "ranking", "table_ranking"], "visual_style": "editorial", "depth": "deep"},
    "comparison_studio": {"name": "Comparison Studio", "description": "Headline metric cards, two-metric comparisons and a results table.", "widgets": ["metric_cards", "comparison", "table_ranking"], "visual_style": "minimal", "depth": "quick"},
}


def template_selection(template_id, custom_widgets=None, visual_style=None):
    """Return a portable, brand-neutral, AI-readable template contract."""
    if template_id == "custom":
        widgets = list(dict.fromkeys(custom_widgets or []))
        if not widgets or any(w not in WIDGET_TYPES for w in widgets):
            raise ValueError("Choose at least one implemented widget for the custom template.")
        # Add full-data access automatically and declare it openly in the Build command.
        if not any(w in ("ranking", "table_ranking", "heatmap") for w in widgets):
            widgets.append("table_ranking")
        item = {"widgets": widgets, "visual_style": "editorial", "depth": "custom"}
    else:
        if template_id not in TEMPLATES:
            raise ValueError(f"Unknown template ID: {template_id}")
        item = TEMPLATES[template_id]
        widgets = item["widgets"][:]
    style = visual_style or item["visual_style"]
    if style not in ("editorial", "minimal", "bold"):
        raise ValueError("Unknown visual style.")
    return {"contract_version": "6.0", "template_id": template_id,
            "widgets": widgets, "visual_style": style,
            "depth": item["depth"], "animation": "enabled",
            "data_policy": "all_ranked_sheets", "output": "single_html",
            "branding": "streamlit_only"}


def check_selected_page(spec):
    """Fail visibly if AI returns widgets incompatible with requested template/data."""
    selection = spec.get("template") or {}
    if not isinstance(selection, dict) or not selection.get("template_id"):
        raise ValueError("Missing 'template.template_id'. Use the V6 ChatGPT Project instructions and the copied Build command.")
    template_id = selection["template_id"]
    declared = selection.get("widgets")
    if not isinstance(declared, list) or not declared:
        raise ValueError("'template.widgets' must list approved widget identifiers.")
    if any(w not in WIDGET_TYPES for w in declared):
        raise ValueError("The blueprint asks for a widget not implemented in the Python engine.")
    if template_id not in TEMPLATES and template_id != "custom":
        raise ValueError("Unknown template_id. Choose a supported default or 'custom'.")
    if template_id in TEMPLATES:
        allowed = set(TEMPLATES[template_id]["widgets"])
        if any(w not in allowed for w in declared):
            raise ValueError("The blueprint contains widgets outside the selected default template. Ask the AI to revise the feasible widget list.")
    page = spec.get("page") or {}
    sections = page.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("The blueprint must include a non-empty 'page.sections' array.")
    known = {d["id"]: d for d in spec["datasets"]}
    ranked = set()
    for index, sec in enumerate(sections, 1):
        if not isinstance(sec, dict):
            raise ValueError(f"Section {index} is not an object.")
        typ = sec.get("type")
        if typ not in declared and typ != "callout":
            raise ValueError(f"Section {index}: widget '{typ}' was not approved in the chosen template. Update the template or the AI blueprint.")
        ds_id = jid(sec.get("dataset_id") or spec["datasets"][0]["id"])
        if ds_id not in known:
            raise ValueError(f"Section {index} refers to unknown dataset '{ds_id}'.")
        ds=known[ds_id]
        keys=set().union(*(r.keys() for r in ds["rows"]))
        numeric={key for key in keys if any(n(r.get(key)) is not None for r in ds["rows"])}
        if typ in ("ranking", "table_ranking", "heatmap"):
            ranked.add(ds_id)
        if typ != "callout" and typ not in WIDGET_TYPES:
            raise ValueError(f"Section {index}: unimplemented widget '{typ}'.")
        if typ in ("ranking", "table_ranking", "heatmap", "map"):
            metric=sec.get("metric") or ds["primary_metric"]
            if metric not in numeric:
                raise ValueError(f"Section {index}: numeric metric '{metric}' missing from dataset '{ds_id}'.")
        if typ == "map":
            if not any(n(r.get("latitude")) is not None and n(r.get("longitude")) is not None
                       and -90 <= n(r["latitude"]) <= 90 and -180 <= n(r["longitude"]) <= 180 for r in ds["rows"]):
                raise ValueError(f"Section {index}: pin map is not feasible. Dataset '{ds_id}' needs verified numeric latitude and longitude. State names alone do not qualify.")
        if typ in ("comparison", "scatter"):
            metrics=sec.get("metrics") or []
            if len(metrics)<2 or any(m not in numeric for m in metrics[:2]):
                raise ValueError(f"Section {index}: {typ} requires two existing numeric column names in 'metrics'.")
        if typ == "metric_cards":
            metrics=sec.get("metrics") or []
            if not metrics or any(m not in numeric for m in metrics):
                raise ValueError(f"Section {index}: metric_cards requires real numeric metric keys.")
    missing=set(known)-ranked
    if missing:
        raise ValueError("Every ranking dataset needs at least one ranking, table_ranking or heatmap section. Missing: " + ", ".join(sorted(missing)))
    return True


def demo_blueprint(selection):
    """Fictional numbers for the *template preview only*. No published claims."""
    labels=["Seattle", "Portland", "Denver", "Austin", "Boston", "Atlanta", "Phoenix", "Nashville", "Chicago", "Detroit", "Miami", "Dallas", "San Diego", "Charlotte", "Pittsburgh", "Cleveland", "Minneapolis", "Tampa"]
    points=[(47.606,-122.332),(45.515,-122.678),(39.739,-104.990),(30.267,-97.743),(42.360,-71.059),(33.749,-84.388),(33.448,-112.074),(36.162,-86.782),(41.878,-87.630),(42.331,-83.046),(25.761,-80.192),(32.777,-96.797),(32.716,-117.161),(35.227,-80.843),(40.441,-79.996),(41.499,-81.694),(44.978,-93.265),(27.951,-82.457)]
    rows=[{"City":label,"Demo Score":round(88-i*3.45,2),"Demo Cost":round(45+i*2.4+(i%3)*1.6,1),"Demo Accessibility":round(91-i*2.7+(i%4)*1.1,1),"latitude":lat,"longitude":lon} for i,(label,(lat,lon)) in enumerate(zip(labels,points))]
    # The numbers are fake but the city labels/coordinates are common map locations.
    columns=[{"key":"City","label":"City","type":"text"},{"key":"Demo Score","label":"Illustrative Score","type":"number","decimals":2},{"key":"Demo Cost","label":"Illustrative Cost","type":"number","decimals":1},{"key":"Demo Accessibility","label":"Illustrative Accessibility","type":"number","decimals":1}]
    widgets=selection["widgets"]
    sections=[]
    titles={"ranking":"Animated City Ranking","table_ranking":"Searchable Full Ranking","heatmap":"Results Heatmap","comparison":"Two Underlying Indicators","scatter":"Indicator Relationships","map":"Geographic Pin Explorer","metric_cards":"At a Glance","callout":"What the Figures Mean"}
    for w in widgets:
        item={"type":w,"dataset_id":"cities","title":titles[w],"description":"Illustrative values only. Template preview, not verified research.","metric":"Demo Score", "limit":12 if selection["depth"]=="deep" else 10}
        if w in ("comparison","scatter"):
            item["metrics"]=["Demo Cost","Demo Accessibility"]
        elif w=="metric_cards":
            item["metrics"]=["Demo Score","Demo Cost"]
        elif w=="callout":
            item["text"]="Illustrative design preview only. The final research will be supplied in the AI project's JSON file."
        sections.append(item)
    if not any(w in ("ranking","table_ranking","heatmap") for w in widgets):
        # A data-access table is always part of the final page for complete coverage.
        sections.append({"type":"table_ranking","dataset_id":"cities", "title":"Complete Sample Rankings","metric":"Demo Score"})
    active=list(dict.fromkeys([s["type"] for s in sections]))
    result={"schema_version":"6.0","template":{**selection,"widgets":active},"visual_style":selection["visual_style"],"title":"Illustrative City Research — Template Preview", "subtitle":"This animated layout contains fabricated sample values for design demonstration only.","date":"DEMO", "kicker":"TEMPLATE PREVIEW / FICTIONAL DATA", "byline":"Landing Page Studio", "summary":"No scores, comparisons or claims on this page should be published.","intro":["This preview uses deliberately fictional figures to demonstrate page structure, widget behavior and entrance animations. Your finished AI blueprint will replace this with your research."], "hero_stats":[{"value":"18","label":"Sample City Rows"},{"value":str(len(sections)),"label":"Widget Sections"}],"key_findings":[{"stat":"DEMO","headline":"A Design Preview Only","copy":"All numerical values are artificial and exist solely to demonstrate the selected template."}], "methodology":{"summary":"Example layout only. Replace this with verified research methodology.","steps":[{"title":"Upload Original Research to ChatGPT or Claude","text":"Supply your spreadsheet and the copied Build instruction in a separate AI project."},{"title":"Review Feasibility","text":"The AI checks each widget against the actual numeric and geographic columns, then waits for Agreed & Proceed."},{"title":"Render the Final JSON","text":"The approved self-contained JSON drives this same selected layout with publication-specific branding."}],"notes":["No real study or calculations are represented here."],"sources":[]},"datasets":[{"id":"cities","title":"City Rankings (Illustrative)","entity_key":"City","primary_metric":"Demo Score","columns":columns,"rows":rows}],"page":{"sections":sections}}
    return result


def e(v):
    return html.escape(str(v if v is not None else ""), quote=True)

def jid(v):
    return re.sub(r"[^a-z0-9_-]+", "-", unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode("ascii").lower()).strip("-") or "section"

def safe_url(v):
    v = str(v or "").strip()
    p = urlparse(v)
    return v if p.scheme in ("https", "http") and bool(p.netloc) else ""

def n(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None

def json_for_script(o):
    # Prevent prematurely closing <script> and JS script-context injection.
    return json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

def normalize(spec):
    if not isinstance(spec, dict):
        raise ValueError("Blueprint must be a JSON object.")
    src = copy.deepcopy(spec)
    # Brand identity belongs entirely to the Streamlit publishing layer, never
    # to the editorial JSON. Ignore legacy brand/theme values, including URL
    # names and any hex colors that a previous chat may have emitted.
    for key in (
        "brand", "publication_brand", "theme", "palette", "colors",
        "primary_color", "secondary_color", "accent_color", "brand_colors",
        "logo", "logo_url", "css", "custom_css",
    ):
        src.pop(key, None)
    tone = str(src.get("visual_style") or "editorial").strip().casefold()
    src["visual_style"] = tone if tone in ("editorial", "minimal", "bold") else "editorial"
    if not str(src.get("title", "")).strip():
        raise ValueError("Blueprint needs a non-empty 'title'.")
    rows = src.get("rows") or []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("'rows' must be an array of objects, or supplied through a CSV/XLSX upload.")
    cols = src.get("columns") or []
    if not cols and rows:
        cols = [{"key": k, "label": str(k).replace("_", " ").title(), "type": "number" if any(n(r.get(k)) is not None for r in rows) else "text"} for k in rows[0]]
    if not isinstance(cols, list) or any(not isinstance(c, dict) or not c.get("key") for c in cols):
        raise ValueError("'columns' must be an array of objects with 'key' and 'label'.")
    src["rows"] = rows
    src["columns"] = cols
    numerical = [c["key"] for c in cols if c.get("type") in ("number", "percent", "currency", "integer")]
    if not numerical and rows:
        numerical = [k for k in rows[0] if any(n(r.get(k)) is not None for r in rows)]
    metric = src.get("primary_metric") or (numerical[0] if numerical else "")
    if metric and rows and all(n(r.get(metric)) is None for r in rows):
        raise ValueError(f"Primary metric '{metric}' contains no numeric values. Check keys and CSV headers.")
    src["primary_metric"] = metric
    src.setdefault("primary_label", next((c.get("label", c["key"]) for c in cols if c["key"] == metric), metric))
    src.setdefault("entity_key", next((c["key"] for c in cols if c.get("type") == "text"), cols[0]["key"] if cols else "name"))
    src.setdefault("subtitle", "")
    src.setdefault("kicker", "Original Research")
    src.setdefault("summary", "")
    src.setdefault("intro", [])
    src.setdefault("key_findings", [])
    src.setdefault("methodology", {})
    src.setdefault("simple", {})
    src.setdefault("detailed", {})
    if not isinstance(src["simple"], dict) or not isinstance(src["detailed"], dict):
        raise ValueError("'simple' and 'detailed' must be objects.")
    if not isinstance(src["key_findings"], list):
        raise ValueError("'key_findings' must be a list.")
    if not isinstance(src["intro"], list):
        src["intro"] = [str(src["intro"])]
    src["simple"].setdefault("widget_title", "Explore the Complete Ranking")
    src["simple"].setdefault("widget_description", "Switch between chart and table views to explore the results.")
    src["simple"].setdefault("top_n", 10)
    src["simple"].setdefault("direction", "desc")
    src["detailed"].setdefault("sections", [{"type": "ranking", "title": src["simple"]["widget_title"], "description": src["simple"]["widget_description"], "metric": metric}, {"type": "heatmap", "title": "The Full Dataset", "metric": metric}])
    src.setdefault("slug", jid(src["title"]))
    # One self-contained JSON may contain several independently ranked worksheets.
    # Backwards-compatible with legacy blueprints using only top-level rows.
    supplied = src.get("datasets")
    if supplied is not None and (not isinstance(supplied, list) or not supplied):
        raise ValueError("'datasets' must be a non-empty list of dataset objects.")
    if supplied is None:
        supplied = [{"id":"main", "title":src.get("simple", {}).get("widget_title", "Main Ranking"),
                     "entity_key":src["entity_key"], "primary_metric":src["primary_metric"],
                     "columns":src["columns"], "rows":src["rows"]}]
    cleaned=[]
    seen=set()
    for i, entry in enumerate(supplied):
        if not isinstance(entry, dict):
            raise ValueError(f"Dataset {i+1} must be a JSON object.")
        d=copy.deepcopy(entry)
        ident=jid(d.get("id") or f"ranking-{i+1}")
        if ident in seen:
            raise ValueError(f"Dataset IDs must be unique: {ident}")
        seen.add(ident)
        d["id"]=ident
        d.setdefault("title", "Primary Ranking" if i==0 else f"Ranking {i+1}")
        d.setdefault("entity_key", src["entity_key"] if i==0 else "name")
        d.setdefault("primary_metric", src["primary_metric"] if i==0 else "score")
        d.setdefault("rows", src["rows"] if i==0 else [])
        if not isinstance(d["rows"], list) or any(not isinstance(x, dict) for x in d["rows"]):
            raise ValueError(f"Dataset '{ident}' must contain a 'rows' array of records.")
        if not d["rows"]:
            raise ValueError(f"Dataset '{ident}' is empty. Include the actual source worksheet rows.")
        if not any(n(x.get(d["primary_metric"])) is not None for x in d["rows"]):
            raise ValueError(f"Dataset '{ident}' has no numeric values for metric '{d['primary_metric']}'.")
        if not any(str(x.get(d["entity_key"], "")).strip() for x in d["rows"]):
            raise ValueError(f"Dataset '{ident}' lacks values for entity key '{d['entity_key']}'.")
        if not d.get("columns"):
            d["columns"]=[{"key":k,"label":k.replace("_"," "),"type":"number" if any(n(x.get(k)) is not None for x in d["rows"]) else "text"} for k in d["rows"][0]]
        if not isinstance(d["columns"], list) or any(not isinstance(x,dict) or not x.get("key") for x in d["columns"]):
            raise ValueError(f"Dataset '{ident}' has invalid columns.")
        cleaned.append(d)
    src["datasets"]=cleaned
    # Data-bound helpers still expect the primary dataset at the top level.
    src["rows"]=cleaned[0]["rows"]
    src["columns"]=cleaned[0]["columns"]
    src["entity_key"]=cleaned[0]["entity_key"]
    src["primary_metric"]=cleaned[0]["primary_metric"]
    return src

def validate(spec):
    warnings = []
    rows = spec["rows"]
    keys = set().union(*(r.keys() for r in rows)) if rows else set()
    if not rows:
        warnings.append("No dataset attached. The layouts will render, but data widgets will be empty.")
    if len(rows) > 20000:
        warnings.append("This is a large embedded dataset (>20,000 rows); published HTML may be heavy.")
    if len(spec["columns"]) > 5:
        warnings.append("The table has more than five columns. Horizontal scrolling will be available on small screens.")
    if spec["primary_metric"] and spec["primary_metric"] not in keys and rows:
        warnings.append("Primary metric is not a column in the data.")
    for i, section in enumerate(spec["detailed"].get("sections", []), 1):
        dataset_id=jid(section.get("dataset_id") or spec["datasets"][0]["id"])
        ds=next((d for d in spec["datasets"] if d["id"]==dataset_id),None)
        if ds is None:
            warnings.append(f"Detailed section {i} refers to a dataset_id that does not exist: {dataset_id}.")
            continue
        rows=ds["rows"]
        keys=set().union(*(r.keys() for r in rows))
        typ = section.get("type")
        if typ not in WIDGET_TYPES:
            warnings.append(f"Detailed section {i}: unsupported type '{typ}'. It will be skipped.")
        if typ == "map" and rows and not any(n(r.get("latitude")) is not None and n(r.get("longitude")) is not None for r in rows):
            warnings.append(f"Detailed section {i}: map requires 'latitude' and 'longitude' columns with valid numbers.")
        if typ in ("comparison", "scatter"):
            mets = section.get("metrics", [])
            if len(mets) < 2:
                warnings.append(f"Detailed section {i}: {typ} needs two metrics in 'metrics'.")
            elif rows and any(x not in keys for x in mets[:2]):
                warnings.append(f"Detailed section {i}: {typ} metric name not found in the CSV columns.")
    return warnings

def logo_html(brand, theme, logo_uri=None):
    if logo_uri:
        # Only data images supplied by trusted local uploader, never javascript URIs.
        if logo_uri.startswith(("data:image/png;base64,", "data:image/svg+xml;base64,", "data:image/webp;base64,")):
            return f'<img class="brand-image" src="{e(logo_uri)}" alt="{e(brand)} logo">'
    if brand == "Action Network":
        return '<span class="brand-lockup"><svg class="brand-symbol" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="16" fill="none" stroke="var(--bright)" stroke-width="3.8"/><path d="m11 20 6 6 12-14" fill="none" stroke="var(--bright)" stroke-width="3.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span>ACTION NETWORK</span></span>'
    return f'<span class="brand-lockup brand-text"><span class="brand-marker" aria-hidden="true"></span><span>{e(theme["wordmark"])}</span></span>'

def method_html(spec):
    m = spec.get("methodology") or {}
    items = []
    if m.get("summary"):
        items.append(f'<p class="method-summary">{e(m["summary"])}</p>')
    steps = m.get("steps", [])
    if steps:
        items.append('<div class="method-grid">')
        for i, s in enumerate(steps, 1):
            items.append(f'<article class="method-card"><span class="method-number">{i:02d}</span><h3>{e(s.get("title","Step"))}</h3><p>{e(s.get("text",""))}</p></article>')
        items.append('</div>')
    if m.get("notes"):
        items.append('<div class="method-notes">' + ''.join(f'<p>{e(note)}</p>' for note in m["notes"]) + '</div>')
    if m.get("sources"):
        links = []
        for source in m["sources"]:
            if isinstance(source, str):
                links.append(f'<span>{e(source)}</span>')
            else:
                u = safe_url(source.get("url"))
                label = e(source.get("label", u))
                links.append(f'<a href="{e(u)}" target="_blank" rel="noopener noreferrer">{label} ↗</a>' if u else f'<span>{label}</span>')
        items.append('<div class="sources"><strong>Research sources</strong><div class="source-links">' + ''.join(f"<div class=\"source-link\">{link}</div>" for link in links) + '</div></div>')
    if not items:
        items = ['<p>Methodology details were not supplied in the blueprint. Add them before publication.</p>']
    return ''.join(items)

def findings_html(spec, compact=False):
    findings = spec.get("key_findings", [])[:3 if compact else 6]
    if not findings:
        return ""
    out = ['<div class="findings">']
    for i, f in enumerate(findings):
        if isinstance(f, str):
            f = {"headline": f}
        out.append(f'<article class="finding {"featured" if i == 0 else ""}"><div class="finding-stat">{e(f.get("stat", f"{i+1:02d}"))}</div><div><h3>{e(f.get("headline", "Key finding"))}</h3><p>{e(f.get("copy", ""))}</p></div></article>')
    out.append('</div>')
    return ''.join(out)

def widget_html(kind, spec, section, idx):
    base = f'w{idx}'
    selected = next((d for d in spec["datasets"] if d["id"] == jid(section.get("dataset_id") or spec["datasets"][0]["id"])), spec["datasets"][0])
    metric = str(section.get("metric") or selected.get("primary_metric") or "")
    title = section.get("title") or {"ranking":"Ranking", "heatmap":"Full Results", "map":"Geographic Breakdown", "scatter":"Compare Two Measures", "comparison":"Side-by-Side Comparison", "metric_cards":"At a Glance", "callout":"What the Numbers Mean"}.get(kind, "Data Explorer")
    desc = section.get("description", "")
    title_html = f'<div class="section-heading"><span class="eyebrow">Data Explorer / {idx:02d}</span><h2>{e(title)}</h2>{f"<p>{e(desc)}</p>" if desc else ""}</div>'
    if kind == "callout":
        return f'<section class="section" id="{base}">{title_html}<div class="editorial-callout"><p>{e(section.get("text", ""))}</p></div></section>'
    attrs = f'data-dataset="{e(selected["id"])}" data-widget="{e(kind)}" data-id="{base}" data-metric="{e(metric)}" data-direction="{e(section.get("direction", "desc"))}" data-limit="{int(n(section.get("limit", 12)) or 12)}"'
    attrs += f' data-table-page="{int(n(section.get("table_page", 12)) or 12)}"'
    mets = section.get("metrics", [])
    if isinstance(mets, list):
        attrs += f' data-metrics="{e(json.dumps(mets))}"'
    if kind == "ranking":
        content = f'<div class="visual-frame"><div class="visual-controls"><div class="view-buttons"><button class="view-btn active" type="button" data-view="chart">Bar Chart</button><button class="view-btn" type="button" data-view="table">Full Table</button></div><div class="view-buttons"><button class="export-btn" data-export="png" type="button">Export PNG ↓</button><button class="export-btn" data-export="csv" type="button">Export CSV ↓</button></div></div><div class="view chart-view"></div><div class="view table-view" hidden></div></div>'
    elif kind in ("heatmap", "table_ranking"):
        content = '<div class="visual-frame"><div class="view table-view"></div></div>'
    else:
        content = '<div class="visual-frame"><div class="view widget-content"></div></div>'
    return f'<section class="section" id="{base}">{title_html}<div class="widget" {attrs}>{content}</div></section>'

CSS = r"""

/* Brand-independent layout directions: a JSON may choose ONE of these styles,
   but all accent colors always come from the Streamlit brand selection. */
.visual-style-minimal .hero::after{display:none}
.visual-style-minimal .hero h1{font-size:clamp(40px,5.5vw,74px)}
.visual-style-minimal .finding,.visual-style-minimal .visual-frame{box-shadow:none}
.visual-style-minimal .section{padding-top:clamp(34px,4.4vw,58px);padding-bottom:clamp(34px,4.4vw,58px)}
.visual-style-bold .hero h1{font-size:clamp(46px,7vw,96px);font-weight:900}
.visual-style-bold .section-heading h2{letter-spacing:-.036em}
.visual-style-bold .finding{box-shadow:0 14px 30px rgba(16,24,32,.09)}
.visual-style-bold .visual-frame{box-shadow:0 19px 50px rgba(16,24,32,.11)}

:root{--primary:__PRIMARY__;--bright:__BRIGHT__;--dark:__DARK__;--navy:__NAVY__;--navy2:__NAVY2__;--soft:__SOFT__;--line:#dce2e6;--ink:#1e2930;--muted:#65737c;--white:#fff;--wash:#f6f7f8;--display:'Barlow Condensed','Arial Narrow',sans-serif;--serif:'Source Serif 4',Georgia,serif}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:75px;scrollbar-color:var(--primary) #e6ebee;scrollbar-width:thin}html::-webkit-scrollbar,.rank-scroll::-webkit-scrollbar,.nav-inner::-webkit-scrollbar{width:7px;height:7px}html::-webkit-scrollbar-thumb,.rank-scroll::-webkit-scrollbar-thumb,.nav-inner::-webkit-scrollbar-thumb{background:var(--primary);border-radius:12px}html::-webkit-scrollbar-track,.rank-scroll::-webkit-scrollbar-track{background:#e6ebee}body{margin:0;background:var(--white);color:var(--ink);font:17px/1.66 var(--serif);overflow-x:hidden}button,input{font:inherit}button{cursor:pointer}a{color:var(--dark)}a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid var(--bright);outline-offset:2px}h1,h2,h3,p{margin-top:0}h1,h2,h3,button,.eyebrow,.brand-lockup,.feature-num,.hero-stat strong,.metric-number,.rank-pill,.bar-value,.table th,.footer-link,.table-pager,.widget-kicker,.finding-stat{font-family:var(--display)}h2{font-size:clamp(34px,5vw,56px);line-height:1.02;color:var(--navy);letter-spacing:-.012em}h3{line-height:1.13;font-size:25px;color:var(--navy)}.wrap{max-width:1240px;margin:auto;padding:0 clamp(19px,3.4vw,46px)}.hero{position:relative;background:radial-gradient(900px 440px at 90% 12%,color-mix(in srgb,var(--primary) 22%,transparent),transparent 60%),linear-gradient(125deg,#080e13 0%,var(--navy) 51%,var(--navy2) 100%);color:white;overflow:hidden;border-bottom:6px solid var(--primary)}.hero::after{position:absolute;content:"";inset:0;pointer-events:none;background:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:58px 58px;mask-image:linear-gradient(90deg,transparent,#000)}.hero-inner{position:relative;z-index:1;padding-top:clamp(24px,4vw,46px);padding-bottom:clamp(35px,5.5vw,70px)}.hero-top{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:20px;margin-bottom:clamp(34px,5vw,60px)}.brand-lockup{display:inline-flex;align-items:center;gap:12px;font-size:clamp(20px,2.4vw,29px);font-weight:900;letter-spacing:.04em;line-height:1;white-space:nowrap}.brand-image{display:block;height:43px;max-width:min(360px,90vw);width:auto;object-fit:contain}.brand-symbol{height:37px;width:37px}.brand-marker{display:block;width:10px;height:33px;background:var(--bright);transform:skew(-16deg);box-shadow:6px 0 0 color-mix(in srgb,var(--bright) 45%,transparent)}.research-mark{color:#a2b2b9;font:700 12px var(--display);letter-spacing:.15em;text-transform:uppercase}.eyebrow{display:block;font-weight:800;font-size:13px;color:var(--dark);letter-spacing:.14em;text-transform:uppercase}.hero .eyebrow{color:var(--bright);margin-bottom:16px}.hero h1{max-width:1110px;font-size:clamp(43px,6.4vw,87px);line-height:.98;font-weight:900;letter-spacing:-.013em;margin:0}.hero h1 .accent{color:var(--bright)}.dek{margin:22px 0 0;color:#d5e0e4;font-size:clamp(17px,1.8vw,21px);line-height:1.56;max-width:940px}.byline{margin:22px 0 0;color:#95aab2;font:600 14px var(--display);letter-spacing:.045em}.hero-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;margin-top:34px;background:#354c4b;border:1px solid rgba(255,255,255,.1)}.hero-stat{background:rgba(13,24,31,.92);padding:21px 20px}.hero-stat strong{font-size:clamp(27px,3.6vw,45px);line-height:1;font-weight:900;color:var(--bright);display:block}.hero-stat small{display:block;font:700 12px/1.3 var(--display);letter-spacing:.1em;text-transform:uppercase;color:#b0c1c8;margin-top:9px}.nav{position:sticky;top:0;z-index:30;backdrop-filter:blur(12px);background:rgba(255,255,255,.97);border-bottom:1px solid var(--line);box-shadow:0 4px 14px rgba(0,0,0,.035)}.nav-inner{display:flex;gap:8px;align-items:center;overflow-x:auto;padding-top:10px;padding-bottom:10px;scrollbar-width:thin;scrollbar-color:var(--primary) transparent}.nav a{text-decoration:none;white-space:nowrap;font:800 14px var(--display);letter-spacing:.04em;color:var(--navy);border:1px solid var(--line);border-bottom:3px solid var(--primary);padding:7px 14px;transition:.15s}.nav a:hover{background:var(--navy);color:white}.section{padding:clamp(40px,5.4vw,75px) 0;border-bottom:1px solid var(--line);scroll-margin-top:72px}.section.alt{background:var(--wash)}.section-heading{max-width:980px;margin-bottom:27px}.section-heading .eyebrow{margin-bottom:8px}.section-heading h2{margin-bottom:15px}.section-heading p{color:var(--muted);font-size:17px;line-height:1.58;margin:0}.intro{font-size:19px;max-width:980px}.intro p{margin:0 0 17px}.findings{display:grid;grid-template-columns:1fr;gap:12px}.finding{display:grid;grid-template-columns:minmax(95px,180px) 1fr;align-items:center;gap:20px;padding:22px 25px;border:1px solid var(--line);border-left:6px solid var(--primary);background:white;box-shadow:0 8px 22px rgba(16,24,32,.04)}.finding.featured{background:linear-gradient(120deg,var(--navy) 40%,var(--navy2));border-left-color:var(--bright);color:white}.finding-stat{font-size:clamp(31px,4.2vw,51px);line-height:1;color:var(--dark);font-weight:900;overflow-wrap:anywhere}.featured .finding-stat{color:var(--bright)}.finding h3{margin:0 0 5px;font-size:25px;font-weight:800}.finding p{margin:0;font-size:15px;line-height:1.55;color:var(--muted)}.finding.featured h3{color:white}.finding.featured p{color:#c5d1d6}.visual-frame{border:1px solid var(--line);background:#fff;box-shadow:0 14px 40px rgba(16,24,32,.065);overflow:hidden}.visual-controls{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;align-items:center;padding:13px 16px;background:var(--wash);border-bottom:1px solid var(--line)}.view-buttons{display:flex;gap:8px;flex-wrap:wrap}.view-btn,.export-btn,.table-pager button,.table-search{border:1px solid #cdd9d4;background:#fff;color:var(--navy);padding:10px 15px;font:800 14px var(--display);letter-spacing:.035em}.view-btn.active,.view-btn:hover{background:var(--primary);border-color:var(--primary);color:var(--navy)}.export-btn:hover,.table-pager button:hover{border-color:var(--dark)}.view[hidden]{display:none!important}.bar-chart{display:grid;gap:13px;padding:25px 26px 27px}.bar-row{display:grid;grid-template-columns:45px minmax(125px,225px) minmax(95px,1fr) 95px;gap:13px;align-items:center}.rank-pill{height:34px;width:38px;background:var(--navy);color:var(--bright);font-size:16px;font-weight:900;display:grid;place-items:center}.bar-label{font:800 18px/1.16 var(--display);color:var(--navy);overflow-wrap:anywhere}.bar-track{height:29px;background:#e8ecef;overflow:hidden}.bar-fill{height:100%;width:0;background:linear-gradient(90deg,var(--primary),var(--dark));transition:width 800ms cubic-bezier(.2,.75,.2,1)}.bar-chart.visible .bar-fill{width:var(--p)}.bar-value{text-align:right;font-size:23px;line-height:1.15;color:var(--navy);font-weight:900;white-space:nowrap}.widget-note{font:14px/1.45 var(--serif);color:var(--muted);padding:4px 26px 21px}.table-tools{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 16px}.table-search{font:14px var(--serif);max-width:370px;width:100%;min-width:0;font-weight:400}.table-count{font:800 13px var(--display);color:var(--muted);white-space:nowrap}.rank-scroll{overflow-x:auto;scrollbar-width:thin;scrollbar-color:var(--primary) #e6ebee}.table{border-collapse:collapse;width:100%;min-width:690px;font-size:14px}.table th{position:sticky;top:0;text-align:left;font-weight:800;text-transform:none;letter-spacing:.03em;font-size:15px;color:white;background:var(--navy);padding:14px 15px;cursor:pointer;white-space:nowrap}.table th:hover{background:var(--navy2)}.table td{padding:13px 15px;border-bottom:1px solid var(--line);white-space:nowrap}.table tbody tr:nth-child(even){background:#f8f9fa}.table tbody tr:hover{background:var(--soft)}.table td.namecell{font-weight:700;color:var(--navy)}.heat-cell{box-shadow:inset 4px 0 var(--primary);background-color:var(--shade)!important;font-weight:800}.table-pager{display:flex;align-items:center;justify-content:center;gap:14px;padding:12px;border-top:1px solid var(--line);font-size:14px}.table-pager button{padding:7px 11px}.table-pager button:disabled{opacity:.35;cursor:default}.editorial-callout{color:#fff;background:linear-gradient(130deg,var(--navy),var(--navy2));border-left:6px solid var(--bright);padding:30px 36px}.editorial-callout p{margin:0;font-size:clamp(19px,2.1vw,25px);line-height:1.5}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:12px;padding:20px}.metric-card{border:1px solid var(--line);border-top:5px solid var(--primary);background:var(--wash);padding:22px}.metric-number{font-size:39px;line-height:1;display:block;color:var(--dark);font-weight:900}.metric-label{font:800 15px var(--display);margin-top:11px;display:block;color:var(--navy);text-transform:capitalize}.compare-chart{padding:22px;display:grid;gap:19px}.compare-item{padding-bottom:18px;border-bottom:1px solid var(--line)}.compare-head{display:flex;justify-content:space-between;gap:12px;font:800 18px var(--display);color:var(--navy);margin-bottom:11px}.compare-track{position:relative;min-height:17px;background:#e8ecef;margin:5px 0;overflow:hidden}.compare-fill{height:17px;background:var(--primary);width:var(--p)}.compare-fill.alt-fill{background:#6f91a4}.legend{display:flex;flex-wrap:wrap;gap:20px;padding:15px 23px 0;font:800 13px var(--display);color:var(--muted)}.legend i{display:inline-block;width:11px;height:11px;margin-right:6px;background:var(--primary)}.legend .alt-key{background:#6f91a4}.scatter-box{padding:20px}.scatter-svg{display:block;width:100%;max-height:520px}.scatter-axis{stroke:#a8bcb2;stroke-width:1.2}.scatter-grid{stroke:#e2eae6;stroke-width:1}.scatter-dot{fill:var(--primary);stroke:white;stroke-width:2;opacity:.82;cursor:pointer}.scatter-dot:hover{stroke:var(--navy);stroke-width:3;opacity:1}.scatter-label{fill:var(--muted);font:13px var(--display)}.scatter-caption{margin:8px 0 0;color:var(--muted);font-size:14px}.map-box{height:480px;min-height:320px;z-index:1}.map-error{padding:24px;background:var(--soft);font-size:15px}.map-pin{border-radius:50%}.method-summary{font-size:18px;max-width:960px}.method-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.method-card{border:1px solid var(--line);border-top:4px solid var(--primary);padding:24px;background:var(--wash)}.method-number{font:900 29px var(--display);color:var(--dark)}.method-card h3{font-size:23px;margin:10px 0 8px}.method-card p{font-size:15px;line-height:1.52;color:var(--muted);margin:0}.method-notes{padding:20px 0;color:var(--muted);font-size:15px}.method-notes p{margin:0 0 10px}.sources{border-left:4px solid var(--primary);background:var(--soft);padding:17px 20px;font-size:14px;margin-top:22px}.footer{background:var(--navy);color:#b7c8cd;padding:30px 0;font:14px/1.5 var(--serif)}.footer .wrap{display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px}.footer strong{color:var(--bright);font:800 16px var(--display)}.footer-link{color:var(--bright);text-decoration:none;font-weight:800}.backtop{margin-top:24px;display:inline-block;text-decoration:none;font:800 15px var(--display);color:var(--dark)}.empty{padding:26px;color:var(--muted)}
@media(max-width:750px){.hero-top{margin-bottom:35px}.research-mark{display:none}.bar-chart{padding:15px 12px}.bar-row{grid-template-columns:30px minmax(85px,135px) minmax(45px,1fr) 65px;gap:6px}.rank-pill{width:28px;height:28px;font-size:13px}.bar-label{font-size:14px}.bar-value{font-size:17px}.bar-track{height:22px}.finding{grid-template-columns:1fr;gap:10px;padding:20px}.finding-stat{font-size:39px}.finding h3{font-size:23px}.section{padding:42px 0}.visual-controls{padding:10px}.view-btn,.export-btn{padding:9px 10px;font-size:12px}.metric-grid{grid-template-columns:1fr 1fr}.map-box{height:360px}}
@media(max-width:480px){.metric-grid{grid-template-columns:1fr}.bar-row{grid-template-columns:25px minmax(80px,110px) minmax(20px,1fr) 55px}.bar-label{font-size:12.5px}.bar-value{font-size:15px}.bar-track{height:18px}.rank-pill{width:24px;height:25px}.dek{font-size:17px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}.bar-fill{width:var(--p)!important}}
@media print{.nav,.visual-controls,.table-tools,.table-pager,.backtop{display:none!important}.bar-fill{width:var(--p)!important}.section{break-inside:avoid}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

CSS += r"""

/* V5 editorial system. Designed to be readable and work in a Streamlit iframe. */
:root{--section-space:clamp(58px,7vw,98px)}
body{font-size:17px;line-height:1.78;background:#fff}
.wrap{max-width:1210px;padding-left:clamp(20px,4vw,56px);padding-right:clamp(20px,4vw,56px)}
.hero-inner{padding-top:clamp(32px,5vw,64px);padding-bottom:clamp(50px,7vw,90px)}
.hero h1{line-height:1.02;max-width:1000px}
.dek{max-width:870px;line-height:1.65}
.section{position:relative;padding:var(--section-space) 0;border-bottom:0}
.section:not(:last-child)::after{content:"";position:absolute;bottom:0;left:50%;width:min(88%,1050px);height:1px;transform:translateX(-50%);background:linear-gradient(90deg,transparent,var(--primary),var(--line) 50%,var(--primary),transparent);opacity:.52}
.section-heading{max-width:1000px;margin-bottom:clamp(26px,3vw,40px)}
.section-heading h2{font-size:clamp(34px,4.5vw,55px);line-height:1.08;letter-spacing:-.028em;margin:9px 0 16px}
.section-heading p{max-width:900px;font-size:17px;line-height:1.74}
.intro{line-height:1.86;max-width:930px}
.intro p{margin-bottom:21px}
.findings{gap:16px}
.finding{padding:26px 30px;gap:28px;box-shadow:0 9px 32px rgba(16,24,32,.06)}
.finding p{line-height:1.75}
.visual-frame{border-top:5px solid var(--primary);box-shadow:0 18px 50px rgba(16,24,32,.09)}
.visual-controls{padding:18px 20px}
.bar-chart{gap:16px;padding:clamp(19px,3vw,32px)}
.bar-row{grid-template-columns:45px minmax(125px,230px) minmax(75px,1fr) 110px;gap:14px;min-height:37px}
.bar-track{height:28px;border-radius:2px}
.bar-value{font-size:22px}
.bar-chart .bar-row{opacity:0;transform:translateY(12px);transition:transform .55s ease,opacity .55s ease;transition-delay:var(--stagger)}
.bar-chart.is-visible .bar-row{opacity:1;transform:none}
.bar-fill{transition:width 1200ms cubic-bezier(.15,.7,.2,1);transition-delay:calc(var(--stagger, 0ms) + 130ms)}
.compare-fill{width:0;transition:width 1100ms cubic-bezier(.2,.75,.2,1)}
.compare-chart.is-visible .compare-fill{width:var(--p)}
.chart-pager{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:16px;padding:5px 24px 23px;font:800 14px var(--display);color:var(--muted)}
.chart-pager button{padding:9px 14px;background:white;color:var(--navy);border:1px solid var(--line);font:800 13px var(--display)}
.chart-pager button:hover{background:var(--primary)}
.chart-pager button:disabled{opacity:.34;cursor:default}
.table-pager{gap:18px;padding:16px}
.table-pager button{border-radius:2px}
.table td{line-height:1.4}
.method-summary{max-width:940px;line-height:1.85;margin-bottom:32px}
.method-grid{display:grid;grid-template-columns:minmax(0,1fr)!important;gap:14px;max-width:940px}
.method-card{display:grid;grid-template-columns:80px minmax(0,1fr);column-gap:20px;align-items:start;border:1px solid var(--line);border-left:5px solid var(--primary);border-top:1px solid var(--line);padding:clamp(20px,3vw,30px);background:white;box-shadow:0 8px 26px rgba(16,24,32,.04)}
.method-number{grid-row:1/3;line-height:1.05;font-size:32px}
.method-card h3{margin:0 0 10px;font-size:26px}
.method-card p{font-size:16px;line-height:1.8}
.method-notes{max-width:940px;border-top:1px solid var(--line);padding:24px 0;margin-top:28px;line-height:1.8}
.method-notes p{margin-bottom:12px}
.sources{max-width:940px;display:block;border-left:5px solid var(--primary);padding:23px 27px;margin:30px 0 0;line-height:1.7}
.sources>strong{display:block;font:900 18px var(--display);text-transform:uppercase;letter-spacing:.04em;color:var(--navy);margin:0 0 13px}
.source-links{display:grid;gap:12px}
.source-link{display:block;overflow-wrap:anywhere;line-height:1.55;font-size:15px}
.source-link a{text-decoration:underline;text-underline-offset:3px}
.backtop-row{display:flex;justify-content:center;margin-top:44px}
.backtop{display:inline-flex;align-items:center;justify-content:center;gap:10px;margin:0;padding:13px 26px;border:2px solid var(--primary);background:var(--navy);color:#fff!important;text-decoration:none;font:900 15px var(--display);text-transform:uppercase;letter-spacing:.07em;box-shadow:0 9px 22px rgba(16,24,32,.12);transition:transform .2s,background .2s}
.backtop:hover{transform:translateY(-3px);background:var(--dark)}
.nav-inner{gap:10px}
.motion-replay{margin-left:auto;flex:none;border:1px solid var(--primary);padding:8px 12px;background:var(--navy);color:#fff;font:800 13px var(--display);white-space:nowrap}
.motion-replay:hover{background:var(--dark)}
.motion-reveal{opacity:0;transform:translateY(20px);transition:opacity 680ms ease,transform 680ms cubic-bezier(.2,.75,.2,1)}
.motion-reveal.is-visible{opacity:1;transform:translateY(0)}
.scatter-dot{transform-box:fill-box;transform-origin:center;animation:dotAppear .75s backwards;animation-delay:var(--stagger)}
@keyframes dotAppear{from{opacity:0;transform:scale(.15)}to{opacity:.82;transform:scale(1)}}
@media(max-width:750px){.method-card{grid-template-columns:55px minmax(0,1fr);gap:10px;padding:20px}.method-number{font-size:27px}.bar-row{grid-template-columns:32px minmax(90px,135px) minmax(55px,1fr) 77px;gap:7px}.bar-value{font-size:17px}.section{padding:55px 0}.sources{padding:19px}.motion-replay{margin-left:0}}
@media(max-width:480px){.method-card{grid-template-columns:1fr}.method-number{grid-row:auto}.method-card h3{margin:0}.bar-row{grid-template-columns:26px minmax(78px,105px) minmax(30px,1fr) 60px}.bar-value{font-size:14px}}
@media(prefers-reduced-motion:reduce){.motion-reveal,.bar-chart .bar-row{opacity:1!important;transform:none!important}.compare-fill,.bar-fill{width:var(--p)!important;transition:none!important}.scatter-dot{animation:none!important}}

"""


CSS += r"""
/* V6 template-specific editorial styling. Every accent references brand tokens. */
.template-classic_tables .hero{background:linear-gradient(130deg,var(--navy),var(--navy2));border-bottom-width:3px}
.template-classic_tables .hero h1{font-size:clamp(37px,5vw,68px);max-width:980px}
.template-classic_tables .section-heading h2{font-size:clamp(31px,3.8vw,44px)}
.template-classic_tables .visual-frame{box-shadow:none;border-top-width:3px}
.template-classic_tables .table th{text-transform:uppercase;font-size:12px;letter-spacing:.08em}
.template-classic_tables .finding{border-left-width:3px;box-shadow:none}
.template-visual_rankings .hero{background:radial-gradient(800px 420px at 85% 10%,color-mix(in srgb,var(--bright) 28%,transparent),transparent 64%),linear-gradient(130deg,var(--navy),var(--navy2))}
.template-visual_rankings .hero h1{font-size:clamp(45px,6.7vw,91px)}
.template-visual_rankings .visual-frame{border-top:7px solid var(--primary)}
.template-visual_rankings .finding.featured{box-shadow:0 22px 55px rgba(9,21,28,.16)}
.template-editorial_deep .hero{background:radial-gradient(650px 420px at 13% 105%,color-mix(in srgb,var(--primary) 30%,transparent),transparent),linear-gradient(100deg,var(--navy) 4%,var(--navy2) 98%)}
.template-editorial_deep .hero-inner{padding-top:clamp(60px,7vw,98px);padding-bottom:clamp(80px,9vw,128px)}
.template-editorial_deep .section-heading h2{font-size:clamp(40px,5.5vw,68px)}
.template-editorial_deep .section.alt{background:color-mix(in srgb,var(--soft) 32%,#fff)}
.template-editorial_deep .visual-frame{border-left:5px solid var(--primary)}
.template-geo_explorer .hero{background:linear-gradient(120deg,var(--navy),color-mix(in srgb,var(--primary) 26%,var(--navy)))}
.template-geo_explorer .hero:after{background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:35px 35px;mask-image:none}
.template-geo_explorer .map-box{height:535px}
.template-geo_explorer .visual-frame{border:3px solid color-mix(in srgb,var(--primary) 42%,#fff)}
.template-comparison_studio .hero{background:linear-gradient(115deg,var(--navy),var(--navy2))}
.template-comparison_studio .hero h1{font-size:clamp(37px,5.4vw,75px)}
.template-comparison_studio .metric-card{border-top:6px solid var(--primary);box-shadow:0 12px 28px rgba(16,24,32,.07)}
.template-comparison_studio .compare-chart{gap:25px;padding:clamp(24px,3vw,36px)}
.template-custom .visual-frame{border-top:6px solid var(--primary)}
"""

JS = r"""(()=>{'use strict';
const S=JSON.parse(document.getElementById('lp-data').textContent),DATASETS=Object.fromEntries((S.datasets||[]).map(d=>[d.id,d]));
const $=(q,root=document)=>root.querySelector(q),$$=(q,root=document)=>Array.from(root.querySelectorAll(q));
const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const num=v=>v===null||v===undefined||v===''?NaN:Number(v);
const good=v=>Number.isFinite(num(v));
const reduceMotion=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const motionObserver=('IntersectionObserver' in window)?new IntersectionObserver(entries=>{entries.forEach(en=>{if(en.isIntersecting){en.target.classList.add('is-visible');if(en.target.classList.contains('bar-chart'))en.target.classList.add('visible');motionObserver.unobserve(en.target)}})},{threshold:.07,rootMargin:'0px 0px -24px 0px'}):null;
function reveal(element){if(!element)return;if(reduceMotion||!motionObserver){element.classList.add('is-visible','visible');return} motionObserver.observe(element)}
$$('.hero-inner,.intro,.section-heading,.finding,.method-card,.method-summary,.sources,.editorial-callout').forEach(el=>{el.classList.add('motion-reveal');reveal(el)});
$$('[data-replay]').forEach(btn=>btn.addEventListener('click',()=>{ $$('.motion-reveal,.bar-chart,.compare-chart,.scatter-dot').forEach(el=>{el.classList.remove('is-visible','visible');if(el.classList.contains('motion-reveal')||el.classList.contains('bar-chart')){if(motionObserver)motionObserver.observe(el);else el.classList.add('is-visible','visible')}});window.scrollTo({top:0,behavior:reduceMotion?'auto':'smooth'})}));
$$('[data-widget]').forEach(w=>{
const d=DATASETS[w.dataset.dataset]||S.datasets?.[0]||S;
const ROWS=d.rows||[],COLS=d.columns||[],EKEY=d.entity_key||'name';
const col=(k)=>COLS.find(c=>c.key===k)||{key:k,label:k,type:'number'};
const fmt=(v,k)=>{const c=col(k),x=num(v);if(!good(v))return v===null||v===undefined?'—':String(v); const digs=c.decimals!=null?Math.max(0,Math.min(6,Number(c.decimals))):(c.type==='integer'?0:2);const f=new Intl.NumberFormat('en-US',{maximumFractionDigits:digs,minimumFractionDigits:c.decimals===undefined?0:digs}); if(c.type==='currency')return (c.prefix||'$')+f.format(x);if(c.type==='percent')return f.format((c.scale==='fraction'||c.value_scale==='fraction')?x*100:x)+'%';return (c.prefix||'')+f.format(x)+(c.suffix||'')};
const metricName=(k)=>col(k).label||k;
function sorted(rows,k,dir){return [...rows].sort((a,b)=>{const x=num(a[k]),y=num(b[k]);if(Number.isFinite(x)&&Number.isFinite(y))return (dir==='asc'?1:-1)*(x-y);if(Number.isFinite(x))return -1;if(Number.isFinite(y))return 1;return String(a[k]||'').localeCompare(String(b[k]||''))*(dir==='asc'?1:-1)});}
function imageExport(widget){const target=$('.chart-view',widget);if(!target)return;const old=target.hidden;target.hidden=false;
function proceed(){if(typeof window.html2canvas!=='function'){alert('PNG export needs a connection to load the screenshot library.');target.hidden=old;return} const width=Math.max(600,target.scrollWidth);const scale=Math.max(2,Math.ceil(2560/width));target.classList.add('exporting');html2canvas(target,{backgroundColor:'#ffffff',scale:scale,useCORS:true,windowWidth:Math.max(window.innerWidth,1100)}).then(canvas=>{const link=document.createElement('a');link.download=(S.slug||'study')+'-chart.png';link.href=canvas.toDataURL('image/png');link.click()}).catch(err=>alert('PNG export could not finish: '+err.message)).finally(()=>{target.hidden=old;target.classList.remove('exporting')})}
if(window.html2canvas){proceed();return} const script=document.createElement('script');script.src='https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';script.onload=proceed;script.onerror=()=>{target.hidden=old;alert('Image export requires internet access on the first use.')};document.head.appendChild(script)}
function csvExport(){const headers=COLS.length?COLS.map(c=>c.key):Object.keys(ROWS[0]||{});const quote=x=>'"'+String(x??'').replace(/"/g,'""')+'"';const body=[headers.map(quote).join(','),...ROWS.map(r=>headers.map(k=>quote(r[k])).join(','))].join('\r\n');const a=document.createElement('a'),url=URL.createObjectURL(new Blob(['\ufeff'+body],{type:'text/csv;charset=utf-8'}));a.href=url;a.download=(S.slug||'study')+'-data.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000)}
function chart(host,k,dir,limit){
const all=sorted(ROWS.filter(r=>good(r[k])),k,dir);const PAGE=Math.max(1,limit||10);let page=0;
function draw(){const rows=all.slice(page*PAGE,(page+1)*PAGE);const max=Math.max(...all.map(r=>Math.abs(num(r[k]))),1);
if(!rows.length){host.innerHTML='<p class="empty">No numeric data available.</p>';return}
const bars='<div class="bar-chart">'+rows.map((r,i)=>`<div class="bar-row" style="--stagger:${i*65}ms"><span class="rank-pill">${i+1+page*PAGE}</span><div class="bar-label" title="${esc(r[EKEY])}">${esc(r[EKEY])}</div><div class="bar-track"><div class="bar-fill" style="--p:${Math.max(1,Math.abs(num(r[k]))/max*100).toFixed(2)}%"></div></div><div class="bar-value">${esc(fmt(r[k],k))}</div></div>`).join('')+'</div>';
const nav=all.length>PAGE?`<div class="chart-pager"><button type="button" class="pager-back" ${page===0?'disabled':''}>← Previous ${PAGE}</button><span>Showing ${page*PAGE+1}–${Math.min((page+1)*PAGE,all.length)} of ${all.length}</span><button type="button" class="pager-next" ${(page+1)*PAGE>=all.length?'disabled':''}>Next ${PAGE} →</button></div>`:'';
host.innerHTML=bars+nav+`<p class="widget-note">Ranked by ${esc(metricName(k))}. Use the table view to search and sort all ${all.length} records.</p>`;
if(nav){$('.pager-back',host).addEventListener('click',()=>{page--;draw();});$('.pager-next',host).addEventListener('click',()=>{page++;draw();});}
reveal($('.bar-chart',host));
}
draw();}
function table(host,k,dir,heat){const columns=COLS.length?COLS:Object.keys(ROWS[0]||{}).map(key=>({key,label:key}));let query='',sortKey=k||columns[0]?.key,sortDir=dir||'desc',page=0;const PAGE=Math.max(1,Number(w.dataset.tablePage)||12);host.innerHTML='<div class="table-tools"><input class="table-search" type="search" placeholder="Search the full ranking..." aria-label="Search records"><span class="table-count"></span></div><div class="rank-scroll"><table class="table"><thead><tr>'+columns.map(c=>`<th tabindex="0" scope="col" data-col="${esc(c.key)}">${esc(c.label||c.key)} <span class="sort-icon">↕</span></th>`).join('')+'</tr></thead><tbody></tbody></table></div><div class="table-pager"><button type="button" data-p="prev">← Previous</button><span class="pagenumber"></span><button type="button" data-p="next">Next →</button></div>';
const tbody=$('tbody',host),count=$('.table-count',host),pager=$('.table-pager',host);
function draw(){const filtered=ROWS.filter(r=>!query||Object.values(r).some(v=>String(v??'').toLowerCase().includes(query)));const ordered=sorted(filtered,sortKey,sortDir),maxPage=Math.max(0,Math.ceil(ordered.length/PAGE)-1);page=Math.min(page,maxPage);const take=ordered.slice(page*PAGE,page*PAGE+PAGE);let mn=Math.min(...filtered.map(r=>num(r[k])).filter(Number.isFinite)),mx=Math.max(...filtered.map(r=>num(r[k])).filter(Number.isFinite));
tbody.innerHTML=take.map(r=>'<tr>'+columns.map(c=>{const val=r[c.key],isHeat=heat&&c.key===k&&good(val);const norm=mx===mn?.5:(num(val)-mn)/(mx-mn);const shade=isHeat?` style="--shade:color-mix(in srgb, var(--primary) ${Math.round(7+28*norm)}%, white)"`:'';return `<td class="${c.key===EKEY?'namecell ':''}${isHeat?'heat-cell':''}"${shade}>${esc(fmt(val,c.key))}</td>`}).join('')+'</tr>').join('')||`<tr><td colspan="${columns.length}">No matching records</td></tr>`;
count.textContent=filtered.length.toLocaleString()+' records';$('.pagenumber',host).textContent=(page+1)+' / '+(maxPage+1);$('[data-p="prev"]',pager).disabled=page===0;$('[data-p="next"]',pager).disabled=page>=maxPage;$$('th',host).forEach(th=>{$('.sort-icon',th).textContent=th.dataset.col===sortKey?(sortDir==='asc'?'↑':'↓'):'↕'});}
$('.table-search',host).addEventListener('input',ev=>{query=ev.target.value.toLowerCase().trim();page=0;draw()});$$('th',host).forEach(th=>{const click=()=>{if(sortKey===th.dataset.col)sortDir=sortDir==='asc'?'desc':'asc';else{sortKey=th.dataset.col;sortDir='desc'}page=0;draw()};th.addEventListener('click',click);th.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();click()}})});$$('[data-p]',pager).forEach(b=>b.addEventListener('click',()=>{page+=b.dataset.p==='next'?1:-1;draw()}));draw()}
function comparison(host,metrics,limit,dir){const [a,b]=metrics;if(!a||!b){host.innerHTML='<p class="empty">Specify two metric keys for this comparison.</p>';return}const rows=sorted(ROWS.filter(r=>good(r[a])&&good(r[b])),a,dir).slice(0,limit),ma=Math.max(...rows.map(r=>Math.abs(num(r[a]))),1),mb=Math.max(...rows.map(r=>Math.abs(num(r[b]))),1);host.innerHTML=`<div class="legend"><span><i></i>${esc(metricName(a))}</span><span><i class="alt-key"></i>${esc(metricName(b))}</span></div><div class="compare-chart">`+rows.map(r=>`<div class="compare-item"><div class="compare-head"><span>${esc(r[EKEY])}</span><span>${esc(fmt(r[a],a))} / ${esc(fmt(r[b],b))}</span></div><div class="compare-track"><div class="compare-fill" style="--p:${Math.abs(num(r[a]))/ma*100}%"></div></div><div class="compare-track"><div class="compare-fill alt-fill" style="--p:${Math.abs(num(r[b]))/mb*100}%"></div></div></div>`).join('')+`</div><p class="widget-note">Each measure is scaled independently. Bar lengths should not be compared across different units.</p>`}
function cards(host,metrics){const keys=(metrics.length?metrics:[S.primary_metric]).filter(Boolean);let out='';for(const k of keys){const vals=ROWS.map(r=>num(r[k])).filter(Number.isFinite);if(!vals.length)continue;const avg=vals.reduce((a,b)=>a+b,0)/vals.length;out+='<article class="metric-card"><span class="metric-number">'+esc(fmt(avg,k))+'</span><span class="metric-label">Average '+esc(metricName(k))+'</span></article>';out+='<article class="metric-card"><span class="metric-number">'+esc(fmt(Math.max(...vals),k))+'</span><span class="metric-label">Highest '+esc(metricName(k))+'</span></article>'}host.innerHTML=out?'<div class="metric-grid">'+out+'</div>':'<p class="empty">No valid metrics for snapshot cards.</p>'}
function scatter(host,metrics){const [xk,yk]=metrics;if(!xk||!yk){host.innerHTML='<p class="empty">Choose two numeric metric keys.</p>';return}const pts=ROWS.filter(r=>good(r[xk])&&good(r[yk]));if(!pts.length){host.innerHTML='<p class="empty">No points for this metric pair.</p>';return}const x0=Math.min(...pts.map(r=>num(r[xk]))),x1=Math.max(...pts.map(r=>num(r[xk]))),y0=Math.min(...pts.map(r=>num(r[yk]))),y1=Math.max(...pts.map(r=>num(r[yk]))),W=880,H=460,left=90,right=38,top=25,bottom=70,xscale=v=>left+(num(v)-x0)/(x1-x0||1)*(W-left-right),yscale=v=>top+(1-(num(v)-y0)/(y1-y0||1))*(H-top-bottom);let v=`<svg class="scatter-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Scatterplot of ${esc(metricName(xk))} versus ${esc(metricName(yk))}">`;for(let i=0;i<=4;i++){let gx=left+(W-left-right)*i/4,gy=top+(H-top-bottom)*i/4;v+=`<line x1="${gx}" y1="${top}" x2="${gx}" y2="${H-bottom}" class="scatter-grid"/><line x1="${left}" y1="${gy}" x2="${W-right}" y2="${gy}" class="scatter-grid"/><text x="${gx}" y="${H-bottom+22}" text-anchor="middle" class="scatter-label">${esc((x0+(x1-x0)*i/4).toFixed(1))}</text><text x="${left-10}" y="${gy+4}" text-anchor="end" class="scatter-label">${esc((y1-(y1-y0)*i/4).toFixed(1))}</text>`}v+=`<line x1="${left}" y1="${H-bottom}" x2="${W-right}" y2="${H-bottom}" class="scatter-axis"/><line x1="${left}" y1="${top}" x2="${left}" y2="${H-bottom}" class="scatter-axis"/><text x="${W/2}" y="${H-12}" text-anchor="middle" class="scatter-label">${esc(metricName(xk))}</text><text x="16" y="${H/2}" transform="rotate(-90 16 ${H/2})" text-anchor="middle" class="scatter-label">${esc(metricName(yk))}</text>`;for(const r of pts){v+=`<circle class="scatter-dot" cx="${xscale(r[xk])}" cy="${yscale(r[yk])}" r="${pts.length>200?4:7}"><title>${esc(r[EKEY])}: ${esc(fmt(r[xk],xk))} / ${esc(fmt(r[yk],yk))}</title></circle>`}v+='</svg>';host.innerHTML='<div class="scatter-box">'+v+'<p class="scatter-caption">Hover over any point for the record name and exact values.</p></div>'}
function map(host,k){const pts=ROWS.filter(r=>good(r.latitude)&&good(r.longitude)&&Math.abs(num(r.latitude))<=90&&Math.abs(num(r.longitude))<=180);if(!pts.length){host.innerHTML='<p class="map-error">Map unavailable: provide latitude and longitude columns.</p>';return}if(typeof window.L==='undefined'){host.innerHTML='<p class="map-error">The map needs an internet connection to load its map library and tiles. All other charts and tables work offline.</p>';return}host.innerHTML='<div class="map-box"></div>';const m=L.map($('.map-box',host),{scrollWheelZoom:false});L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(m);const vals=pts.map(r=>num(r[k])).filter(Number.isFinite),lo=Math.min(...vals),hi=Math.max(...vals);const markers=[];pts.forEach(r=>{let value=num(r[k]);let radius=Number.isFinite(value)?6+10*((value-lo)/(hi-lo||1)):7;let marker=L.circleMarker([num(r.latitude),num(r.longitude)],{radius,color:'#ffffff',weight:2,fillColor:getComputedStyle(document.documentElement).getPropertyValue('--primary').trim(),fillOpacity:.84}).addTo(m);marker.bindPopup('<strong>'+esc(r[EKEY])+'</strong><div>'+esc(metricName(k))+': '+esc(fmt(r[k],k))+'</div>');markers.push(marker)});if(markers.length)m.fitBounds(L.featureGroup(markers).getBounds().pad(.16),{maxZoom:10});setTimeout(()=>m.invalidateSize(),300)}
const kind=w.dataset.widget,k=w.dataset.metric,dir=w.dataset.direction,limit=Number(w.dataset.limit)||12;let metrics=[];try{metrics=JSON.parse(w.dataset.metrics||'[]')}catch{}const host=$('.widget-content',w)||$('.table-view',w);
if(kind==='ranking'){chart($('.chart-view',w),k,dir,limit);table($('.table-view',w),k,dir,false);$$('[data-view]',w).forEach(b=>b.addEventListener('click',()=>{$$('[data-view]',w).forEach(x=>x.classList.toggle('active',x===b));$('.chart-view',w).hidden=b.dataset.view!=='chart';$('.table-view',w).hidden=b.dataset.view!=='table';if(b.dataset.view==='chart'){$('.bar-chart',w)?.classList.add('visible')}}));$$('[data-export]',w).forEach(b=>b.addEventListener('click',()=>b.dataset.export==='png'?imageExport(w):csvExport()))}
else if(kind==='heatmap')table(host,k,dir,true);
else if(kind==='table_ranking')table(host,k,dir,false);
else if(kind==='comparison'){comparison(host,metrics,limit,dir);reveal($('.compare-chart',w));}
else if(kind==='scatter'){scatter(host,metrics);$$('.scatter-dot',w).forEach((x,i)=>{x.style.setProperty('--stagger',(i%25*25)+'ms')});}
else if(kind==='metric_cards')cards(host,metrics);
else if(kind==='map')map(host,k);

});
})();
"""

def _quick_limit(dataset):
    # Top 10 for long rankings; <=20 full; optionally all 30/32 teams.
    size=len(dataset["rows"])
    override=n(dataset.get("quick_display_limit"))
    if override is not None and override>0:
        return min(size,int(override))
    if dataset.get("show_all_quick") is True:
        return size
    if size <=20:
        return size
    key=str(dataset.get("entity_key", "")).lower()
    if size in (30,32) and any(x in key for x in ("team", "franchise", "club")):
        return size
    return 10


def render(spec, brand="Action Network", mode="quick_visual", logo_uri=None):
    spec=normalize(spec)
    if brand not in BRANDS:
        raise ValueError(f"Unknown brand '{brand}'.")
    if mode=="simple":
        mode="quick_visual"  # legacy compatibility
    if mode not in ("quick_table", "quick_visual", "detailed", "selected"):
        raise ValueError("Mode must be quick_table, quick_visual, detailed, or selected.")
    theme=BRANDS[brand]
    css=CSS
    for key in ("primary","bright","dark","navy","navy2","soft"):
        css=css.replace("__"+key.upper()+"__",theme[key])
    title=e(spec["title"])
    summary=e(spec.get("subtitle") or spec.get("summary") or "")
    header=f'<header class="hero" id="top"><div class="wrap hero-inner"><div class="hero-top">{logo_html(brand,theme,logo_uri)}<span class="research-mark">Data & Research / {e(spec.get("date", ""))}</span></div><span class="eyebrow">{e(spec.get("kicker", "Original Research"))}</span><h1>{title}</h1>'
    if summary:header+=f'<p class="dek">{summary}</p>'
    if spec.get("byline"):header+=f'<p class="byline">{e(spec["byline"])}</p>'
    if spec.get("hero_stats"):
        header+='<div class="hero-stats">'+''.join(f'<div class="hero-stat"><strong>{e(x.get("value", ""))}</strong><small>{e(x.get("label", ""))}</small></div>' for x in spec["hero_stats"][:4])+'</div>'
    header+='</div></header>'
    intro=''.join(f'<p>{e(x)}</p>' for x in spec.get("intro",[]))
    intro_section=f'<section class="section" id="overview"><div class="wrap"><div class="section-heading"><span class="eyebrow">Study Overview</span><h2>{e(spec.get("overview_heading", "What the Data Reveals"))}</h2></div><div class="intro">{intro or e(spec.get("summary", ""))}</div></div></section>' if intro or spec.get("summary") else ''
    finding_section=f'<section class="section alt" id="findings"><div class="wrap"><div class="section-heading"><span class="eyebrow">Key Takeaways</span><h2>{e(spec.get("findings_heading", "The Biggest Findings"))}</h2><p>{e(spec.get("findings_dek", "The standout results from the analysis."))}</p></div>{findings_html(spec, compact=mode not in ("detailed","selected"))}</div></section>' if spec.get("key_findings") else ''
    sections=[]
    if mode == "selected":
        check_selected_page(spec)
        for sec in spec["page"]["sections"]:
            copied=copy.deepcopy(sec)
            copied["dataset_id"]=jid(copied.get("dataset_id") or spec["datasets"][0]["id"])
            if copied["type"]=="ranking":
                maximum=12 if spec["template"].get("depth")=="deep" else 50
                copied["limit"]=min(maximum,int(n(copied.get("limit",12)) or 12))
            sections.append(copied)
    elif mode in ("quick_table","quick_visual"):
        for i,d in enumerate(spec["datasets"],1):
            count=len(d["rows"])
            display=_quick_limit(d)
            sec={"dataset_id":d["id"],"title":d["title"],"description":d.get("description") or (f"Explore the {count:,} records in this ranking. Switch views or search the complete table."),"metric":d["primary_metric"],"direction":d.get("direction","desc"),"limit":display,"table_page":12}
            sec["type"]="table_ranking" if mode=="quick_table" else "ranking"
            sections.append(sec)
        if mode=="quick_visual":
            primary=spec["datasets"][0]
            numeric=[x["key"] for x in primary["columns"] if x.get("type") in ("number","percent","integer","currency")]
            coords=any(n(row.get("latitude")) is not None and n(row.get("longitude")) is not None for row in primary["rows"])
            if coords:
                sections.append({"type":"map","dataset_id":primary["id"],"title":"Geographic View","description":"Explore the verified geographic points behind the ranking.","metric":primary["primary_metric"]})
            elif len(numeric)>=2:
                metrics=[k for k in numeric if k!=primary["primary_metric"]][:2]
                if len(metrics)==2:
                    sections.append({"type":"comparison","dataset_id":primary["id"],"title":"Behind the Rankings","description":"A closer comparison of two underlying measures.","metrics":metrics,"limit":min(display,10)})
    else:
        seen=set()
        for sec in spec.get("detailed",{}).get("sections",[]):
            if not isinstance(sec,dict) or sec.get("type") not in WIDGET_TYPES:
                continue
            copied=copy.deepcopy(sec)
            copied["dataset_id"]=jid(copied.get("dataset_id") or spec["datasets"][0]["id"])
            d=next((x for x in spec["datasets"] if x["id"]==copied["dataset_id"]),None)
            if d is None:
                continue
            if copied["type"]=="ranking":
                copied["limit"]=min(12,int(n(copied.get("limit",12)) or 12))
                seen.add(d["id"])
            elif copied["type"]=="comparison":
                copied["limit"]=min(12,int(n(copied.get("limit",12)) or 12))
            sections.append(copied)
        for d in spec["datasets"]:
            if d["id"] not in seen:
                sections.append({"type":"ranking","dataset_id":d["id"],"title":d["title"],"description":d.get("description") or "Full rankings available using the search and paginated chart/table views.","metric":d["primary_metric"],"limit":12,"table_page":12})
    content=[];navlinks=[]
    for i,sec in enumerate(sections,1):
        html_section=widget_html(sec["type"],spec,sec,i)
        # widget_html creates the section shell; wrap the content in the shared page grid.
        html_section=re.sub(r'(<section class="section" id="w\d+">)(.*?)(</section>)',r'\1<div class="wrap">\2</div>\3',html_section,flags=re.S)
        content.append(html_section)
        navlinks.append((f"w{i}",str(sec.get("nav_title") or sec.get("title") or sec.get("type")).strip()[:34]))
    if mode in ("detailed","selected") and spec.get("detailed",{}).get("closing"):
        content.append(f'<section class="section alt"><div class="wrap"><div class="editorial-callout"><p>{e(spec["detailed"]["closing"])}</p></div></div></section>')
    if mode not in ("detailed","selected") and spec.get("simple",{}).get("closing"):
        content.append(f'<section class="section alt"><div class="wrap"><div class="editorial-callout"><p>{e(spec["simple"]["closing"])}</p></div></div></section>')
    method=f'<section class="section alt" id="methodology"><div class="wrap"><div class="section-heading"><span class="eyebrow">Research Notes</span><h2>Methodology & Sources</h2><p>How the analysis was conducted and where the data came from.</p></div>{method_html(spec)}<div class="backtop-row"><a class="backtop" href="#top">↑ Back to top</a></div></div></section>'
    links=[]
    if intro_section:links.append(("overview","Overview"))
    if finding_section:links.append(("findings","Key Findings"))
    links.extend(navlinks)
    links.append(("methodology","Methodology"))
    nav='<nav class="nav" aria-label="Page sections"><div class="wrap nav-inner">'+''.join(f'<a href="#{e(key)}">{e(label)}</a>' for key,label in links)+'<button class="motion-replay" type="button" data-replay title="Replay entrance animations">↻ Replay motion</button></div></nav>'
    labels={"quick_table":"Quick Read · Tables","quick_visual":"Quick Read · Visual","detailed":"Deep Dive","selected":"Selected Template"}
    footer=f'<footer class="footer"><div class="wrap"><strong>{e(brand)}</strong><span>{e(spec.get("footer_note", "Original data-led research"))} · {labels[mode]}</span></div></footer>'
    use_map=any(x.get("type")=="map" for x in sections)
    deps='<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>' if use_map else ''
    boot=f'document.addEventListener("DOMContentLoaded",()=>{{{JS}}});' if use_map else JS
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>{title} | {e(brand)}</title><meta name="description" content="{e(spec.get("summary") or spec.get("subtitle") or spec["title"])}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800;900&family=Source+Serif+4:wght@400;500;600;700&display=swap" rel="stylesheet">{deps}<style>{css}</style></head><body class="visual-style-{spec["visual_style"]} template-{jid((spec.get("template") or {}).get("template_id") or "visual_rankings")}">{header}{nav}<main>{intro_section}{finding_section}{''.join(content)}{method}</main>{footer}<script id="lp-data" type="application/json">{json_for_script(spec)}</script><script>{boot}</script></body></html>'''
