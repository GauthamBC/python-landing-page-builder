"""Deterministic, brand-aware data-led landing page HTML generator.

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
    "Action Network": dict(primary="#00b67a", bright="#00e09a", dark="#00865b", navy="#101820", navy2="#152630", soft="#e8fff6", wordmark="ACTION NETWORK", note="Reference styling extracted from supplied Action Network landing pages."),
    "VegasInsider": dict(primary="#18b8da", bright="#6bd9f3", dark="#007b9c", navy="#111925", navy2="#1e3042", soft="#e7f8fc", wordmark="VEGASINSIDER", note="Provisional palette and text lockup. Replace with approved brand assets before publishing."),
    "RotoGrinders": dict(primary="#f4ad2e", bright="#ffd16b", dark="#af7100", navy="#141a21", navy2="#263240", soft="#fff7e6", wordmark="ROTOGRINDERS", note="Provisional palette and text lockup. Replace with approved brand assets before publishing."),
    "Canada Sports Betting": dict(primary="#d71931", bright="#ff6272", dark="#a10a20", navy="#121212", navy2="#292929", soft="#fff0f1", wordmark="CANADA SPORTS BETTING", note="Red/black starting palette and text lockup; verify against approved brand assets."),
}
WIDGET_TYPES = {
    "ranking": "Animated bars and searchable, sortable table toggle",
    "heatmap": "Full ranking table with gradient metric heatmap",
    "comparison": "Two-metric side-by-side bar comparison",
    "scatter": "Interactive SVG two-metric scatterplot",
    "map": "Interactive geographic pins with Leaflet (requires latitude/longitude)",
    "metric_cards": "Dynamic min, max, mean, total snapshot cards",
    "callout": "Editorial analysis pull quote / takeaway",
}

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
        items.append('<div class="sources"><strong>Sources</strong>' + ' · '.join(links) + '</div>')
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
    metric = str(section.get("metric") or spec.get("primary_metric") or "")
    title = section.get("title") or {"ranking":"Ranking", "heatmap":"Full Results", "map":"Geographic Breakdown", "scatter":"Compare Two Measures", "comparison":"Side-by-Side Comparison", "metric_cards":"At a Glance", "callout":"What the Numbers Mean"}.get(kind, "Data Explorer")
    desc = section.get("description", "")
    title_html = f'<div class="section-heading"><span class="eyebrow">Data Explorer / {idx:02d}</span><h2>{e(title)}</h2>{f"<p>{e(desc)}</p>" if desc else ""}</div>'
    if kind == "callout":
        return f'<section class="section" id="{base}">{title_html}<div class="editorial-callout"><p>{e(section.get("text", ""))}</p></div></section>'
    attrs = f'data-widget="{e(kind)}" data-id="{base}" data-metric="{e(metric)}" data-direction="{e(section.get("direction", "desc"))}" data-limit="{int(n(section.get("limit", 12)) or 12)}"'
    mets = section.get("metrics", [])
    if isinstance(mets, list):
        attrs += f' data-metrics="{e(json.dumps(mets))}"'
    if kind == "ranking":
        content = f'<div class="visual-frame"><div class="visual-controls"><div class="view-buttons"><button class="view-btn active" type="button" data-view="chart">Bar Chart</button><button class="view-btn" type="button" data-view="table">Full Table</button></div><div class="view-buttons"><button class="export-btn" data-export="png" type="button">Export PNG ↓</button><button class="export-btn" data-export="csv" type="button">Export CSV ↓</button></div></div><div class="view chart-view"></div><div class="view table-view" hidden></div></div>'
    elif kind == "heatmap":
        content = '<div class="visual-frame"><div class="view table-view"></div></div>'
    else:
        content = '<div class="visual-frame"><div class="view widget-content"></div></div>'
    return f'<section class="section" id="{base}">{title_html}<div class="widget" {attrs}>{content}</div></section>'

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800;900&family=Source+Serif+4:wght@400;500;600;700&display=swap');
:root{--primary:__PRIMARY__;--bright:__BRIGHT__;--dark:__DARK__;--navy:__NAVY__;--navy2:__NAVY2__;--soft:__SOFT__;--line:#dce6e2;--ink:#1e2930;--muted:#65737c;--white:#fff;--wash:#f6f9f7;--display:'Barlow Condensed','Arial Narrow',sans-serif;--serif:'Source Serif 4',Georgia,serif}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:75px;scrollbar-color:var(--primary) #e6ece9;scrollbar-width:thin}html::-webkit-scrollbar,.rank-scroll::-webkit-scrollbar,.nav-inner::-webkit-scrollbar{width:7px;height:7px}html::-webkit-scrollbar-thumb,.rank-scroll::-webkit-scrollbar-thumb,.nav-inner::-webkit-scrollbar-thumb{background:var(--primary);border-radius:12px}html::-webkit-scrollbar-track,.rank-scroll::-webkit-scrollbar-track{background:#e6ece9}body{margin:0;background:var(--white);color:var(--ink);font:17px/1.66 var(--serif);overflow-x:hidden}button,input{font:inherit}button{cursor:pointer}a{color:var(--dark)}a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid var(--bright);outline-offset:2px}h1,h2,h3,p{margin-top:0}h1,h2,h3,button,.eyebrow,.brand-lockup,.feature-num,.hero-stat strong,.metric-number,.rank-pill,.bar-value,.table th,.footer-link,.table-pager,.widget-kicker,.finding-stat{font-family:var(--display)}h2{font-size:clamp(34px,5vw,56px);line-height:1.02;color:var(--navy);letter-spacing:-.012em}h3{line-height:1.13;font-size:25px;color:var(--navy)}.wrap{max-width:1240px;margin:auto;padding:0 clamp(19px,3.4vw,46px)}.hero{position:relative;background:radial-gradient(900px 440px at 90% 12%,color-mix(in srgb,var(--primary) 22%,transparent),transparent 60%),linear-gradient(125deg,#080e13 0%,var(--navy) 51%,var(--navy2) 100%);color:white;overflow:hidden;border-bottom:6px solid var(--primary)}.hero::after{position:absolute;content:"";inset:0;pointer-events:none;background:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:58px 58px;mask-image:linear-gradient(90deg,transparent,#000)}.hero-inner{position:relative;z-index:1;padding-top:clamp(24px,4vw,46px);padding-bottom:clamp(35px,5.5vw,70px)}.hero-top{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:20px;margin-bottom:clamp(34px,5vw,60px)}.brand-lockup{display:inline-flex;align-items:center;gap:12px;font-size:clamp(20px,2.4vw,29px);font-weight:900;letter-spacing:.04em;line-height:1;white-space:nowrap}.brand-image{display:block;height:43px;max-width:min(360px,90vw);width:auto;object-fit:contain}.brand-symbol{height:37px;width:37px}.brand-marker{display:block;width:10px;height:33px;background:var(--bright);transform:skew(-16deg);box-shadow:6px 0 0 color-mix(in srgb,var(--bright) 45%,transparent)}.research-mark{color:#a2b2b9;font:700 12px var(--display);letter-spacing:.15em;text-transform:uppercase}.eyebrow{display:block;font-weight:800;font-size:13px;color:var(--dark);letter-spacing:.14em;text-transform:uppercase}.hero .eyebrow{color:var(--bright);margin-bottom:16px}.hero h1{max-width:1110px;font-size:clamp(43px,6.4vw,87px);line-height:.98;font-weight:900;letter-spacing:-.013em;margin:0}.hero h1 .accent{color:var(--bright)}.dek{margin:22px 0 0;color:#d5e0e4;font-size:clamp(17px,1.8vw,21px);line-height:1.56;max-width:940px}.byline{margin:22px 0 0;color:#95aab2;font:600 14px var(--display);letter-spacing:.045em}.hero-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;margin-top:34px;background:#354c4b;border:1px solid rgba(255,255,255,.1)}.hero-stat{background:rgba(13,24,31,.92);padding:21px 20px}.hero-stat strong{font-size:clamp(27px,3.6vw,45px);line-height:1;font-weight:900;color:var(--bright);display:block}.hero-stat small{display:block;font:700 12px/1.3 var(--display);letter-spacing:.1em;text-transform:uppercase;color:#b0c1c8;margin-top:9px}.nav{position:sticky;top:0;z-index:30;backdrop-filter:blur(12px);background:rgba(255,255,255,.97);border-bottom:1px solid var(--line);box-shadow:0 4px 14px rgba(0,0,0,.035)}.nav-inner{display:flex;gap:8px;align-items:center;overflow-x:auto;padding-top:10px;padding-bottom:10px;scrollbar-width:thin;scrollbar-color:var(--primary) transparent}.nav a{text-decoration:none;white-space:nowrap;font:800 14px var(--display);letter-spacing:.04em;color:var(--navy);border:1px solid var(--line);border-bottom:3px solid var(--primary);padding:7px 14px;transition:.15s}.nav a:hover{background:var(--navy);color:white}.section{padding:clamp(40px,5.4vw,75px) 0;border-bottom:1px solid var(--line);scroll-margin-top:72px}.section.alt{background:var(--wash)}.section-heading{max-width:980px;margin-bottom:27px}.section-heading .eyebrow{margin-bottom:8px}.section-heading h2{margin-bottom:15px}.section-heading p{color:var(--muted);font-size:17px;line-height:1.58;margin:0}.intro{font-size:19px;max-width:980px}.intro p{margin:0 0 17px}.findings{display:grid;grid-template-columns:1fr;gap:12px}.finding{display:grid;grid-template-columns:minmax(95px,180px) 1fr;align-items:center;gap:20px;padding:22px 25px;border:1px solid var(--line);border-left:6px solid var(--primary);background:white;box-shadow:0 8px 22px rgba(16,24,32,.04)}.finding.featured{background:linear-gradient(120deg,var(--navy) 40%,var(--navy2));border-left-color:var(--bright);color:white}.finding-stat{font-size:clamp(31px,4.2vw,51px);line-height:1;color:var(--dark);font-weight:900;overflow-wrap:anywhere}.featured .finding-stat{color:var(--bright)}.finding h3{margin:0 0 5px;font-size:25px;font-weight:800}.finding p{margin:0;font-size:15px;line-height:1.55;color:var(--muted)}.finding.featured h3{color:white}.finding.featured p{color:#c5d1d6}.visual-frame{border:1px solid var(--line);background:#fff;box-shadow:0 14px 40px rgba(16,24,32,.065);overflow:hidden}.visual-controls{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;align-items:center;padding:13px 16px;background:var(--wash);border-bottom:1px solid var(--line)}.view-buttons{display:flex;gap:8px;flex-wrap:wrap}.view-btn,.export-btn,.table-pager button,.table-search{border:1px solid #cdd9d4;background:#fff;color:var(--navy);padding:10px 15px;font:800 14px var(--display);letter-spacing:.035em}.view-btn.active,.view-btn:hover{background:var(--primary);border-color:var(--primary);color:var(--navy)}.export-btn:hover,.table-pager button:hover{border-color:var(--dark)}.view[hidden]{display:none!important}.bar-chart{display:grid;gap:13px;padding:25px 26px 27px}.bar-row{display:grid;grid-template-columns:45px minmax(125px,225px) minmax(95px,1fr) 95px;gap:13px;align-items:center}.rank-pill{height:34px;width:38px;background:var(--navy);color:var(--bright);font-size:16px;font-weight:900;display:grid;place-items:center}.bar-label{font:800 18px/1.16 var(--display);color:var(--navy);overflow-wrap:anywhere}.bar-track{height:29px;background:#e8efeb;overflow:hidden}.bar-fill{height:100%;width:0;background:linear-gradient(90deg,var(--primary),var(--dark));transition:width 800ms cubic-bezier(.2,.75,.2,1)}.bar-chart.visible .bar-fill{width:var(--p)}.bar-value{text-align:right;font-size:23px;line-height:1.15;color:var(--navy);font-weight:900;white-space:nowrap}.widget-note{font:14px/1.45 var(--serif);color:var(--muted);padding:4px 26px 21px}.table-tools{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 16px}.table-search{font:14px var(--serif);max-width:370px;width:100%;min-width:0;font-weight:400}.table-count{font:800 13px var(--display);color:var(--muted);white-space:nowrap}.rank-scroll{overflow-x:auto;scrollbar-width:thin;scrollbar-color:var(--primary) #e6ece9}.table{border-collapse:collapse;width:100%;min-width:690px;font-size:14px}.table th{position:sticky;top:0;text-align:left;font-weight:800;text-transform:none;letter-spacing:.03em;font-size:15px;color:white;background:var(--navy);padding:14px 15px;cursor:pointer;white-space:nowrap}.table th:hover{background:var(--navy2)}.table td{padding:13px 15px;border-bottom:1px solid var(--line);white-space:nowrap}.table tbody tr:nth-child(even){background:#f8faf9}.table tbody tr:hover{background:var(--soft)}.table td.namecell{font-weight:700;color:var(--navy)}.heat-cell{box-shadow:inset 4px 0 var(--primary);background-color:var(--shade)!important;font-weight:800}.table-pager{display:flex;align-items:center;justify-content:center;gap:14px;padding:12px;border-top:1px solid var(--line);font-size:14px}.table-pager button{padding:7px 11px}.table-pager button:disabled{opacity:.35;cursor:default}.editorial-callout{color:#fff;background:linear-gradient(130deg,var(--navy),var(--navy2));border-left:6px solid var(--bright);padding:30px 36px}.editorial-callout p{margin:0;font-size:clamp(19px,2.1vw,25px);line-height:1.5}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:12px;padding:20px}.metric-card{border:1px solid var(--line);border-top:5px solid var(--primary);background:var(--wash);padding:22px}.metric-number{font-size:39px;line-height:1;display:block;color:var(--dark);font-weight:900}.metric-label{font:800 15px var(--display);margin-top:11px;display:block;color:var(--navy);text-transform:capitalize}.compare-chart{padding:22px;display:grid;gap:19px}.compare-item{padding-bottom:18px;border-bottom:1px solid var(--line)}.compare-head{display:flex;justify-content:space-between;gap:12px;font:800 18px var(--display);color:var(--navy);margin-bottom:11px}.compare-track{position:relative;min-height:17px;background:#e9eeeb;margin:5px 0;overflow:hidden}.compare-fill{height:17px;background:var(--primary);width:var(--p)}.compare-fill.alt-fill{background:#6f91a4}.legend{display:flex;flex-wrap:wrap;gap:20px;padding:15px 23px 0;font:800 13px var(--display);color:var(--muted)}.legend i{display:inline-block;width:11px;height:11px;margin-right:6px;background:var(--primary)}.legend .alt-key{background:#6f91a4}.scatter-box{padding:20px}.scatter-svg{display:block;width:100%;max-height:520px}.scatter-axis{stroke:#a8bcb2;stroke-width:1.2}.scatter-grid{stroke:#e2eae6;stroke-width:1}.scatter-dot{fill:var(--primary);stroke:white;stroke-width:2;opacity:.82;cursor:pointer}.scatter-dot:hover{stroke:var(--navy);stroke-width:3;opacity:1}.scatter-label{fill:var(--muted);font:13px var(--display)}.scatter-caption{margin:8px 0 0;color:var(--muted);font-size:14px}.map-box{height:480px;min-height:320px;z-index:1}.map-error{padding:24px;background:var(--soft);font-size:15px}.map-pin{border-radius:50%}.method-summary{font-size:18px;max-width:960px}.method-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.method-card{border:1px solid var(--line);border-top:4px solid var(--primary);padding:24px;background:var(--wash)}.method-number{font:900 29px var(--display);color:var(--dark)}.method-card h3{font-size:23px;margin:10px 0 8px}.method-card p{font-size:15px;line-height:1.52;color:var(--muted);margin:0}.method-notes{padding:20px 0;color:var(--muted);font-size:15px}.method-notes p{margin:0 0 10px}.sources{border-left:4px solid var(--primary);background:var(--soft);padding:17px 20px;font-size:14px;margin-top:22px}.footer{background:var(--navy);color:#b7c8cd;padding:30px 0;font:14px/1.5 var(--serif)}.footer .wrap{display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px}.footer strong{color:var(--bright);font:800 16px var(--display)}.footer-link{color:var(--bright);text-decoration:none;font-weight:800}.backtop{margin-top:24px;display:inline-block;text-decoration:none;font:800 15px var(--display);color:var(--dark)}.empty{padding:26px;color:var(--muted)}
@media(max-width:750px){.hero-top{margin-bottom:35px}.research-mark{display:none}.bar-chart{padding:15px 12px}.bar-row{grid-template-columns:30px minmax(85px,135px) minmax(45px,1fr) 65px;gap:6px}.rank-pill{width:28px;height:28px;font-size:13px}.bar-label{font-size:14px}.bar-value{font-size:17px}.bar-track{height:22px}.finding{grid-template-columns:1fr;gap:10px;padding:20px}.finding-stat{font-size:39px}.finding h3{font-size:23px}.section{padding:42px 0}.visual-controls{padding:10px}.view-btn,.export-btn{padding:9px 10px;font-size:12px}.metric-grid{grid-template-columns:1fr 1fr}.map-box{height:360px}}
@media(max-width:480px){.metric-grid{grid-template-columns:1fr}.bar-row{grid-template-columns:25px minmax(80px,110px) minmax(20px,1fr) 55px}.bar-label{font-size:12.5px}.bar-value{font-size:15px}.bar-track{height:18px}.rank-pill{width:24px;height:25px}.dek{font-size:17px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}.bar-fill{width:var(--p)!important}}
@media print{.nav,.visual-controls,.table-tools,.table-pager,.backtop{display:none!important}.bar-fill{width:var(--p)!important}.section{break-inside:avoid}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

JS = r"""
(()=>{'use strict';
const S=JSON.parse(document.getElementById('lp-data').textContent),ROWS=S.rows||[],COLS=S.columns||[],EKEY=S.entity_key||'name';
const $=(q,root=document)=>root.querySelector(q),$$=(q,root=document)=>Array.from(root.querySelectorAll(q));
const esc=(v)=>String(v==null?'':v).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const num=(v)=>v===null||v===undefined||v===''?NaN:Number(v);
const good=(v)=>Number.isFinite(num(v));
const col=(k)=>COLS.find(c=>c.key===k)||{key:k,label:k,type:'number'};
const fmt=(v,k)=>{const c=col(k),x=num(v);if(!good(v))return v===null||v===undefined?'—':String(v); const digs=c.decimals!=null?Math.max(0,Math.min(6,Number(c.decimals))):(c.type==='integer'?0:2);const f=new Intl.NumberFormat('en-US',{maximumFractionDigits:digs,minimumFractionDigits:c.decimals===undefined?0:digs}); if(c.type==='currency')return (c.prefix||'$')+f.format(x);if(c.type==='percent')return f.format(x)+'%';return (c.prefix||'')+f.format(x)+(c.suffix||'')};
const metricName=(k)=>col(k).label||k;
function sorted(rows,k,dir){return [...rows].sort((a,b)=>{const x=num(a[k]),y=num(b[k]);if(Number.isFinite(x)&&Number.isFinite(y))return (dir==='asc'?1:-1)*(x-y);if(Number.isFinite(x))return -1;if(Number.isFinite(y))return 1;return String(a[k]||'').localeCompare(String(b[k]||''))*(dir==='asc'?1:-1)});}
function imageExport(widget){const target=$('.chart-view',widget);if(!target)return;const old=target.hidden;target.hidden=false;
function proceed(){if(typeof window.html2canvas!=='function'){alert('PNG export needs a connection to load the screenshot library.');target.hidden=old;return} const width=Math.max(600,target.scrollWidth);const scale=Math.max(2,Math.ceil(2560/width));target.classList.add('exporting');html2canvas(target,{backgroundColor:'#ffffff',scale:scale,useCORS:true,windowWidth:Math.max(window.innerWidth,1100)}).then(canvas=>{const link=document.createElement('a');link.download=(S.slug||'study')+'-chart.png';link.href=canvas.toDataURL('image/png');link.click()}).catch(err=>alert('PNG export could not finish: '+err.message)).finally(()=>{target.hidden=old;target.classList.remove('exporting')})}
if(window.html2canvas){proceed();return} const script=document.createElement('script');script.src='https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';script.onload=proceed;script.onerror=()=>{target.hidden=old;alert('Image export requires internet access on the first use.')};document.head.appendChild(script)}
function csvExport(){const headers=COLS.length?COLS.map(c=>c.key):Object.keys(ROWS[0]||{});const quote=x=>'"'+String(x??'').replace(/"/g,'""')+'"';const body=[headers.map(quote).join(','),...ROWS.map(r=>headers.map(k=>quote(r[k])).join(','))].join('\r\n');const a=document.createElement('a'),url=URL.createObjectURL(new Blob(['\ufeff'+body],{type:'text/csv;charset=utf-8'}));a.href=url;a.download=(S.slug||'study')+'-data.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000)}
function chart(host,k,dir,limit){let rows=sorted(ROWS.filter(r=>good(r[k])),k,dir).slice(0,Math.max(1,limit)),max=Math.max(...rows.map(r=>Math.abs(num(r[k]))),1);if(!rows.length){host.innerHTML='<p class="empty">No numeric data to display for '+esc(k)+'.</p>';return}host.innerHTML='<div class="bar-chart">'+rows.map((r,i)=>`<div class="bar-row"><span class="rank-pill">${i+1}</span><div class="bar-label" title="${esc(r[EKEY])}">${esc(r[EKEY])}</div><div class="bar-track"><div class="bar-fill" style="--p:${Math.max(1,Math.abs(num(r[k]))/max*100).toFixed(2)}%"></div></div><div class="bar-value">${esc(fmt(r[k],k))}</div></div>`).join('')+'</div><div class="widget-note">Sorted by '+esc(metricName(k))+'. Switch to the table to view every record and additional measures.</div>';requestAnimationFrame(()=>requestAnimationFrame(()=>$('.bar-chart',host)?.classList.add('visible')))}
function table(host,k,dir,heat){const columns=COLS.length?COLS:Object.keys(ROWS[0]||{}).map(key=>({key,label:key}));let query='',sortKey=k||columns[0]?.key,sortDir=dir||'desc',page=0;const PAGE=15;host.innerHTML='<div class="table-tools"><input class="table-search" type="search" placeholder="Search the full ranking..." aria-label="Search records"><span class="table-count"></span></div><div class="rank-scroll"><table class="table"><thead><tr>'+columns.map(c=>`<th tabindex="0" scope="col" data-col="${esc(c.key)}">${esc(c.label||c.key)} <span class="sort-icon">↕</span></th>`).join('')+'</tr></thead><tbody></tbody></table></div><div class="table-pager"><button type="button" data-p="prev">← Previous</button><span class="pagenumber"></span><button type="button" data-p="next">Next →</button></div>';
const tbody=$('tbody',host),count=$('.table-count',host),pager=$('.table-pager',host);
function draw(){const filtered=ROWS.filter(r=>!query||Object.values(r).some(v=>String(v??'').toLowerCase().includes(query)));const ordered=sorted(filtered,sortKey,sortDir),maxPage=Math.max(0,Math.ceil(ordered.length/PAGE)-1);page=Math.min(page,maxPage);const take=ordered.slice(page*PAGE,page*PAGE+PAGE);let mn=Math.min(...filtered.map(r=>num(r[k])).filter(Number.isFinite)),mx=Math.max(...filtered.map(r=>num(r[k])).filter(Number.isFinite));
tbody.innerHTML=take.map(r=>'<tr>'+columns.map(c=>{const val=r[c.key],isHeat=heat&&c.key===k&&good(val);const norm=mx===mn?.5:(num(val)-mn)/(mx-mn);const shade=isHeat?` style="--shade:color-mix(in srgb, var(--primary) ${Math.round(7+28*norm)}%, white)"`:'';return `<td class="${c.key===EKEY?'namecell ':''}${isHeat?'heat-cell':''}"${shade}>${esc(fmt(val,c.key))}</td>`}).join('')+'</tr>').join('')||`<tr><td colspan="${columns.length}">No matching records</td></tr>`;
count.textContent=filtered.length.toLocaleString()+' records';$('.pagenumber',host).textContent=(page+1)+' / '+(maxPage+1);$('[data-p="prev"]',pager).disabled=page===0;$('[data-p="next"]',pager).disabled=page>=maxPage;$$('th',host).forEach(th=>{$('.sort-icon',th).textContent=th.dataset.col===sortKey?(sortDir==='asc'?'↑':'↓'):'↕'});}
$('.table-search',host).addEventListener('input',ev=>{query=ev.target.value.toLowerCase().trim();page=0;draw()});$$('th',host).forEach(th=>{const click=()=>{if(sortKey===th.dataset.col)sortDir=sortDir==='asc'?'desc':'asc';else{sortKey=th.dataset.col;sortDir='desc'}page=0;draw()};th.addEventListener('click',click);th.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();click()}})});$$('[data-p]',pager).forEach(b=>b.addEventListener('click',()=>{page+=b.dataset.p==='next'?1:-1;draw()}));draw()}
function comparison(host,metrics,limit,dir){const [a,b]=metrics;if(!a||!b){host.innerHTML='<p class="empty">Specify two metric keys for this comparison.</p>';return}const rows=sorted(ROWS.filter(r=>good(r[a])&&good(r[b])),a,dir).slice(0,limit),ma=Math.max(...rows.map(r=>Math.abs(num(r[a]))),1),mb=Math.max(...rows.map(r=>Math.abs(num(r[b]))),1);host.innerHTML=`<div class="legend"><span><i></i>${esc(metricName(a))}</span><span><i class="alt-key"></i>${esc(metricName(b))}</span></div><div class="compare-chart">`+rows.map(r=>`<div class="compare-item"><div class="compare-head"><span>${esc(r[EKEY])}</span><span>${esc(fmt(r[a],a))} / ${esc(fmt(r[b],b))}</span></div><div class="compare-track"><div class="compare-fill" style="--p:${Math.abs(num(r[a]))/ma*100}%"></div></div><div class="compare-track"><div class="compare-fill alt-fill" style="--p:${Math.abs(num(r[b]))/mb*100}%"></div></div></div>`).join('')+`</div><p class="widget-note">Each measure is scaled independently. Bar lengths should not be compared across different units.</p>`}
function cards(host,metrics){const keys=(metrics.length?metrics:[S.primary_metric]).filter(Boolean);let out='';for(const k of keys){const vals=ROWS.map(r=>num(r[k])).filter(Number.isFinite);if(!vals.length)continue;const avg=vals.reduce((a,b)=>a+b,0)/vals.length;out+='<article class="metric-card"><span class="metric-number">'+esc(fmt(avg,k))+'</span><span class="metric-label">Average '+esc(metricName(k))+'</span></article>';out+='<article class="metric-card"><span class="metric-number">'+esc(fmt(Math.max(...vals),k))+'</span><span class="metric-label">Highest '+esc(metricName(k))+'</span></article>'}host.innerHTML=out?'<div class="metric-grid">'+out+'</div>':'<p class="empty">No valid metrics for snapshot cards.</p>'}
function scatter(host,metrics){const [xk,yk]=metrics;if(!xk||!yk){host.innerHTML='<p class="empty">Choose two numeric metric keys.</p>';return}const pts=ROWS.filter(r=>good(r[xk])&&good(r[yk]));if(!pts.length){host.innerHTML='<p class="empty">No points for this metric pair.</p>';return}const x0=Math.min(...pts.map(r=>num(r[xk]))),x1=Math.max(...pts.map(r=>num(r[xk]))),y0=Math.min(...pts.map(r=>num(r[yk]))),y1=Math.max(...pts.map(r=>num(r[yk]))),W=880,H=460,left=90,right=38,top=25,bottom=70,xscale=v=>left+(num(v)-x0)/(x1-x0||1)*(W-left-right),yscale=v=>top+(1-(num(v)-y0)/(y1-y0||1))*(H-top-bottom);let v=`<svg class="scatter-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Scatterplot of ${esc(metricName(xk))} versus ${esc(metricName(yk))}">`;for(let i=0;i<=4;i++){let gx=left+(W-left-right)*i/4,gy=top+(H-top-bottom)*i/4;v+=`<line x1="${gx}" y1="${top}" x2="${gx}" y2="${H-bottom}" class="scatter-grid"/><line x1="${left}" y1="${gy}" x2="${W-right}" y2="${gy}" class="scatter-grid"/><text x="${gx}" y="${H-bottom+22}" text-anchor="middle" class="scatter-label">${esc((x0+(x1-x0)*i/4).toFixed(1))}</text><text x="${left-10}" y="${gy+4}" text-anchor="end" class="scatter-label">${esc((y1-(y1-y0)*i/4).toFixed(1))}</text>`}v+=`<line x1="${left}" y1="${H-bottom}" x2="${W-right}" y2="${H-bottom}" class="scatter-axis"/><line x1="${left}" y1="${top}" x2="${left}" y2="${H-bottom}" class="scatter-axis"/><text x="${W/2}" y="${H-12}" text-anchor="middle" class="scatter-label">${esc(metricName(xk))}</text><text x="16" y="${H/2}" transform="rotate(-90 16 ${H/2})" text-anchor="middle" class="scatter-label">${esc(metricName(yk))}</text>`;for(const r of pts){v+=`<circle class="scatter-dot" cx="${xscale(r[xk])}" cy="${yscale(r[yk])}" r="${pts.length>200?4:7}"><title>${esc(r[EKEY])}: ${esc(fmt(r[xk],xk))} / ${esc(fmt(r[yk],yk))}</title></circle>`}v+='</svg>';host.innerHTML='<div class="scatter-box">'+v+'<p class="scatter-caption">Hover over any point for the record name and exact values.</p></div>'}
function map(host,k){const pts=ROWS.filter(r=>good(r.latitude)&&good(r.longitude)&&Math.abs(num(r.latitude))<=90&&Math.abs(num(r.longitude))<=180);if(!pts.length){host.innerHTML='<p class="map-error">Map unavailable: provide latitude and longitude columns.</p>';return}if(typeof window.L==='undefined'){host.innerHTML='<p class="map-error">The map needs an internet connection to load its map library and tiles. All other charts and tables work offline.</p>';return}host.innerHTML='<div class="map-box"></div>';const m=L.map($('.map-box',host),{scrollWheelZoom:false});L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(m);const vals=pts.map(r=>num(r[k])).filter(Number.isFinite),lo=Math.min(...vals),hi=Math.max(...vals);const markers=[];pts.forEach(r=>{let value=num(r[k]);let radius=Number.isFinite(value)?6+10*((value-lo)/(hi-lo||1)):7;let marker=L.circleMarker([num(r.latitude),num(r.longitude)],{radius,color:'#ffffff',weight:2,fillColor:getComputedStyle(document.documentElement).getPropertyValue('--primary').trim(),fillOpacity:.84}).addTo(m);marker.bindPopup('<strong>'+esc(r[EKEY])+'</strong><div>'+esc(metricName(k))+': '+esc(fmt(r[k],k))+'</div>');markers.push(marker)});if(markers.length)m.fitBounds(L.featureGroup(markers).getBounds().pad(.16),{maxZoom:10});setTimeout(()=>m.invalidateSize(),300)}
$$('[data-widget]').forEach(w=>{const kind=w.dataset.widget,k=w.dataset.metric,dir=w.dataset.direction,limit=Number(w.dataset.limit)||12;let metrics=[];try{metrics=JSON.parse(w.dataset.metrics||'[]')}catch{}const host=$('.widget-content',w)||$('.table-view',w);
if(kind==='ranking'){chart($('.chart-view',w),k,dir,limit);table($('.table-view',w),k,dir,false);$$('[data-view]',w).forEach(b=>b.addEventListener('click',()=>{$$('[data-view]',w).forEach(x=>x.classList.toggle('active',x===b));$('.chart-view',w).hidden=b.dataset.view!=='chart';$('.table-view',w).hidden=b.dataset.view!=='table'}));$$('[data-export]',w).forEach(b=>b.addEventListener('click',()=>b.dataset.export==='png'?imageExport(w):csvExport()))}
else if(kind==='heatmap')table(host,k,dir,true);
else if(kind==='comparison')comparison(host,metrics,limit,dir);
else if(kind==='scatter')scatter(host,metrics);
else if(kind==='metric_cards')cards(host,metrics);
else if(kind==='map')map(host,k);
});
})();
"""

def render(spec, brand="Action Network", mode="simple", logo_uri=None):
    spec = normalize(spec)
    if brand not in BRANDS:
        raise ValueError(f"Unknown brand '{brand}'.")
    if mode not in ("simple", "detailed"):
        raise ValueError("Mode must be 'simple' or 'detailed'.")
    theme = BRANDS[brand]
    css = CSS
    for key in ("primary", "bright", "dark", "navy", "navy2", "soft"):
        css = css.replace("__" + key.upper() + "__", theme[key])
    title = e(spec["title"])
    summary = e(spec.get("subtitle") or spec.get("summary") or "")
    header_stats = spec.get("hero_stats") or []
    header = f'<header class="hero" id="top"><div class="wrap hero-inner"><div class="hero-top">{logo_html(brand,theme,logo_uri)}<span class="research-mark">Data & Research / {e(spec.get("date", ""))}</span></div><span class="eyebrow">{e(spec.get("kicker", "Original Research"))}</span><h1>{title}</h1>{f"<p class=\"dek\">{summary}</p>" if summary else ""}{f"<p class=\"byline\">{e(spec.get('byline', brand + ' Research'))}</p>" if spec.get('byline') else ""}'
    if header_stats:
        header += '<div class="hero-stats">' + ''.join(f'<div class="hero-stat"><strong>{e(x.get("value", ""))}</strong><small>{e(x.get("label", ""))}</small></div>' for x in header_stats[:4]) + '</div>'
    header += '</div></header>'
    intro = ''.join(f'<p>{e(x)}</p>' for x in spec.get("intro", []))
    intro_section = f'<section class="section" id="overview"><div class="wrap"><div class="section-heading"><span class="eyebrow">Study Overview</span><h2>{e(spec.get("overview_heading", "What the Data Reveals"))}</h2></div><div class="intro">{intro or e(spec.get("summary", ""))}</div></div></section>' if (intro or spec.get("summary")) else ""
    finding_section = f'<section class="section alt" id="findings"><div class="wrap"><div class="section-heading"><span class="eyebrow">Key Takeaways</span><h2>{e(spec.get("findings_heading", "The Biggest Findings"))}</h2><p>{e(spec.get("findings_dek", "The standout results from the analysis."))}</p></div>{findings_html(spec, compact=(mode == "simple"))}</div></section>' if spec.get("key_findings") else ""
    content = []
    if mode == "simple":
        s = spec.get("simple", {})
        c = {"type": "ranking", "title": s.get("widget_title", "Explore the Complete Ranking"), "description": s.get("widget_description", ""), "metric": spec["primary_metric"], "limit": s.get("top_n", 10), "direction": s.get("direction", "desc")}
        content.append(widget_html("ranking", spec, c, 1))
        close = s.get("closing") or ""
        if close:
            content.append(f'<section class="section alt"><div class="wrap"><div class="editorial-callout"><p>{e(close)}</p></div></div></section>')
    else:
        for i, s in enumerate(spec["detailed"].get("sections", []), 1):
            if s.get("type") in WIDGET_TYPES:
                content.append(widget_html(s["type"], spec, s, i))
        if spec["detailed"].get("closing"):
            content.append(f'<section class="section alt"><div class="wrap"><div class="editorial-callout"><p>{e(spec["detailed"]["closing"])}</p></div></div></section>')
    # section outer wrapper is common and separate from .section wrappers in widget_html
    body_widgets = ''.join(re.sub(r'(<section class="section" id="w\d+">)(.*?)(</section>)',r'\1<div class="wrap">\2</div>\3',s,flags=re.S) for s in content)
    method = f'<section class="section alt" id="methodology"><div class="wrap"><div class="section-heading"><span class="eyebrow">Research Notes</span><h2>Methodology & Sources</h2><p>How the analysis was conducted and where the data came from.</p></div>{method_html(spec)}<a class="backtop" href="#top">↑ Back to top</a></div></section>'
    navlinks = []
    if intro_section: navlinks.append(("overview", "Overview"))
    if finding_section: navlinks.append(("findings", "Key Findings"))
    if mode == "simple": navlinks.append(("w1", "Explore Rankings"))
    else:
        for i, s in enumerate(spec["detailed"].get("sections", []),1):
            if s.get("type") in WIDGET_TYPES: navlinks.append((f"w{i}",str(s.get("nav_title") or s.get("title") or s.get("type")).strip()[:32]))
    navlinks.append(("methodology", "Methodology"))
    nav = '<nav class="nav" aria-label="Page sections"><div class="wrap nav-inner">' + ''.join(f'<a href="#{e(key)}">{e(label)}</a>' for key,label in navlinks) + '</div></nav>'
    footer = f'<footer class="footer"><div class="wrap"><strong>{e(brand)}</strong><span>{e(spec.get("footer_note", "Original data-led research"))} · {"Quick Read" if mode == "simple" else "Deep Dive"}</span></div></footer>'
    use_map = mode=="detailed" and any(x.get("type")=="map" for x in spec["detailed"].get("sections", []))
    mapdeps = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzX6DQgTO9gtum2fzhniQ/9JE=" crossorigin=""><script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>' if use_map else ""
    # For map scripts use DOMContentLoaded to ensure deferred Leaflet finishes first.
    boot = f'document.addEventListener("DOMContentLoaded",()=>{{{JS}}});' if use_map else JS
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>{title} | {e(brand)}</title><meta name="description" content="{e(spec.get("summary") or spec.get("subtitle") or spec["title"])}">{mapdeps}<style>{css}</style></head><body>{header}{nav}<main>{intro_section}{finding_section}{body_widgets}{method}</main>{footer}<script id="lp-data" type="application/json">{json_for_script(spec)}</script><script>{boot}</script></body></html>'''
