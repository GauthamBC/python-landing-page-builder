"""Landing Page Studio v7.17 - Build / Widgets / Outputs.

Drop-in replacement for the existing repository's app.py.
Works with the original landing_engine.py and Streamlit >=1.56 (auto-height iframe).

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


# Preview gallery displays actual working mini-widgets, not static SVG thumbnails.
# True contiguous-US and neighbouring country outlines come from Natural Earth;
# numerical scores are explicitly fictional samples, never source research.
_GALLERY_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{--primary:__PRIMARY__;--secondary:__SECONDARY__;--pale:__PALE__;--ink:#f5f8fb;--muted:#9db0be;--panel:#101c26;--line:#2a3b46;--bg:#080f16}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--ink);font-size:14px}button,input{font:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--primary);outline-offset:3px}
header{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:9px 0 17px;border-bottom:1px solid var(--line);margin-bottom:17px;flex-wrap:wrap}.eyebrow{color:var(--primary);font-size:10px;letter-spacing:.19em;font-weight:900;text-transform:uppercase}.headbrand{font-size:14px;font-weight:850;letter-spacing:.01em}.headbrand span{color:var(--primary)}.small{font-size:12px;color:var(--muted);line-height:1.6}.replay{border:1px solid #4a5963;background:#16242e;color:#e3f1f4;padding:9px 12px;border-radius:7px;font-size:12px;font-weight:700;transition:.2s}.replay:hover{border-color:var(--primary);color:var(--primary)}
.gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:17px;padding-bottom:25px}.widget{background:linear-gradient(155deg,#14232e,#0e1923 90%);border:1px solid var(--line);border-radius:14px;overflow:hidden;min-width:0;box-shadow:0 10px 24px #0002;transition:border-color .2s,transform .2s}.widget:hover{border-color:color-mix(in srgb,var(--primary) 55%,var(--line))}.widget.feature{grid-column:1/-1}.widget-head{padding:18px 20px 14px;display:flex;gap:8px;align-items:flex-start;justify-content:space-between}.widget-title{font-size:17px;letter-spacing:-.02em;font-weight:850}.widget-description{font-size:12px;color:var(--muted);line-height:1.55;margin-top:5px}.tag{display:inline-flex;align-items:center;gap:5px;border:1px solid color-mix(in srgb,var(--primary) 35%,var(--line));background:color-mix(in srgb,var(--primary) 10%,transparent);color:var(--pale);padding:7px 9px;border-radius:6px;font:700 11px/1.1 ui-monospace,monospace;white-space:nowrap}.widget-body{padding:2px 18px 18px;min-height:237px}.widget.feature .widget-body{padding:0 18px 18px;min-height:0}
.map-stage{background:radial-gradient(ellipse at 44% 49%,#233a40 0%,#122a34 52%,#0b1622 100%);border:1px solid #33464f;border-radius:11px;position:relative;overflow:hidden;min-height:370px}.map-stage:before{content:"";position:absolute;inset:0;background:linear-gradient(#ffffff09 1px,transparent 1px),linear-gradient(90deg,#ffffff08 1px,transparent 1px);background-size:42px 42px;pointer-events:none;z-index:0}.map-layout{display:grid;grid-template-columns:minmax(0,1fr) 240px;gap:0;align-items:stretch}.map-svg{display:block;width:100%;height:367px;position:relative;z-index:1}.country{stroke:#5d7981;stroke-width:1.2;fill:#263d46}.country.us{fill:#34525a;stroke:#8ba6a8;stroke-width:1.4;transition:fill .3s}.country.na{fill:#213841;opacity:.75}.gridline{stroke:#7fa2a9;stroke-width:1;stroke-dasharray:2 7;opacity:.14}.map-pin{cursor:pointer;transition:opacity .25s,filter .2s}.map-pin .ring{fill:#07161c;stroke:var(--primary);stroke-width:2.3}.map-pin .core{fill:var(--primary)}.map-pin text{font:800 12px system-ui;fill:#051516;pointer-events:none}.map-pin:focus-visible .ring,.map-pin.selected .ring,.map-pin:hover .ring{stroke:#fff;stroke-width:3}.map-pin.selected .ring,.map-pin:hover .ring{filter:drop-shadow(0 0 5px var(--primary))}.dimmed .map-pin:not(.selected){opacity:.30}.map-pin:not(.selected){opacity:.83}.map-note{position:absolute;left:15px;bottom:14px;z-index:3;background:#0a1623c7;color:#bcd0d1;padding:7px 9px;border:1px solid #40545e;border-radius:6px;font-size:10px;letter-spacing:.04em}.map-watermark{position:absolute;left:16px;top:16px;z-index:3;color:#bdd1d5;font-size:10px;font-weight:800;letter-spacing:.17em}.geo-panel{border-left:1px solid #38525b;background:#0a1822b8;padding:18px 15px;position:relative;z-index:2}.geo-big{font-size:30px;font-weight:850;letter-spacing:-.05em;color:var(--primary);line-height:1.2}.geo-city{font-weight:850;font-size:16px}.geo-detail{color:#9db0be;font-size:11px;line-height:1.65;margin-top:5px}.geo-ranks{margin-top:18px;display:grid;gap:6px}.geo-rank{border:1px solid transparent;background:#192b36;color:#cadbe4;border-radius:5px;padding:8px 9px;display:flex;justify-content:space-between;gap:6px;font-size:12px;text-align:left;width:100%}.geo-rank:hover,.geo-rank.active{border-color:var(--primary);background:#203b3d}.geo-rank strong{color:var(--primary)}
.mini-tools{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap}.search{width:100%;color:#e8f2f5;padding:9px 10px;background:#0a141e;border:1px solid #41525d;border-radius:6px;outline:none}.search:focus{border-color:var(--primary)}table{width:100%;border-collapse:collapse;font-size:12px}th{padding:10px 8px;color:#c8d7df;text-align:left;letter-spacing:.03em;font-size:11px;background:#192a36;user-select:none;cursor:pointer}th:hover{color:var(--primary)}td{padding:11px 8px;color:#dde8ee;border-bottom:1px solid #31404b}tr:hover td{background:#26383f}.rank-id{color:var(--primary);font-weight:900}.tab-foot{font-size:11px;color:#8399a7;margin-top:10px}.bar-row{display:grid;grid-template-columns:67px minmax(0,1fr) 40px;gap:9px;align-items:center;margin:14px 0}.bar-name{font-size:12px;color:#cfdee4;font-weight:700}.bar-track{border-radius:3px;background:#263945;height:18px;overflow:hidden}.bar-fill{height:100%;background:linear-gradient(90deg,var(--primary),color-mix(in srgb,var(--primary) 60%,white));width:0;border-radius:3px;transition:width 1.0s cubic-bezier(.12,.65,.2,1);transition-delay:var(--delay)}.animated .bar-fill{width:var(--value)}.bar-amt{text-align:right;font-size:12px;font-weight:850;color:var(--pale)}.chart-axis{display:flex;justify-content:space-between;color:#8395a2;font-size:10px;margin-top:8px}.metric-split{display:flex;gap:12px}.measure{flex:1;min-width:0;border:1px solid #35434d;background:#192b36;border-radius:9px;padding:16px 12px;text-align:left;cursor:pointer}.measure:hover,.measure.selected{border-color:var(--primary);background:#233c40}.measure .m-label{font-size:12px;color:#9fb4c3}.measure .m-number{font-size:37px;font-weight:850;color:var(--primary);line-height:1.4}.measure:nth-child(2) .m-number{color:#e3edf1}.measure .m-bar{height:7px;border-radius:7px;background:#31434f;overflow:hidden}.measure .m-bar span{display:block;background:var(--primary);height:100%;width:var(--value);transition:width 1s}.measure:nth-child(2) .m-bar span{background:#91adba}.measure .m-note{font-size:10px;color:#9eb2c0;margin-top:10px}.compare-summary{color:#cbd8dc;border-left:3px solid var(--primary);padding:9px 12px;background:#0d1c25;font-size:12px;margin-top:12px}
.scatter-svg{width:100%;height:217px;overflow:visible}.scatter-axis{stroke:#8fa6ae;stroke-width:1}.scatter-grid{stroke:#546977;stroke-width:1;opacity:.32}.scatter-dot{fill:var(--primary);stroke:#e6fafa;stroke-width:1.8;opacity:.88;cursor:pointer;transform-box:fill-box;transform-origin:center;transition:transform .2s,opacity .2s}.scatter-dot:hover{transform:scale(1.45);opacity:1}.scatter-trend{fill:none;stroke:#93a7b5;stroke-dasharray:6 6;stroke-width:2}.scatter-label{fill:#a2b2bf;font:11px system-ui}.tooltip{font-size:11px;color:var(--primary);margin-top:6px;min-height:21px}.scatter-svg .plotgroup{animation:scatter-appear .7s backwards;animation-delay:var(--delay)}@keyframes scatter-appear{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.heat-grid{display:grid;grid-template-columns:69px repeat(5,1fr);gap:6px;align-items:center;margin-top:7px}.heat-label{color:#aebdc9;font-size:11px;text-align:center}.heat-row{font-size:11px;color:#bccbd2}.heat{height:32px;border:1px solid #ffffff12;border-radius:4px;cursor:crosshair;transition:transform .15s,filter .2s,opacity .5s;opacity:0;background:color-mix(in srgb,var(--primary) var(--intensity),#16262f)}.animated .heat{opacity:1;transition-delay:var(--delay)}.heat:hover{transform:scale(1.07);filter:brightness(1.6);outline:2px solid #e5f9f6}.stat-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.stat{border:1px solid #34444f;border-radius:8px;background:#192b36;padding:15px 10px}.stat .number{font-weight:900;font-size:clamp(21px,2.7vw,33px);color:var(--primary);letter-spacing:-.04em}.stat .stat-name{color:#9eb1bd;font-size:11px;margin-top:5px}.stat-note{font-size:11px;margin-top:19px;line-height:1.6;color:#adbfc8}.callout{background:linear-gradient(100deg,color-mix(in srgb,var(--primary) 11%,#13242e),#14232e);padding:21px;border-left:4px solid var(--primary);border-radius:5px}.callout h4{font-size:21px;line-height:1.25;margin:0 0 12px}.callout p{line-height:1.7;color:#c2d1d8;font-size:13px;margin:0}.demo-sample{display:inline-block;font-size:10px;padding:3px 6px;border:1px solid #546975;border-radius:3px;color:#a9c0c9;margin-top:10px}.widget.reveal{opacity:.93;transform:translateY(9px);transition:opacity .55s ease,transform .55s ease}.widget.reveal.shown{opacity:1;transform:none}
@media(max-width:950px){.map-layout{grid-template-columns:1fr}.map-stage{min-height:unset}.geo-panel{border-left:0;border-top:1px solid #38525b;display:grid;grid-template-columns:1fr 1fr;gap:5px 12px}.geo-ranks{grid-column:1/-1;display:flex;flex-wrap:wrap}.geo-rank{width:auto}.map-svg{height:auto;max-height:330px}}
@media(max-width:670px){.gallery{grid-template-columns:1fr;gap:13px}.widget.feature{grid-column:1}.widget-head{padding:16px 15px 12px;flex-wrap:wrap}.widget-body,.widget.feature .widget-body{padding:0 12px 15px}.map-svg{height:260px}.geo-panel{grid-template-columns:1fr}.geo-ranks{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.stat-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.map-watermark{font-size:9px}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.widget.reveal{opacity:1;transform:none}.bar-fill{width:var(--value)}.heat{opacity:1}}

/* v7.5 — accurate vector state geometry, floating data card, meaningful finite motion. */
.widget.feature .widget-body{padding:0 14px 16px}
.atlas-stage{isolation:isolate;position:relative;min-height:630px;border:1px solid #27434b;overflow:hidden;border-radius:7px;background:radial-gradient(ellipse at 58% 50%,#123b37 0%,#071922 55%,#08131e 100%)}
.atlas-stars{position:absolute;inset:0;opacity:.45;pointer-events:none;background-image:radial-gradient(circle at 19% 22%,#b9e7cb 1px,transparent 1.9px),radial-gradient(circle at 68% 38%,#97bdc7 1px,transparent 1.8px),radial-gradient(circle at 80% 72%,#88b4af .9px,transparent 1.6px);background-size:170px 165px,230px 195px,100px 150px}
.atlas-heading{position:absolute;top:22px;left:24px;right:24px;z-index:4;display:flex;gap:6px;flex-direction:column;pointer-events:none}.atlas-heading strong{font-weight:900;color:#f3fbf8;font-size:clamp(18px,3vw,34px);letter-spacing:-.04em;line-height:1.1}.atlas-heading small{font-size:12px;color:#a5bfc5}
.atlas-gradient{position:absolute;z-index:4;left:24px;right:24px;top:120px;display:flex;align-items:center;gap:13px;pointer-events:none;font-size:10px;font-weight:900;letter-spacing:.08em;color:#bdcfd1}.gradient-track{height:7px;flex:1;max-width:650px;background:linear-gradient(90deg,#12373b,var(--primary));position:relative;overflow:hidden}.gradient-sweep{position:absolute;top:0;bottom:0;width:32%;left:-35%;background:linear-gradient(90deg,transparent,#ffffff80,transparent)}.widget.animated .gradient-sweep{animation:sweep 1.8s .45s ease-out both}@keyframes sweep{to{left:130%}}
.state-atlas{position:relative;z-index:1;display:block;width:100%;height:clamp(560px,56vw,730px);max-height:730px;overflow:visible;margin-top:30px}
.us-state{stroke:color-mix(in srgb,var(--primary) 55%,#547778);stroke-width:.95;cursor:pointer;fill:color-mix(in srgb,var(--primary) var(--score),#10333c);fill-opacity:.82;transition:fill .18s,stroke .2s,filter .2s,fill-opacity .2s;outline:none}.us-state:hover,.us-state.chosen,.us-state:focus-visible{fill:var(--primary);fill-opacity:.98;stroke:#d8fff3;stroke-width:2;filter:drop-shadow(0 0 6px var(--primary))}
.widget:not(.animated) .us-state{fill-opacity:.08}.widget.animated .us-state{animation:state-appear .7s backwards;animation-delay:calc(var(--order)*43ms)}@keyframes state-appear{from{fill-opacity:.05;stroke-opacity:.2}to{fill-opacity:.82;stroke-opacity:1}}
.state-name{font-family:system-ui, sans-serif;text-anchor:middle;dominant-baseline:middle;font-size:11px;letter-spacing:.12em;font-weight:900;fill:#d7ede3;opacity:.9;pointer-events:none;text-shadow:0 1px 3px #06141c}.map-halo{opacity:.7;transition:cx .35s ease,cy .35s ease}.widget.animated #mapBeacon{animation:beacon 1.25s .6s ease both}@keyframes beacon{from{opacity:0}to{opacity:1}}
.map-flyout{position:absolute;top:175px;left:27%;z-index:3;width:min(340px,42%);background:#07151ff2;border:1px solid #3b6261;border-left:6px solid var(--primary);box-shadow:0 24px 75px #0008;backdrop-filter:blur(11px);padding:19px 20px;transition:border-color .2s;pointer-events:none}
.widget.animated .map-flyout{animation:flyout-in .75s .65s both}@keyframes flyout-in{from{opacity:0;transform:translateY(17px)}to{opacity:1;transform:none}}
.flyout-top{display:flex;align-items:center;justify-content:space-between;gap:7px}.flyout-top .eyebrow{font-size:9px}.flyout-rank{color:#021a16;background:var(--primary);padding:7px 9px;font-size:11px;font-weight:900}.map-flyout h3{color:white;font-size:clamp(18px,2.5vw,26px);margin:13px 0;padding-bottom:13px;border-bottom:1px solid #24444d}.flyout-main{display:flex;align-items:center;gap:16px}.flyout-main>strong{color:var(--primary);font-size:clamp(35px,5vw,57px);font-weight:950;letter-spacing:-.065em}.flyout-main b{color:#b4c2c8;font-size:10px;letter-spacing:.11em;display:block}.flyout-main small{display:block;font-size:11px;color:#a3b8c0;margin-top:5px}.flyout-grid{display:grid;grid-template-columns:repeat(2,1fr);margin:17px -20px 14px;border-top:1px solid #24444d;border-bottom:1px solid #24444d}.flyout-grid>div{padding:12px 15px;border-right:1px solid #24444d;border-bottom:1px solid #24444d}.flyout-grid strong{color:white;display:block;font-size:22px;line-height:1.2}.flyout-grid small{display:block;color:#94a8b4;font-size:9px;margin-top:4px}.map-flyout p{margin:0;font-size:11px;line-height:1.55;color:#bdd1d2}
.atlas-foot{position:absolute;bottom:12px;left:24px;right:24px;display:flex;justify-content:space-between;gap:10px;z-index:4;flex-wrap:wrap;pointer-events:none;font-size:10px;font-weight:650;color:#b3ced0}.atlas-foot i{width:7px;height:7px;display:inline-block;background:var(--primary);border-radius:50%;margin-right:6px}
/* All examples animate after first entering view and replay on demand. */
.widget:not(.animated) .bar-row{opacity:0;transform:translateY(12px)}.widget.animated .bar-row{opacity:1;transform:none;transition:opacity .45s,transform .45s;transition-delay:var(--delay,100ms)}
.widget:not(.animated) .measure .m-bar span{width:0}.widget.animated .measure .m-bar span{width:var(--value);transition:width 1.2s .2s cubic-bezier(.2,.8,.1,1)}
.widget:not(.animated) .plotgroup{opacity:0;transform:translateY(17px)}.widget.animated .plotgroup{animation:scatter-pop-v75 .75s backwards;animation-delay:var(--delay)}@keyframes scatter-pop-v75{from{opacity:0;transform:translateY(14px) scale(.65)}to{opacity:1;transform:none}}
.widget:not(.animated) .scatter-trend{stroke-dasharray:600;stroke-dashoffset:600}.widget.animated .scatter-trend{animation:trend-draw 1.5s .3s ease forwards}@keyframes trend-draw{from{stroke-dasharray:600;stroke-dashoffset:600}to{stroke-dasharray:6 6;stroke-dashoffset:0}}
.widget:not(.animated) .heat{opacity:0;transform:scale(.86)}.widget.animated .heat{opacity:1;transform:none;transition:opacity .45s,transform .45s;transition-delay:var(--delay)}.widget.animated .heat:hover{transform:scale(1.08)}
.widget:not(.animated) tbody tr{opacity:0;transform:translateY(7px)}.widget.animated tbody tr{animation:tab-in .45s backwards;animation-delay:calc(var(--ri)*85ms)}@keyframes tab-in{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.widget:not(.animated) .stat{opacity:0;transform:translateY(11px)}.widget.animated .stat{animation:tab-in .6s backwards;animation-delay:calc(var(--ci)*110ms)}
.widget:not(.animated) .callout{opacity:0;transform:translateX(-17px)}.widget.animated .callout{animation:tab-in .7s backwards}
@media(max-width:840px){.atlas-stage{min-height:540px}.state-atlas{height:570px}.map-flyout{top:170px;left:24%;width:320px}.atlas-foot{bottom:8px;font-size:9px}}
@media(max-width:600px){.atlas-stage{min-height:550px}.atlas-heading{left:12px;top:13px}.atlas-gradient{top:96px;left:12px;right:12px;gap:6px;font-size:8px}.state-atlas{height:390px;margin-top:40px}.map-flyout{position:relative;top:auto;left:auto;width:auto;max-width:100%;margin:-53px 12px 38px;padding:14px;border-left-width:4px}.map-flyout h3{margin:5px 0}.flyout-grid{margin:6px -14px}.flyout-grid>div{padding:8px}.flyout-main>strong{font-size:39px}.atlas-foot{position:relative;left:auto;right:auto;bottom:auto;padding:0 12px 9px}.state-name{font-size:13px}}
@media(prefers-reduced-motion:reduce){.widget *,.widget *:before,.widget *:after{animation:none!important;transition:none!important}.widget .us-state{fill-opacity:.82!important}.widget .bar-fill,.widget .measure .m-bar span{width:var(--value)!important}.widget .heat,.widget .stat,.widget .callout,.widget tbody tr{opacity:1!important;transform:none!important}.widget .scatter-trend{stroke-dasharray:6 6!important;stroke-dashoffset:0!important}}

/* v7.6: map header and legend occupy their own rows, clear of the state map. */
:root{--map-border:color-mix(in srgb,var(--primary) 34%,#35404d);--map-surface:color-mix(in srgb,var(--primary) 10%,#091521);--map-core:color-mix(in srgb,var(--primary) 16%,#07121e);--map-quiet:color-mix(in srgb,var(--primary) 3%,#080e17)}
.widget{background:linear-gradient(145deg,color-mix(in srgb,var(--primary) 6%,#15202d),#0e1924 88%);border-color:color-mix(in srgb,var(--primary) 12%,#344452)}
.widget.reveal{opacity:0;transform:translateY(26px);transition:opacity .65s ease,transform .65s cubic-bezier(.17,.67,.2,1)}
.widget.reveal.shown{opacity:1;transform:translateY(0)}
.atlas-stage{min-height:0;background:radial-gradient(ellipse at 50% 52%,var(--map-core),var(--map-quiet) 74%,#080f19 100%);border-color:var(--map-border);padding-top:1px;transition:background .3s,border-color .3s}
.atlas-stars{background-image:radial-gradient(circle at 19% 22%,color-mix(in srgb,var(--primary) 45%,#b3bac4) 1px,transparent 1.9px),radial-gradient(circle at 68% 38%,color-mix(in srgb,var(--primary) 20%,#97bdc7) 1px,transparent 1.8px),radial-gradient(circle at 80% 72%,color-mix(in srgb,var(--primary) 22%,#88b4af) .9px,transparent 1.6px)}
.atlas-heading{position:relative;top:auto;left:auto;right:auto;z-index:4;padding:21px 24px 0;min-height:99px;pointer-events:none}
.atlas-gradient{position:relative;top:auto;left:auto;right:auto;margin:9px 24px 3px;display:grid;grid-template-columns:max-content minmax(45px,1fr) max-content;gap:13px;align-items:center;z-index:4;pointer-events:none;font-size:10px}
.atlas-gradient span{white-space:nowrap}
.gradient-track{width:100%;max-width:none;background:linear-gradient(90deg,color-mix(in srgb,var(--primary) 7%,#091522),var(--primary));border:1px solid color-mix(in srgb,var(--primary) 17%,transparent)}
.state-atlas{height:auto;max-height:none;aspect-ratio:1180/700;margin-top:0;overflow:visible}
.us-state{fill:color-mix(in srgb,var(--primary) var(--score),var(--map-core));stroke:color-mix(in srgb,var(--primary) 50%,#657688)}
.state-name{fill:color-mix(in srgb,var(--primary) 12%,#e6edf1)}
.us-state:hover,.us-state.chosen,.us-state:focus-visible{stroke:#f7fbff}
.map-flyout{top:clamp(178px,24%,290px);left:29%;background:color-mix(in srgb,var(--primary) 5%,#08131f);border-color:var(--map-border);border-left-color:var(--primary);visibility:hidden;opacity:0;transform:translateY(10px);transition:opacity .19s ease,transform .19s ease,visibility .19s;pointer-events:none}
.map-flyout.is-visible{visibility:visible;opacity:1;transform:translateY(0)}
.widget.animated .map-flyout{animation:none}
.map-halo,#mapBeacon{opacity:0;transition:opacity .2s ease,cx .2s ease,cy .2s ease}
.atlas-stage.is-inspecting .map-halo{opacity:.74}
.atlas-stage.is-inspecting #mapBeacon{opacity:1}
.widget.animated #mapBeacon{animation:none}
.flyout-rank{color:#07111a}
.flyout-grid,.map-flyout h3{border-color:var(--map-border)}
.flyout-grid>div{border-color:var(--map-border)}
.measure,.stat{background:color-mix(in srgb,var(--primary) 9%,#192531);border-color:var(--map-border)}
.measure:hover,.measure.selected{background:color-mix(in srgb,var(--primary) 16%,#15212f)}
.measure:nth-child(2) .m-bar span{background:var(--pale)}
.measure:nth-child(2) .m-number{color:var(--pale)}
.compare-summary{background:color-mix(in srgb,var(--primary) 7%,#0c1722)}
.callout{background:linear-gradient(110deg,color-mix(in srgb,var(--primary) 14%,#13222b),color-mix(in srgb,var(--secondary) 38%,#172635))}
.heat{background:color-mix(in srgb,var(--primary) var(--intensity),color-mix(in srgb,var(--primary) 4%,#14232d))}
.scatter-svg .plotgroup{animation:none}
.widget:not(.animated) .plotgroup{opacity:0;transform:translateY(14px)}
.widget.animated .plotgroup{animation:scatter-pop-v75 .75s backwards;animation-delay:var(--delay)}
.widget:not(.animated) .scatter-trend{stroke-dasharray:600;stroke-dashoffset:600}
.widget:not(.animated) .heat{opacity:0;transform:scale(.86)}
.widget.animated .heat{opacity:1;transform:none;transition:opacity .45s,transform .45s;transition-delay:var(--delay)}
.widget:not(.animated) .measure{opacity:.45;transform:translateY(8px)}
.widget.animated .measure{opacity:1;transform:none;transition:opacity .48s ease,transform .48s ease;transition-delay:.1s}
.widget:not(.animated) .compare-summary{opacity:0;transform:translateX(-10px)}
.widget.animated .compare-summary{opacity:1;transform:none;transition:opacity .5s ease,transform .5s ease;transition-delay:.3s}
.widget:not(.animated) .bar-fill{width:0}
.widget.animated .bar-fill{width:var(--value)}
.widget:not(.animated) .gradient-sweep{animation:none}
@media(max-width:840px){.atlas-heading{padding:15px 16px 0;min-height:90px}.atlas-gradient{margin:8px 16px 0}.state-atlas{height:auto}.map-flyout{top:28%;left:18%;width:min(325px,57%)} }
@media(max-width:600px){.atlas-heading{min-height:90px;padding:13px 12px 0}.atlas-heading strong{font-size:clamp(19px,5vw,28px)}.atlas-gradient{margin:6px 12px 2px;gap:5px;font-size:8px;grid-template-columns:max-content minmax(20px,1fr) max-content}.atlas-gradient span{font-size:7px;letter-spacing:0}.state-atlas{height:auto;min-height:0;margin-top:0;aspect-ratio:1180/700}.map-flyout{display:none;position:relative;top:auto;left:auto;width:auto;max-width:none;margin:0 12px 14px;padding:14px;transform:none}.map-flyout.is-visible{display:block;transform:none}.atlas-foot{position:relative;left:auto;right:auto;bottom:auto;padding:8px 12px 12px}.atlas-foot span{font-size:9px}.map-flyout h3{margin:5px 0}.flyout-grid{margin:6px -14px}.flyout-grid>div{padding:8px}}
@media(prefers-reduced-motion:reduce){.widget.reveal,.widget .bar-row,.widget .bar-fill,.widget .plotgroup,.widget .measure,.widget .compare-summary,.widget .stat,.widget .callout,.widget tbody tr,.widget .heat{opacity:1!important;transform:none!important;animation:none!important;transition:none!important}.widget .map-flyout:not(.is-visible){visibility:hidden!important;opacity:0!important}.widget .map-flyout.is-visible{visibility:visible!important;opacity:1!important}.widget .map-halo,.widget #mapBeacon{opacity:0!important}.widget .atlas-stage.is-inspecting .map-halo,.widget .atlas-stage.is-inspecting #mapBeacon{opacity:1!important}}

/* v7.8 — complete publication identity, not just changed green/red/blue bars. */
:root{
  --brand-background:__BRAND_BACKGROUND__;--brand-panel:__BRAND_PANEL__;
  --brand-elevated:__BRAND_ELEVATED__;--brand-ocean:__BRAND_OCEAN__;
  --brand-horizon:__BRAND_HORIZON__;--brand-line:__BRAND_LINE__;
  --brand-highlight:__BRAND_HIGHLIGHT__;
}
body{background:var(--brand-background);background-image:radial-gradient(700px 460px at 80% 0%,color-mix(in srgb,var(--primary) 4%,transparent),transparent)}
header{border-bottom-color:var(--brand-line)}
.widget{background:linear-gradient(140deg,color-mix(in srgb,var(--primary) 4%,var(--brand-panel)),var(--brand-panel) 95%);border-color:var(--brand-line)}
.widget:hover{border-color:color-mix(in srgb,var(--primary) 45%,var(--brand-line))}
.widget .tag{background:color-mix(in srgb,var(--primary) 9%,var(--brand-panel));border-color:color-mix(in srgb,var(--primary) 48%,var(--brand-line));color:var(--pale)}
.atlas-stage{background:radial-gradient(ellipse at 51% 55%,var(--brand-horizon),var(--brand-ocean) 63%,var(--brand-background) 100%);border-color:color-mix(in srgb,var(--primary) 26%,var(--brand-line))}
.atlas-stars{background-image:radial-gradient(circle at 19% 22%,color-mix(in srgb,var(--primary) 30%,#a0bac6) 1px,transparent 1.9px),radial-gradient(circle at 68% 38%,color-mix(in srgb,var(--primary) 20%,#8795a9) 1px,transparent 1.8px),radial-gradient(circle at 80% 72%,color-mix(in srgb,var(--primary) 22%,#7d8995) .9px,transparent 1.6px)}
.us-state{fill:color-mix(in srgb,var(--primary) var(--score),var(--brand-highlight));stroke:color-mix(in srgb,var(--primary) 36%,#909ba8)}
.gradient-track{background:linear-gradient(90deg,var(--brand-elevated),var(--primary));border-color:var(--brand-line)}
.map-flyout{background:color-mix(in srgb,var(--primary) 4%,var(--brand-ocean));border-color:var(--brand-line);border-left-color:var(--primary);box-shadow:0 22px 56px #0009}
.flyout-grid,.flyout-grid>div,.map-flyout h3{border-color:var(--brand-line)}
.measure,.stat,.geo-rank{background:var(--brand-elevated);border-color:var(--brand-line)}
.measure:hover,.measure.selected,.geo-rank:hover,.geo-rank.active{background:color-mix(in srgb,var(--primary) 15%,var(--brand-elevated));border-color:var(--primary)}
.compare-summary{background:color-mix(in srgb,var(--primary) 7%,var(--brand-panel))}
.callout{background:linear-gradient(110deg,color-mix(in srgb,var(--primary) 13%,var(--brand-panel)),color-mix(in srgb,var(--secondary) 30%,var(--brand-elevated)))}
.heat{background:color-mix(in srgb,var(--primary) var(--intensity),var(--brand-elevated))}
th{background:var(--brand-elevated);border-bottom:1px solid var(--brand-line)}
td{border-bottom-color:var(--brand-line)}tr:hover td{background:color-mix(in srgb,var(--primary) 12%,var(--brand-panel))}
.search{background:var(--brand-ocean);border-color:var(--brand-line)}
.bar-track,.measure .m-bar{background:color-mix(in srgb,var(--primary) 13%,var(--brand-line))}
.replay{background:var(--brand-panel);border-color:var(--brand-line)}
.scatter-grid{stroke:color-mix(in srgb,var(--primary) 20%,var(--brand-line))}
.scatter-trend{stroke:color-mix(in srgb,var(--primary) 27%,#a2b4c1)}
.atlas-heading{background:linear-gradient(to bottom,color-mix(in srgb,var(--brand-ocean) 60%,transparent),transparent)}
/* Never render a selected state or card on initial load. Hover/focus/tap reveals it. */
.map-flyout:not(.is-visible){visibility:hidden;opacity:0;pointer-events:none}
/* Keep legend above the map in its own non-overlapping row. */
.atlas-gradient{position:relative;top:auto;left:auto;right:auto;z-index:5;margin:10px 24px 12px}
@media(max-width:600px){.atlas-gradient{margin:9px 12px 5px}}


/* v7.8 — follow-the-state responsive tooltip, no fixed map overlay */
.map-flyout{
  position:absolute!important;top:0!important;left:0!important;
  width:min(296px,calc(100% - 20px))!important;max-width:296px;
  margin:0!important;padding:12px 14px!important;
  border-left-width:4px;z-index:14;
  transform:translate3d(var(--tooltip-x,0px),var(--tooltip-y,0px),0)!important;
  transform-origin:top left;will-change:transform,opacity;
  transition:opacity .13s ease,visibility .13s ease;
  box-shadow:0 14px 34px rgba(0,0,0,.44);
  pointer-events:none!important;
}
.map-flyout.is-visible{transform:translate3d(var(--tooltip-x,0px),var(--tooltip-y,0px),0)!important;}
.map-flyout .flyout-top .eyebrow{font-size:9px;letter-spacing:.11em}
.map-flyout .flyout-rank{font-size:10px;padding:5px 8px}
.map-flyout h3{font-size:21px;margin:7px 0 8px;padding:0 0 8px;line-height:1.15}
.map-flyout .flyout-main{gap:10px}
.map-flyout .flyout-main>strong{font-size:clamp(29px,3.2vw,40px);line-height:1.05}
.map-flyout .flyout-main b{font-size:9px;letter-spacing:.06em}
.map-flyout .flyout-main small{font-size:10px;margin-top:2px}
.map-flyout .flyout-grid{margin:10px -14px 8px}
.map-flyout .flyout-grid>div{padding:7px 12px}
.map-flyout .flyout-grid strong{font-size:18px}
.map-flyout .flyout-grid small{font-size:8px;margin-top:2px}
.map-flyout p{font-size:10px;line-height:1.35}
@media(max-width:700px){
 .map-flyout{position:absolute!important;display:block!important;width:min(230px,calc(100% - 16px))!important;max-width:230px!important;padding:9px 10px!important;margin:0!important;}
 .map-flyout h3{font-size:17px;margin:5px 0;padding-bottom:6px}
 .map-flyout .flyout-top .eyebrow{font-size:8px}
 .map-flyout .flyout-rank{font-size:9px;padding:4px 6px}
 .map-flyout .flyout-main>strong{font-size:30px}
 .map-flyout .flyout-main b{font-size:8px}
 .map-flyout .flyout-main small{font-size:9px}
 .map-flyout .flyout-grid{margin:7px -10px 0}
 .map-flyout .flyout-grid>div{padding:5px 8px}
 .map-flyout .flyout-grid strong{font-size:16px}
 .map-flyout .flyout-grid small{font-size:7px}
 .map-flyout p{display:none}
}
@media(max-width:390px){
 .map-flyout{width:min(194px,calc(100% - 12px))!important;padding:7px 8px!important;}
 .map-flyout h3{font-size:15px}
 .map-flyout .flyout-main>strong{font-size:27px}
 .map-flyout .flyout-grid{margin:6px -8px 0}
 .map-flyout .flyout-grid strong{font-size:15px}
 .map-flyout .flyout-grid small{font-size:7px}
}
@media(prefers-reduced-motion:reduce){
 .map-flyout,.map-flyout.is-visible{transition:none!important;animation:none!important;}
}


/* v7.9 — extra brand-adaptive demonstrations; all data are fictional. */
.preview-count{display:inline-flex;align-items:center;gap:8px;margin-top:6px;font-weight:800;color:var(--pale)}
.count-pill{border:1px solid color-mix(in srgb,var(--primary) 70%,var(--brand-line));border-radius:50px;padding:5px 11px;background:color-mix(in srgb,var(--primary) 13%,var(--brand-panel));color:var(--primary);font-size:13px}

/* v7.16: clear identity on the left and live widget count on the right. */
.gallery-toolbar{display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:nowrap;padding:16px 0 20px}
.gallery-identity{display:flex;flex-direction:column;gap:12px;min-width:0}
.gallery-identity .headbrand{line-height:1.3}
.live-preview-label{color:var(--muted)!important;font-weight:600}
.gallery-tally{display:flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:6px;flex-shrink:0;text-align:right}
.gallery-tally .count-pill{font-size:17px;line-height:1.3;padding:8px 15px}
.gallery-tally .small{font-size:11px;white-space:nowrap}
@media(max-width:540px){
 .gallery-toolbar{flex-wrap:wrap;gap:12px;padding-top:12px}
 .gallery-identity{gap:8px}
 .gallery-tally{margin-left:0;flex-direction:row;justify-content:space-between;align-items:center;gap:10px;width:100%;text-align:left}
 .gallery-tally .count-pill{font-size:14px;padding:6px 10px;white-space:nowrap}
 .gallery-tally .small{font-size:10px;white-space:normal;text-align:right}
}
.status-chip{white-space:nowrap;font-size:10px;color:#becdd5;border:1px solid var(--brand-line);border-radius:5px;padding:5px 7px;background:var(--brand-elevated)}
.preview-card-label{margin-top:7px;font:700 10px/1.4 ui-monospace,monospace;color:var(--pale);white-space:normal}
.demo-feature{font-size:11px;color:var(--muted);line-height:1.5;margin:4px 0 0}
.choice-tools{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:11px}
.choice-tools button{border:1px solid var(--brand-line);background:var(--brand-elevated);color:var(--ink);border-radius:6px;padding:6px 10px;font-size:11px;font-weight:750}
.choice-tools button.active,.choice-tools button:hover{background:var(--primary);color:var(--brand-ocean);border-color:var(--primary)}
.donut-flex{display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;min-height:187px}
.donut-wheel{width:min(182px,51%);overflow:visible;flex-shrink:0;transform:rotate(-90deg)}
.donut-arc{fill:none;stroke-width:22;stroke-linecap:butt;stroke-dasharray:0 258;stroke-dashoffset:var(--offset);transition:opacity .23s,stroke-width .25s;cursor:pointer}
.animated .donut-arc{animation:donutReveal .85s cubic-bezier(.13,.7,.25,1) forwards;animation-delay:var(--dly)}
.donut-arc:hover,.donut-arc.active{stroke-width:26}
.donut-wheel.pie .donut-arc{stroke-width:82}
.donut-wheel.pie .donut-arc:hover,.donut-wheel.pie .donut-arc.active{stroke-width:82}
.donut-wheel.pie .donut-center,.donut-wheel.pie .donut-total{opacity:0}
@keyframes donutReveal{from{stroke-dasharray:0 258}to{stroke-dasharray:var(--arc) 258}}
.donut-center{fill:var(--brand-ocean);transition:opacity .25s}
.donut-total{fill:var(--ink);font-size:24px;font-weight:850;text-anchor:middle;transform:rotate(90deg);transform-origin:75px 75px}
.legend-list{display:grid;gap:5px;min-width:120px;flex:1;max-width:200px}
.legend-row{border:1px solid transparent;border-radius:6px;background:transparent;color:var(--ink);font-size:11px;display:flex;gap:9px;align-items:center;text-align:left;padding:7px;transition:background .2s,border-color .2s}
.legend-row strong{margin-left:auto}
.legend-row.active,.legend-row:hover{background:var(--brand-elevated);border-color:var(--brand-line)}
.legend-swatch{width:11px;height:11px;border-radius:3px;flex-shrink:0}
.hybrid-table,.heat-table{table-layout:auto}
.hybrid-table td,.heat-table td{padding:9px 7px}
.hybrid-table th,.heat-table th{font-size:10px;padding:8px 7px}
.hybrid-table td:first-child,.heat-table td:first-child{font-weight:800;color:var(--ink)}
.hybrid-meter{height:13px;background:var(--brand-line);border-radius:3px;min-width:64px;overflow:hidden}
.hybrid-meter>i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--primary),color-mix(in srgb,var(--primary) 60%,white));transition:width .9s ease;transition-delay:var(--dly)}
.animated .hybrid-meter>i{width:var(--w)}
.hybrid-score{font-weight:850;color:var(--pale)}
.heat-value{display:block;text-align:center;padding:7px 4px;border-radius:4px;background:color-mix(in srgb,var(--primary) var(--shade),var(--brand-elevated));font-weight:800;color:var(--ink);transition:background .25s,transform .25s,opacity .45s;opacity:.3}
.animated .heat-value{opacity:1;animation:heatPop .45s ease both;animation-delay:var(--dly)}
.heat-value:hover{transform:scale(1.07);outline:1px solid var(--primary)}
@keyframes heatPop{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:scale(1)}}
.trend-svg,.slope-svg{width:100%;max-height:230px;display:block;overflow:visible}
.mini-axis{font-size:10px;fill:var(--muted)}
.mini-grid{stroke:var(--brand-line);stroke-width:1;fill:none}
.trend-series{fill:none;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:var(--path-len);stroke-dashoffset:var(--path-len);transition:stroke-dashoffset 1.35s ease;transition-delay:var(--dly)}
.animated .trend-series{stroke-dashoffset:0}
.trend-point{cursor:pointer;fill:var(--brand-panel);stroke-width:3;opacity:0;transform-origin:center;transition:opacity .3s;transition-delay:.65s}
.animated .trend-point{opacity:1}
.trend-point:hover,.trend-point:focus{stroke-width:5}
.mini-tooltip{min-height:20px;color:var(--pale);font-size:11px;margin-top:8px}
.stack-grid{display:grid;gap:16px;padding:8px 0 0}
.stack-row{display:grid;grid-template-columns:65px minmax(0,1fr) 35px;align-items:center;gap:9px;font-size:11px}
.stack-track{height:24px;display:flex;overflow:hidden;border-radius:4px;background:var(--brand-line)}
.stack-piece{display:block;flex:0 0 0;width:0;transition:flex-basis .95s cubic-bezier(.2,.8,.2,1);transition-delay:var(--dly);position:relative;cursor:pointer}
.animated .stack-piece{flex-basis:var(--w)}
.stack-piece:hover{filter:brightness(1.2)}
.stack-value{color:var(--pale);font-weight:800;text-align:right}
.stack-legend{display:flex;gap:13px;flex-wrap:wrap;margin-top:15px;color:var(--muted);font-size:10px}
.stack-legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.slope-line{fill:none;stroke-width:3.5;stroke-linecap:round;stroke-dasharray:var(--path-len);stroke-dashoffset:var(--path-len);transition:stroke-dashoffset 1.25s ease,opacity .25s;transition-delay:var(--dly);cursor:pointer}
.animated .slope-line{stroke-dashoffset:0}
.slope-svg:has(.slope-line:hover) .slope-line:not(:hover){opacity:.15}
.slope-dot{stroke:var(--brand-ocean);stroke-width:2;pointer-events:none}
.slope-lbl{font-size:11px;fill:var(--ink);font-weight:700;pointer-events:none}
@media(max-width:550px){.donut-wheel{max-width:158px}.widget-head{flex-wrap:wrap}.status-chip{font-size:9px}.donut-flex{gap:3px}.legend-list{min-width:108px}}
@media(prefers-reduced-motion:reduce){.donut-arc{stroke-dasharray:var(--arc) 258!important;animation:none!important}.trend-series,.slope-line{stroke-dashoffset:0!important}.hybrid-meter>i{width:var(--w)!important}.stack-piece{flex-basis:var(--w)!important}.heat-value,.trend-point{opacity:1!important;animation:none!important}}


/* v7.10 interactive infographic library: 12 new brand-adaptive demonstrations */
.library-summary{display:flex;gap:9px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:11px;line-height:1.5}
.library-summary strong{color:var(--pale)}
.infographic-label{font-size:10px;letter-spacing:.095em;text-transform:uppercase;font-weight:900;color:var(--primary);margin-bottom:10px}
.infographic-foot{font-size:11px;line-height:1.5;color:var(--muted);min-height:17px;margin-top:11px}
.infographic-canvas{border:1px solid var(--brand-line);border-radius:9px;background:color-mix(in srgb,var(--brand-ocean) 86%,var(--brand-panel));padding:12px;min-height:190px;overflow:hidden;position:relative}
.infographic-canvas svg{width:100%;display:block;height:auto;overflow:visible}
.preview-only{color:var(--pale);font:700 10px ui-monospace,monospace;white-space:nowrap;border:1px solid var(--brand-line);padding:5px 7px;border-radius:5px}
.world-canvas{padding:12px 14px 7px;min-height:360px;position:relative;border-radius:10px;background:radial-gradient(circle at 49% 37%,var(--brand-horizon),var(--brand-ocean) 76%);border:1px solid var(--brand-line)}
.world-map{width:100%;display:block;max-height:415px;outline:none}
.world-country{fill:color-mix(in srgb,var(--primary) 14%,var(--brand-ocean));stroke:color-mix(in srgb,var(--primary) 43%,var(--brand-horizon));stroke-width:.35;stroke-linejoin:round;transition:fill .35s,filter .25s,stroke .25s;cursor:crosshair}
.world-country.target{fill:color-mix(in srgb,var(--primary) calc(var(--strength,60)*1%),var(--brand-horizon));cursor:pointer}
.world-country.target:hover,.world-country.target.active{fill:var(--pale);stroke:var(--pale);stroke-width:1.3;filter:drop-shadow(0 0 4px var(--primary))}
.world-map:focus-visible{outline:2px solid var(--primary)}
.world-foot{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;padding:9px 0 0;font-size:11px;color:var(--muted)}
.world-tooltip{position:absolute;pointer-events:none;background:var(--brand-elevated);border:1px solid var(--primary);border-left:4px solid var(--primary);padding:12px 15px;max-width:215px;min-width:155px;color:var(--ink);font-size:12px;box-shadow:0 16px 32px #0008;z-index:2;display:none}
.world-tooltip strong{display:block;font-size:16px;margin:4px 0}.world-tooltip em{font-size:25px;color:var(--primary);font-style:normal;font-weight:900}.world-tooltip small{display:block;color:var(--muted);font-size:10px}
.world-tooltip.visible{display:block}
.route-stage{width:100%;min-height:268px;position:relative;background:radial-gradient(ellipse at 40% 40%,var(--brand-horizon),var(--brand-ocean));border:1px solid var(--brand-line);border-radius:9px;padding:8px 12px 12px}
.route-stage svg{width:100%;height:240px;display:block}
.route-grid{stroke:var(--brand-line);stroke-width:1}.route-path{fill:none;stroke:var(--primary);stroke-width:2.6;stroke-dasharray:6 7;stroke-dashoffset:300;opacity:0;transition:stroke-dashoffset 1.3s ease,opacity .3s,stroke-width .2s;transition-delay:var(--dly);cursor:pointer}
.animated .route-path{stroke-dashoffset:0;opacity:.75}.route-path:hover,.route-path.active{stroke-width:5;opacity:1;filter:drop-shadow(0 0 4px var(--primary))}
.route-dot{fill:var(--primary);stroke:var(--ink);stroke-width:2}.route-text{font-size:12px;fill:var(--ink);font-weight:800}.route-muted{font-size:10px;fill:var(--muted)}
.spark-card{border:1px solid var(--brand-line);border-radius:10px;background:var(--brand-elevated);padding:15px}
.spark-meta{font-size:11px;color:var(--muted)}.spark-top{display:flex;gap:12px;align-items:center;justify-content:space-between}.spark-number{font-weight:900;letter-spacing:-.04em;font-size:clamp(27px,3vw,40px);color:var(--ink)}.spark-delta{font-size:12px;color:var(--primary);font-weight:800}
.spark-svg{height:115px!important;width:100%}.spark-line{fill:none;stroke:var(--primary);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:var(--len);stroke-dashoffset:var(--len);transition:stroke-dashoffset 1.5s ease}.animated .spark-line{stroke-dashoffset:0}
.spark-area{fill:url(#sparkFade)}.spark-cursor{stroke:var(--pale);stroke-dasharray:3 4;opacity:0}.spark-point{fill:var(--primary);stroke:var(--ink);stroke-width:2;opacity:0}.spark-svg:focus-within .spark-point,.spark-svg:hover .spark-point{opacity:1}
.range-chart{position:relative;min-height:182px;display:grid;align-content:center;gap:11px;padding:16px}.range-heading{text-align:center;font-weight:850;font-size:17px;color:var(--ink)}.range-sub{text-align:center;font-size:12px;color:var(--muted)}.range-rail{height:19px;border-radius:3px;background:linear-gradient(90deg,var(--brand-elevated) 0%,var(--primary) 50%,var(--pale) 100%);position:relative;overflow:visible;margin:14px 10px 0}.range-marker{position:absolute;top:50%;left:var(--x);transform:translate(-50%,-50%);width:24px;height:24px;border-radius:50%;border:3px solid white;background:var(--primary);box-shadow:0 0 0 5px color-mix(in srgb,var(--primary) 22%,transparent);transition:left .65s}.range-marker:after{content:attr(data-label);position:absolute;bottom:32px;left:50%;transform:translateX(-50%);white-space:nowrap;color:var(--pale);font-size:11px;font-weight:800}.range-ends{display:flex;justify-content:space-between;font-size:11px;color:var(--muted)}
.range-actions{display:flex;justify-content:center;gap:8px;flex-wrap:wrap}.range-actions button{border:1px solid var(--brand-line);background:var(--brand-elevated);color:var(--ink);padding:6px 10px;border-radius:5px;font-size:11px;font-weight:700}.range-actions button.active{border-color:var(--primary);color:var(--primary)}
.waterfall-graph{height:200px;display:grid;grid-template-columns:repeat(5,1fr);align-items:end;gap:10px;border-bottom:1px solid var(--brand-line);padding:5px 5px 0}.wf-col{height:100%;display:flex;flex-direction:column;justify-content:end;align-items:center;position:relative}.wf-float{position:absolute;bottom:var(--bottom);height:var(--height);width:70%;min-height:4px;background:var(--primary);transform:scaleY(0);transform-origin:bottom;transition:transform .9s ease;transition-delay:var(--dly);border-radius:2px 2px 0 0}.wf-float.negative{background:var(--pale)}.wf-col:last-child .wf-float{background:color-mix(in srgb,var(--primary) 65%,white)}.animated .wf-float{transform:scaleY(1)}.wf-value{position:absolute;bottom:calc(var(--bottom) + var(--height) + 5px);color:var(--ink);font-size:11px;font-weight:800}.wf-label{font-size:9px;position:absolute;bottom:-25px;text-align:center;color:var(--muted);width:100%}
.bubble-canvas{height:195px;position:relative}.bubble{position:absolute;display:grid;place-items:center;border:1px solid var(--pale);border-radius:50%;background:color-mix(in srgb,var(--primary) 58%,var(--brand-ocean));color:var(--ink);font-weight:850;font-size:12px;cursor:pointer;transform:translate(-50%,-50%) scale(0);transition:transform .8s cubic-bezier(.2,.9,.3,1),background .25s;transition-delay:var(--dly)}.animated .bubble{transform:translate(-50%,-50%) scale(1)}.bubble:hover,.bubble.active{background:var(--primary);filter:drop-shadow(0 0 8px color-mix(in srgb,var(--primary) 55%,transparent))}
.radar-svg{max-height:225px}.radar-grid{stroke:var(--brand-line);stroke-width:1;fill:none}.radar-axis{stroke:var(--brand-line)}.radar-area{fill:color-mix(in srgb,var(--primary) 25%,transparent);stroke:var(--primary);stroke-width:3;transform:scale(0);transform-origin:175px 114px;transition:transform 1s cubic-bezier(.25,.9,.2,1)}.animated .radar-area{transform:scale(1)}.radar-axis-text{font-size:10px;fill:var(--muted);text-anchor:middle}.radar-dot{fill:var(--pale);stroke:var(--brand-ocean);stroke-width:2;cursor:pointer}
.funnel-wrap{display:grid;gap:7px;justify-items:center;padding:7px 0 0}.funnel-level{width:var(--width);min-height:38px;display:flex;align-items:center;justify-content:space-between;padding:8px 13px;border:1px solid var(--primary);background:color-mix(in srgb,var(--primary) var(--shade),var(--brand-horizon));clip-path:polygon(3% 0,97% 0,91% 100%,9% 100%);color:var(--ink);font-size:11px;font-weight:800;transform:scaleX(.1);opacity:0;transition:transform .8s ease,opacity .3s;transition-delay:var(--dly);cursor:pointer}.animated .funnel-level{transform:scaleX(1);opacity:1}.funnel-level:hover{filter:brightness(1.25)}
.waffle-wrap{display:grid;grid-template-columns:repeat(10,1fr);gap:5px;width:min(100%,340px);margin:auto;padding:6px}.waffle-cell{width:100%;aspect-ratio:1;background:var(--brand-line);border-radius:3px;transform:scale(0);opacity:0;transition:transform .32s ease,opacity .35s;transition-delay:var(--dly)}.animated .waffle-cell{transform:scale(1);opacity:1}.waffle-cell.filled{background:var(--primary)}.waffle-cell.alternate{background:var(--pale)}
.waffle-caption{text-align:center;font-size:24px;font-weight:900;color:var(--primary)}.waffle-caption span{font-size:12px;color:var(--muted);font-weight:600}
.timeline-wrap{border-left:2px solid var(--brand-line);margin:5px 0 0 16px;display:grid;gap:6px}.timeline-event{margin-left:20px;position:relative;border:1px solid var(--brand-line);padding:11px 14px;border-radius:6px;background:var(--brand-elevated);opacity:0;transform:translateY(14px);transition:opacity .6s,transform .6s;transition-delay:var(--dly);cursor:pointer}.animated .timeline-event{opacity:1;transform:none}.timeline-event:before{content:'';position:absolute;left:-28px;top:16px;width:11px;height:11px;background:var(--primary);border-radius:50%;box-shadow:0 0 0 4px var(--brand-ocean)}.timeline-event strong{font-size:12px;color:var(--ink)}.timeline-event small{display:block;color:var(--muted);margin-top:3px;font-size:11px}.timeline-event:hover{border-color:var(--primary)}
.diverge-bars{display:grid;gap:15px;padding:12px 2px}.diverge-row{display:grid;grid-template-columns:62px 1fr;gap:10px;align-items:center;color:var(--ink);font-size:11px}.diverge-track{display:grid;grid-template-columns:1fr 1fr;height:23px;gap:1px;border-left:0;position:relative}.diverge-track:after{content:'';position:absolute;left:50%;top:-4px;bottom:-4px;border-left:1px solid var(--muted)}.diverge-neg,.diverge-pos{height:19px;align-self:center;max-width:100%;background:var(--pale);transition:width .9s ease;transition-delay:var(--dly)}.diverge-neg{justify-self:end;width:0;border-radius:3px 0 0 3px}.diverge-pos{justify-self:start;width:0;background:var(--primary);border-radius:0 3px 3px 0}.animated .diverge-neg,.animated .diverge-pos{width:var(--width)}
.lolli-wrap{display:grid;gap:18px;padding:8px 0}.lolli-row{display:grid;grid-template-columns:64px 1fr 38px;gap:8px;align-items:center;font-size:11px}.lolli-track{height:2px;background:var(--brand-line);position:relative}.lolli-track:before{content:'';position:absolute;left:0;top:0;height:2px;width:0;background:var(--primary);transition:width 1.1s;transition-delay:var(--dly)}.animated .lolli-track:before{width:var(--width)}.lolli-dot{width:17px;height:17px;background:var(--primary);border:3px solid var(--pale);border-radius:50%;position:absolute;left:0;top:50%;transform:translate(-50%,-50%);transition:left 1.1s;transition-delay:var(--dly)}.animated .lolli-dot{left:var(--width)}
@media(max-width:650px){.world-canvas{min-height:215px}.world-tooltip{padding:8px;min-width:120px;max-width:175px}.world-tooltip strong{font-size:13px}.world-tooltip em{font-size:18px}.route-stage svg{height:auto}.range-heading{font-size:14px}.waterfall-graph{gap:4px}.wf-value{font-size:9px}}
@media(prefers-reduced-motion:reduce){.route-path{stroke-dashoffset:0!important;opacity:1!important}.spark-line{stroke-dashoffset:0!important}.wf-float{transform:none!important}.bubble{transform:translate(-50%,-50%) scale(1)!important}.radar-area{transform:scale(1)!important}.funnel-level,.timeline-event,.waffle-cell{opacity:1!important;transform:none!important}.diverge-neg,.diverge-pos,.lolli-track:before{width:var(--width)!important}.lolli-dot{left:var(--width)!important}}

/* finishing touches after visual review */
.radar-svg{width:min(100%,430px);height:auto;max-height:250px;display:block;margin:0 auto}
.funnel-level{clip-path:none;border-radius:5px;justify-content:space-between;padding:9px 16px}


/* v7.11: single geographical widget, three views, segment controls */
.geo-map-switcher{display:flex;align-items:center;flex-wrap:wrap;gap:8px 9px;padding:14px 12px 15px;margin-bottom:4px;border-bottom:1px solid var(--brand-line)}
.geo-map-btn{border:1px solid var(--brand-line);border-radius:7px;color:var(--ink);background:var(--brand-elevated);font-weight:800;font-size:13px;line-height:1.2;padding:11px 15px;cursor:pointer;transition:color .16s,border-color .16s,background .16s,transform .16s}
.geo-map-btn:hover{border-color:var(--primary);transform:translateY(-1px)}
.geo-map-btn.active{border-color:var(--primary);background:var(--primary);color:#06151a}
.geo-map-btn:focus-visible{outline:3px solid var(--pale);outline-offset:2px}
.geo-map-mode-description{margin-left:auto;color:var(--muted);font-size:11px;font-weight:700}
.geo-mode-panel[hidden]{display:none!important}
.geo-mode-panel.is-entering{animation:geoModeEnter .6s both}
@keyframes geoModeEnter{0%{opacity:0;transform:translateY(9px)}100%{opacity:1;transform:none}}
.geo-world-panel{min-height:360px;overflow:hidden}
.geo-world-panel .world-canvas{min-height:400px}
.geo-world-panel .world-map{max-height:500px}
.geo-world-panel .world-map{overflow:hidden!important;clip-path:inset(0)}
.world-map-clip{width:100%;overflow:hidden;position:relative}.world-map-clip svg{display:block;overflow:hidden!important}
.geo-world-panel[data-map-mode="na"] .world-canvas{min-height:440px}
.geo-world-panel[data-map-mode="na"] .world-map{height:min(47vw,445px);max-height:none}
.geo-world-panel[data-map-mode="na"] .world-country.target:not([data-country="Canada"]):not([data-country="United States of America"]){opacity:.32;pointer-events:none}
.geo-world-panel .world-tooltip{z-index:6}
.world-country{opacity:.6}
.geo-world-panel.is-entering .world-country.target{animation:geoCountryReveal .7s ease-out backwards;animation-delay:calc(var(--reveal-index,0)*100ms)}
@keyframes geoCountryReveal{from{opacity:.1;filter:brightness(.55)}to{opacity:1;filter:brightness(1)}}
@media(max-width:720px){.geo-map-mode-description{width:100%;margin-left:0}.geo-map-btn{flex:1;min-width:0;padding:10px 5px;font-size:12px}.geo-world-panel .world-canvas{min-height:260px}.geo-world-panel[data-map-mode="na"] .world-canvas{min-height:310px}.geo-world-panel[data-map-mode="na"] .world-map{height:300px}.geo-world-panel .world-tooltip{max-width:175px}}
@media(max-width:390px){.geo-map-btn{font-size:11px;padding:10px 4px}.geo-world-panel[data-map-mode="na"] .world-map{height:250px}}
@media(prefers-reduced-motion:reduce){.geo-mode-panel.is-entering,.geo-world-panel.is-entering .world-country.target{animation:none!important}.geo-map-btn{transition:none!important}}

/* v7.14: Canada-only is a focused view of the SAME 13 verified Canadian geometries.
   US and inset features are hidden when the country focus is active. */
.geo-na-panel[data-map-mode="canada"] .na-region[data-country="United States"],
.geo-na-panel[data-map-mode="canada"] .na-map-label[data-country="United States"]{display:none!important}
.geo-na-panel[data-map-mode="canada"] .na-map{max-height:620px}
@media(max-width:640px){.geo-map-switcher{gap:6px}.geo-map-btn{font-size:11px;padding:10px 7px;flex:1 1 calc(50% - 6px)}}

/* v7.12: separate US + Canada admin-level geographic panel */
.geo-na-panel .na-stage{position:relative;padding:17px 18px 12px;background:radial-gradient(circle at 52% 36%,var(--brand-horizon),var(--brand-ocean) 78%);border:1px solid var(--brand-line);border-radius:9px;overflow:hidden}
.na-topline{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-bottom:12px;border-bottom:1px solid var(--brand-line)}
.na-topline strong{color:var(--ink);font-size:clamp(13px,2vw,18px);font-weight:900}
.na-topline span{color:var(--muted);font-size:11px}
.na-scale{display:flex;align-items:center;gap:10px;padding:11px 0 8px;font-size:10px;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.05em}
.na-scale b{flex:1;height:7px;border-radius:5px;background:linear-gradient(90deg,color-mix(in srgb,var(--primary) 20%,var(--brand-ocean)),var(--primary),var(--pale));display:block}
.na-map{width:100%;height:auto;display:block;min-height:230px;max-height:630px;overflow:hidden}
.na-region{stroke:color-mix(in srgb,var(--pale) 52%,var(--brand-ocean));stroke-width:.85;stroke-linejoin:round;fill-rule:evenodd;fill:color-mix(in srgb,var(--primary) var(--shade),var(--brand-horizon));cursor:pointer;transition:fill .2s,stroke .2s,filter .2s;outline:none}
.na-region:hover,.na-region.active,.na-region:focus-visible{fill:var(--pale);stroke:#fff;stroke-width:1.8;filter:drop-shadow(0 0 4px var(--primary))}
.na-inset-label{font-size:13px;letter-spacing:.09em;font-weight:900;fill:var(--pale)}
.na-map-label{fill:var(--ink);font:800 11px Arial,sans-serif;text-anchor:middle;paint-order:stroke;stroke:color-mix(in srgb,var(--brand-ocean) 66%,transparent);stroke-width:2px;pointer-events:none;opacity:.88}
.na-tip{position:absolute;z-index:20;max-width:min(260px,82vw);width:max-content;min-width:165px;background:var(--brand-elevated);color:var(--ink);border:1px solid var(--primary);border-left:4px solid var(--primary);padding:11px 13px;box-shadow:0 16px 35px #0007;pointer-events:none;display:none;border-radius:4px}
.na-tip.visible{display:block}.na-tip b{font-size:16px;display:block;line-height:1.25}.na-tip small{font-size:11px;color:var(--muted);display:block;margin:4px 0}.na-tip strong{font-size:25px;color:var(--primary);font-weight:900}
.na-foot{display:flex;gap:10px;justify-content:space-between;flex-wrap:wrap;color:var(--muted);font-size:10px;padding:9px 0 3px}
.na-loading{padding:25px 5px;color:var(--muted);font-size:13px;text-align:center}
.geo-na-panel.is-entering .na-region{animation:naRegionIntro .5s ease-out backwards;animation-delay:calc(var(--i,0)*13ms)}
@keyframes naRegionIntro{from{opacity:0;filter:brightness(.45)}to{opacity:1;filter:brightness(1)}}
@media(max-width:690px){.geo-na-panel .na-stage{padding:10px 8px}.na-topline span{font-size:10px}.na-scale{font-size:8px}.na-map-label{font-size:9px}.na-tip{padding:8px 9px;min-width:125px;max-width:165px}.na-tip b{font-size:13px}.na-tip strong{font-size:19px}.na-map{min-height:160px}}
@media(prefers-reduced-motion:reduce){.geo-na-panel.is-entering .na-region{animation:none!important}}
</style></head><body>
<header class="gallery-toolbar"><div class="gallery-identity"><div class="eyebrow">Interactive widget gallery</div><div class="headbrand"><span>●</span> __BRAND__ <span class="live-preview-label">/ Live previews</span></div></div><div class="gallery-tally"><span class="count-pill" id="widgetCount">25 widgets</span><span class="small">8 engine-ready · 17 gallery concepts</span></div></header>
<div class="gallery" id="gallery">
<section class="widget feature reveal" data-widget="map">
<div class="widget-head"><div><div class="eyebrow">Geographic storytelling / interactive</div><div class="widget-title" style="font-size:clamp(20px,2.8vw,32px);margin-top:7px">Interactive maps · four geographic views</div><div class="widget-description">Switch between the US, Canada, both countries and the world. Hover, focus or tap a region to explore illustrative data.</div></div><span class="tag">Build (must - map)</span></div>
<div class="widget-body"><div class="geo-map-switcher" role="group" aria-label="Choose a geographic map view">
  <button type="button" class="geo-map-btn active" data-geo-mode="us" aria-pressed="true">US only</button>
  <button type="button" class="geo-map-btn" data-geo-mode="canada" aria-pressed="false">Canada only</button>
  <button type="button" class="geo-map-btn" data-geo-mode="na" aria-pressed="false">US &amp; Canada</button>
  <button type="button" class="geo-map-btn" data-geo-mode="world" aria-pressed="false">World</button>
  <span id="geoMapModeDescription" class="geo-map-mode-description" aria-live="polite">State-level interactive map · 50 US states</span>
</div>
<div class="geo-mode-panel" id="usMapPanel" data-map-panel="us"><div class="atlas-stage" id="atlasStage">
<div class="atlas-stars" aria-hidden="true"></div>
<div class="atlas-heading"><span class="eyebrow">50 states · fictional example index</span><strong>Every state tells a different story.</strong><small>Dark = lower · Bright = higher</small></div>
<div class="atlas-gradient"><span>LOWER INDEX SCORE</span><div class="gradient-track"><i class="gradient-sweep"></i></div><span>HIGHER INDEX SCORE</span></div>
<svg class="state-atlas" viewBox="0 0 1180 700" role="img" aria-label="Interactive choropleth map of 50 US states, with fictional demonstration index scores. Hover over a state or focus with keyboard for details.">
<defs><radialGradient id="beam"><stop offset="0" stop-color="var(--primary)" stop-opacity=".38"/><stop offset="1" stop-color="var(--primary)" stop-opacity="0"/></radialGradient><filter id="brightGlow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<g class="state-group" id="stateGroup"><path class="us-state" id="state-AL" data-state="AL" d="M762.1,517.1L761.4,517.9L759.4,518.5L758.8,518.5L762.1,517.1ZM757.1,515.7L753.1,483.9L754.5,420.3L752.5,418L796.8,414.2L809.1,458L815.7,470L813,473L812.2,478.9L816.8,496.5L770.3,501.4L769.9,504.2L774.3,507.8L775.5,512.8L774.2,515.7L768.1,517.8L764,518.3L768.8,516.4L763.5,508.6L761.8,516.4L757.1,515.7Z" style="--order:0;--score:73%" tabindex="0" role="button" aria-label="Alabama, view demo score"/><text class="state-name" x="783.5" y="466.3" aria-hidden="true">AL</text><path class="us-state" id="state-AR" data-state="AR" d="M704.7,463L653.6,465.1L653.4,453.9L647.5,454.2L645.7,452.2L646,415.1L642.5,391.7L717.3,388.9L719.1,393L714.2,399.8L725,399L726.6,401.1L721.6,404.9L723.5,406.6L722.6,409.4L720.5,408.9L720.6,412.2L719.8,410.4L718.5,411.7L720.6,417.6L716.8,419.9L716.8,424L713.8,423.4L712.8,433.2L706.9,437.3L709,439L706.6,439.5L708.1,440.7L706.5,443.2L704.4,443.1L706.4,447L703.7,448.3L705.7,449.3L702.3,449.5L704.1,450.9L702.4,454.5L704.5,454.1L703,455.3L705.5,454.2L705.3,460.7L703.4,461.1L704.7,463Z" style="--order:1;--score:90%" tabindex="0" role="button" aria-label="Arkansas, view demo score"/><text class="state-name" x="679.3" y="427.0" aria-hidden="true">AR</text><path class="us-state" id="state-AZ" data-state="AZ" d="M350.3,479.6L289.1,443.8L292.1,439L296.5,437.7L296.5,433.9L293.4,431.9L293.9,427.3L298.5,422.9L299.8,414.9L308,409.4L302,395.1L304.4,388.9L305.1,369.5L311.1,369.4L314.8,372.7L317.2,369.6L320.3,352.8L402.6,366.4L386.2,485L350.3,479.6Z" style="--order:2;--score:57%" tabindex="0" role="button" aria-label="Arizona, view demo score"/><text class="state-name" x="347.5" y="418.9" aria-hidden="true">AZ</text><path class="us-state" id="state-CA" data-state="CA" d="M189.6,308.9L192.6,311.6L190.2,300.9L193.3,299.3L190.1,297.6L187.7,303.4L183.7,297.8L181,297.5L183.3,292.2L175.5,275.5L179.2,256.4L174,245.3L174.4,241.4L181.6,232.9L185.8,222.8L185.1,215L187.1,210.8L250.1,228.7L234.2,290.1L302.6,392.4L304.5,404.6L308,409.4L302.2,412.1L298.5,422.9L294.4,425.2L293.4,431.9L297.1,435.1L295.2,439.3L249.4,434.4L247.1,417.4L238,405.4L233.2,404.5L232.8,398.2L222.9,394.2L217.3,386L202.3,381.3L200.1,377.8L203.2,366.4L200,364.1L200.8,359.4L195.5,352.9L189.1,337L189.4,331.1L193.8,327.1L186.1,316.6L188.5,303.7L189.6,308.9ZM204.5,391.6L207.3,391.6L208,393.8L205.2,394.1L204.5,391.6ZM200.2,389.7L202,389.4L202.8,390.7L200.2,389.7ZM227.5,422.6L227,418.5L229.6,423.7L227.5,422.6ZM233,413.4L230.3,412.8L228.7,409.1L232.3,411.5L233,413.4ZM209.4,391.4L213.9,393.8L216,393.9L211.6,394.4L209.4,391.4Z" style="--order:3;--score:74%" tabindex="0" role="button" aria-label="California, view demo score"/><text class="state-name" x="225.5" y="325.0" aria-hidden="true">CA</text><path class="us-state" id="state-CO" data-state="CO" d="M518.7,378.3L402.6,366.4L414.1,282.5L523.9,293.5L518.7,378.3Z" style="--order:4;--score:91%" tabindex="0" role="button" aria-label="Colorado, view demo score"/><text class="state-name" x="464.4" y="331.6" aria-hidden="true">CO</text><path class="us-state" id="state-CT" data-state="CT" d="M970.1,250.3L965.8,233.2L991.4,227.3L994.7,239.7L994.2,241.9L978.3,246.8L968.5,255.7L966.9,253.6L970.1,250.3Z" style="--order:5;--score:58%" tabindex="0" role="button" aria-label="Connecticut, view demo score"/><path class="us-state" id="state-DE" data-state="DE" d="M948.5,315.1L941.4,289.3L944.8,286L947,286.4L944.6,290.8L945.7,294L952.7,304.3L956.6,306L958.9,313L948.5,315.1Z" style="--order:6;--score:75%" tabindex="0" role="button" aria-label="Delaware, view demo score"/><path class="us-state" id="state-FL" data-state="FL" d="M848.8,520.7L836.6,513.1L830.7,514.8L829.5,516.9L831.3,518.2L813.8,525.3L812.1,519.5L796.4,512.7L786.7,512.6L773.1,516.2L775.5,512.7L774.3,507.8L769.9,504.2L770.3,501.4L816.8,496.5L819.9,502.3L867.8,499L869.3,503.3L871.6,502.5L871.8,492.9L881.4,494.1L887.9,513.6L903.9,535.5L905.7,545.5L920,570.6L921.8,591.9L919.1,595.5L918.1,603.8L905.9,608.2L898.5,594.6L891.1,593.9L887,584.7L883.6,582.3L882.2,583.2L880.2,579.3L881.9,579.4L881.6,573.5L878.6,578.8L867.1,563.2L868.9,563.2L872.8,556.1L872.2,554.8L871.2,554.2L871.4,556.6L869.8,556.3L869.4,553.8L867,553.6L869.3,557L867.1,561.6L864.3,556.7L864.2,555.2L864.5,555.7L864.9,552.6L864.2,550.2L865.9,543.4L864.2,534.7L861.4,530L856.9,531L848.8,520.7ZM825.1,522.2L824,523.3L820.9,525.4L819.3,526.1L818.4,525.4L825.1,522.2ZM900,616.9L903.2,618.3L893.7,622L900,616.9ZM881.4,583.4L884,583.6L880.9,583.6L878.7,579L881.4,583.4ZM906.4,616.8L908.2,615.9L908.8,615.2L910.2,614.5L910.3,614.8L907.3,616.9L906.4,616.8ZM916.5,609L919.5,604.1L921.7,597.2L919.2,605.8L916.1,610L914.7,611.5L912.8,613L916.5,609Z" style="--order:7;--score:42%" tabindex="0" role="button" aria-label="Florida, view demo score"/><text class="state-name" x="886.5" y="550.4" aria-hidden="true">FL</text><path class="us-state" id="state-GA" data-state="GA" d="M819.5,501.8L814.4,492.9L814.8,485.3L812.4,480.5L813,473L815.7,470L809.1,458L796.8,414.2L839.2,408.7L836.2,415.9L844.6,419.2L851.7,429.5L872.9,446.3L875.4,454L880,456.8L882.4,463.8L887.5,465.8L882.2,472.4L883.7,474.2L881.7,476.1L883.3,476.5L882.3,483.2L879.4,488.6L881.1,488.7L881.2,494L870.7,493.9L871.4,502.9L868.8,502.9L867.8,499L819.5,501.8Z" style="--order:8;--score:59%" tabindex="0" role="button" aria-label="Georgia, view demo score"/><text class="state-name" x="843.8" y="456.0" aria-hidden="true">GA</text><path class="us-state" id="state-IA" data-state="IA" d="M687,303.3L623,305.4L621.1,302.5L620.6,287L617.8,285.2L617.3,276L609.5,259.8L612.6,251.8L610.2,243.7L692,241.9L694.7,247L693.1,251L695.2,257.6L700.8,259.8L710.4,272.6L707.7,281.5L696.9,285.8L696.1,289.5L698.9,295.5L696.5,301.6L692.2,304.3L692.8,307.7L687,303.3Z" style="--order:9;--score:76%" tabindex="0" role="button" aria-label="Iowa, view demo score"/><text class="state-name" x="663.0" y="275.0" aria-hidden="true">IA</text><path class="us-state" id="state-ID" data-state="ID" d="M295.3,239.5L303.5,201.7L307,195.4L303,189.4L319.9,166.9L315.5,159.6L314.6,149.9L327.2,96.1L340.7,99L336.2,119.8L339.5,126.5L338.3,132L343.2,136.7L348.8,149.8L355,152L350,161.8L350.9,167.6L347.9,169.3L347.2,173.6L350,176.5L356,172.4L358.2,175L360.5,191.2L364.9,194L367.4,203.2L369,200.8L374.6,202.6L376.6,200.4L388.5,203L390.5,198.8L394.5,205.4L386.3,256.9L295.3,239.5Z" style="--order:10;--score:43%" tabindex="0" role="button" aria-label="Idaho, view demo score"/><text class="state-name" x="335.2" y="176.5" aria-hidden="true">ID</text><path class="us-state" id="state-IL" data-state="IL" d="M712.2,353.3L714.9,339.2L709.5,337L706.5,338.8L704.4,331.2L693.6,321.7L691,313.4L692.2,304.3L696.5,301.6L698.9,295.5L696.1,289.5L696.9,285.8L706,283L710,276.7L709.9,270.2L701.8,262.7L745.7,259.6L745.7,264.3L751.4,275.4L755.8,325.5L754.3,329.9L757.5,338.2L750.6,349.9L748.6,362L750.5,365.6L743.9,368.2L744.7,374.8L736,372.1L732.9,375.7L733.7,377.6L729.5,376.6L726.8,371.6L728.3,369.3L726.3,363.1L712.2,353.3Z" style="--order:11;--score:60%" tabindex="0" role="button" aria-label="Illinois, view demo score"/><text class="state-name" x="723.7" y="318.7" aria-hidden="true">IL</text><path class="us-state" id="state-IN" data-state="IN" d="M766,357.7L757.4,354.5L757.1,357.7L752.5,356L751.9,359.4L749.9,357.5L751,348.8L757.5,338.2L754.3,329.9L755.8,325.5L751.5,275.7L755.5,277.2L762.2,273.6L793.5,270.2L800.8,332.8L790.9,335.1L791.6,339.3L785.6,345.4L782.9,352.4L777.1,347.9L773.5,355.8L770,352.9L766,357.7Z" style="--order:12;--score:77%" tabindex="0" role="button" aria-label="Indiana, view demo score"/><text class="state-name" x="776.7" y="314.7" aria-hidden="true">IN</text><path class="us-state" id="state-KS" data-state="KS" d="M518.7,378.3L522.6,314.6L630.4,317.7L637.3,321.4L633.6,327.2L638.3,334.4L642.1,335.5L642.3,381.2L558.5,380.2L518.7,378.3Z" style="--order:0;--score:44%" tabindex="0" role="button" aria-label="Kansas, view demo score"/><text class="state-name" x="581.3" y="347.9" aria-hidden="true">KS</text><path class="us-state" id="state-KY" data-state="KY" d="M752.5,386.4L729.6,388.1L730.3,385.4L732.6,386.5L733.7,384.3L732.8,376.3L735,372.6L744.7,374.8L743.9,368.2L750.5,365.6L748.6,362L752.5,358.5L752.5,356L756.8,357.8L757.3,354.6L760.6,355L765.7,357.9L770,352.9L773.3,355.9L777.1,347.9L782.9,352.4L785.6,345.4L791.6,339.3L790.9,335.1L800.8,332.8L798.8,327.2L800.9,325.1L805.8,325.1L810.5,331.2L819.6,333.8L821.9,331.9L825.9,333.7L832.1,329.5L833.2,332.8L837.4,335L837.6,341.3L840.7,345.8L844.7,350.7L850.6,352.7L839.5,363.4L833.7,372.2L825,376.8L751.8,382.6L752.5,386.4Z" style="--order:1;--score:61%" tabindex="0" role="button" aria-label="Kentucky, view demo score"/><text class="state-name" x="807.0" y="356.6" aria-hidden="true">KY</text><path class="us-state" id="state-LA" data-state="LA" d="M695.3,531L688.7,533L692.5,535.6L686.9,537.5L670.9,533L658.8,535L657.2,533L661.2,527.2L660.2,517.2L664,506.8L658,495.2L658.1,491.3L654.1,486.8L653.6,465.1L704.1,463.6L704.2,465.9L705.3,464L704.4,469L706.4,469.5L704.8,471.8L707.2,471.2L706.1,473L707.8,474.2L705.6,474.6L709.9,476.7L708.1,480.1L705,480.6L707.9,481.6L705.2,483.3L706.8,484.3L703.8,488.8L702.2,488.2L703.7,490L699.4,492.9L701.4,493.9L699.3,495.1L700.3,498.4L698.5,497.5L699.7,500.3L697.2,500.8L699.1,505L697.8,506.2L732.1,504.2L730.3,511.5L736.9,521.2L731.4,526.3L735.7,527.8L737.8,523.3L739.9,523.6L740.1,526.6L742.8,525.2L740,528.2L742.1,529.8L735.2,530.4L738.4,532.8L735.4,532L734.6,535.3L748,541.4L745.6,545.9L743.4,543.8L740.8,547.3L742.2,543L732.2,539.8L732,536.3L729,536.8L727.8,541.5L730.4,540.9L726.5,544.5L723.4,545.6L725.4,544.4L724.6,542.5L723.4,541L720.9,543L720.1,540.9L715,546L718,545.8L714.4,546.5L712,543.7L705.6,542.2L706.5,540L708.7,542.4L708.7,540.7L701.1,536.9L699.3,532.7L695,533.6L695.3,531ZM695.9,538.3L691.9,536.3L697.9,536.4L695.9,538.3ZM748.6,530.6L750,526.6L748.8,523L750.2,526.4L748.6,530.6ZM743.5,523.6L740.4,523.5L743,521.2L743.5,523.6Z" style="--order:2;--score:78%" tabindex="0" role="button" aria-label="Louisiana, view demo score"/><text class="state-name" x="681.1" y="505.5" aria-hidden="true">LA</text><path class="us-state" id="state-MA" data-state="MA" d="M1004.5,235.4L997.7,225.8L965.7,233.2L965.7,218L995.3,211.6L1001.5,206.1L1003,209.6L1006.1,209.9L1002.5,212.9L1001.9,218.9L1006.6,219.2L1009.6,222.9L1007.9,223.4L1013.8,227.4L1019.5,224.6L1016.9,220.2L1014.5,220.2L1017,219.7L1021.4,226.9L1021.2,229.8L1020.3,227.2L1015.3,229.4L1013.8,231.6L1007.6,236.5L1011.2,232.5L1010.8,228.9L1004.5,235.4ZM1021.4,233.1L1023.3,235L1023.2,235.7L1021.1,236.4L1018.4,235.9L1021.4,233.1ZM1012.4,233.6L1015.4,235.7L1009.6,237.3L1012.4,233.6Z" style="--order:3;--score:45%" tabindex="0" role="button" aria-label="Massachusetts, view demo score"/><path class="us-state" id="state-MD" data-state="MD" d="M940.3,326L927.4,319.8L924,321.9L923.5,318.3L927.3,310.2L917.7,308.2L917.1,305L911.9,303.6L909.6,298.3L903.9,297.4L898.4,302.3L894.8,300.2L892.5,305.1L890.2,304.8L885.2,311.5L883.3,300.7L941.4,289.3L948.5,315.1L958.9,313L958.2,320.9L947.9,327.1L946.3,317.9L945.6,318.3L945.5,320.3L945.1,320.7L944,317.9L944.2,321.3L940.1,319.9L938.1,316.6L938.4,313.7L940.5,313L938.6,311.2L937.3,312.9L939,309.1L937.8,306.9L936,309.5L935.8,307.4L936.3,305.1L936.9,306.2L938.6,305.5L936.2,302.4L939.6,297.3L938.9,293.3L931.8,302.4L934.9,306L933.5,312.1L940.3,326ZM944.5,322.1L945,324.3L943.6,321.7L944.5,322.1Z" style="--order:4;--score:62%" tabindex="0" role="button" aria-label="Maryland, view demo score"/><path class="us-state" id="state-ME" data-state="ME" d="M997.1,197.1L984.2,157.6L987.9,158.3L987.6,154.1L990.2,154.3L988.2,152L992.7,142.6L990.6,136.6L992.6,131.2L991.9,125.3L998.2,106.9L1000.9,106.8L1004.3,111.2L1012.6,105L1020.3,108.9L1028.3,136.5L1034.5,137L1035.5,143.3L1038.5,145.8L1041,144.3L1046.1,150.3L1042.6,156.2L1041.7,154.1L1041,156.8L1038.7,156.9L1039.1,158.8L1035,159.4L1035.6,162.3L1033.4,164.9L1031.5,162.3L1029.4,162.7L1031.6,165.5L1030.2,166.9L1030.2,168.2L1028,164.3L1025.6,165.8L1027.2,169.1L1023.6,167.9L1022.3,168.6L1022,165.2L1019.4,167L1020.6,174.6L1018.4,178.5L1017.8,177.7L1015.7,177.9L1011.2,185.2L1008,185.3L1007.8,182.7L1005.7,185.2L1005.3,187.4L1006.7,189.5L1004.5,190.9L1002.5,201.5L997.1,197.1ZM1023.1,171.2L1023.3,174.6L1021.8,173.2L1023.1,171.2ZM1025.5,171.5L1024.4,170.1L1024.7,168.6L1026.8,169.9L1025.5,171.5Z" style="--order:5;--score:79%" tabindex="0" role="button" aria-label="Maine, view demo score"/><text class="state-name" x="1017.1" y="153.4" aria-hidden="true">ME</text><path class="us-state" id="state-MI" data-state="MI" d="M814.8,268.1L762.2,273.6L768.4,262.5L769.8,253.1L762.8,234.1L764,229.8L762.2,224.9L767.1,206.4L770.8,205.1L774.2,199.2L773.3,206.9L774.3,208.6L775.6,203.7L775.4,208.9L776.5,197.7L782.9,194.4L779.8,192L781.8,187.5L779.7,186.9L784.6,185.8L805.7,194L808.2,198.9L805.4,199.2L808.9,205.5L809.1,213.4L806.3,215.7L806.1,219.8L802,222.4L801.4,226.9L802.5,228.6L806.2,229.7L810.4,223L809.3,222.4L815.3,218.4L818.9,219.4L826.8,239.3L826.4,247.3L824.1,250.1L824.5,246.8L821.8,247.8L814.8,268.1ZM743,204.5L742.6,199L739.2,199.6L740.2,192.6L734.9,190.4L735.1,188L705,181.4L700.4,176.9L720.7,166.4L728.1,158.1L734.2,155.3L738.1,156.6L734.6,157.2L731.1,161.5L728.4,170.3L732.5,166.3L737.5,167.4L745,174.9L754.6,175.3L754.4,172.9L756.1,174.7L761.8,169.7L778.9,165.7L778.8,171.9L785.7,172.4L791.7,169.5L792.7,174.9L790.7,176.9L794,177.4L793.5,178.3L796.1,180.8L789.5,182.2L785.1,180.2L784.3,184.8L780,181.6L772.7,180.6L770.2,183.8L761.7,185.1L757.5,192.7L755.8,191.3L758,186.6L754.5,187.5L752.2,191.7L750.9,188.4L743,204.5ZM715.6,148.1L723.4,142.4L726.6,141.1L720.2,147.8L716.8,149.5L715.6,148.1ZM772.5,187.8L774,190.8L772.2,191.6L772.5,187.8ZM790.2,185.5L788.2,186.5L786.7,185L790.2,185.5ZM798.1,179.2L799.8,177.2L802.5,179.4L801.4,181.1L796.6,180.5L798.1,179.2Z" style="--order:6;--score:46%" tabindex="0" role="button" aria-label="Michigan, view demo score"/><text class="state-name" x="750.3" y="179.9" aria-hidden="true">MI</text><path class="us-state" id="state-MN" data-state="MN" d="M692,241.9L612.4,243.7L612.6,205.9L606.7,199.4L610.7,194.9L611.2,189.4L607.7,177.3L607.1,157.7L603.1,146.2L602.1,128.4L631.2,128.5L631.1,120.5L633.8,120.8L635.8,121.8L638.4,133.7L649.7,135.9L650.4,138.2L662.2,135.5L666.8,137.2L665.7,138.9L669.4,139.8L670.8,143.8L672.2,140.9L675.1,140.7L682.3,147L691.7,142.3L693.8,145.4L711.8,145.9L694.6,155.1L676,173.4L677.1,175.1L673.1,176.1L673.6,188.5L665.4,196.3L665.3,199.3L668.9,202L667,216.6L688.3,231.6L692,241.9Z" style="--order:7;--score:63%" tabindex="0" role="button" aria-label="Minnesota, view demo score"/><text class="state-name" x="641.2" y="182.1" aria-hidden="true">MN</text><path class="us-state" id="state-MO" data-state="MO" d="M717.3,388.9L642.5,391.7L642.1,335.5L638.3,334.4L633.6,327.4L637.6,323.1L636.5,320L633.3,320.4L628.8,317L622.9,305.5L687,303.3L692.2,308L691,313.4L693.6,321.6L704.4,331.2L706,338.2L707.7,339.2L709.5,337L715,339.3L711.7,352.6L726.3,363.1L729.4,376.5L734.2,377.9L732.9,386.1L730.3,385.4L728.9,389L727.1,386.8L728,393.4L725.2,393.8L727.2,395.8L725.5,398.9L714.2,399.8L719.1,393L717.3,388.9Z" style="--order:8;--score:80%" tabindex="0" role="button" aria-label="Missouri, view demo score"/><text class="state-name" x="676.7" y="351.6" aria-hidden="true">MO</text><path class="us-state" id="state-MS" data-state="MS" d="M732.1,504.2L697.8,506.2L699.1,505L697.2,500.8L699.7,500.3L698.5,497.5L700.3,498.4L699.3,495.1L701.4,493.9L699.4,492.9L703.7,490L702.2,488.2L703.8,488.8L706.8,484.3L705.2,483.3L707.9,481.6L705,480.6L708.1,480.1L709.9,476.7L705.6,474.6L707.8,474.2L706.1,473L707.2,471.2L704.7,471.6L705.5,464.2L703.4,465.3L705.5,454.2L702.4,454.5L704.1,450.9L702.3,449.3L705.6,449.5L703.7,447.5L706.3,447.1L704.4,443.1L706.5,443.2L708.1,440.7L706.6,439.5L709.1,438.9L706.8,437.4L712.8,433.3L712.2,428L714.4,427.6L712.6,426.9L712.8,425.5L714.4,426.5L714.1,423.2L716.8,424L716.6,420.8L752.6,418.3L754.5,420.3L753.1,483.9L757.1,516.1L748.9,515.5L741.1,518.3L740.1,516.9L738.3,521L736.1,521.3L730.3,511.5L732.1,504.2Z" style="--order:9;--score:47%" tabindex="0" role="button" aria-label="Mississippi, view demo score"/><text class="state-name" x="729.9" y="469.8" aria-hidden="true">MS</text><path class="us-state" id="state-MT" data-state="MT" d="M360.5,191.2L356.2,172.5L350,176.5L347.2,173.6L347.9,169.3L350.9,167.6L350,161.8L355,152L348.8,149.8L343.2,136.7L338.3,132L339.5,126.5L336.2,119.8L340.7,99L416.6,113L506.7,123.8L499.8,207.2L396.2,194.4L394.5,205.4L390.5,198.8L388.5,203L376.6,200.4L374.6,202.6L369,200.8L367.5,203.3L364.9,194L360.5,191.2Z" style="--order:10;--score:64%" tabindex="0" role="button" aria-label="Montana, view demo score"/><text class="state-name" x="429.5" y="153.0" aria-hidden="true">MT</text><path class="us-state" id="state-NC" data-state="NC" d="M839.2,408.7L818.6,411.6L818.5,406.6L822.4,405.1L824.7,399.6L838.9,392.2L844,385.3L845.7,387.4L848.6,383.6L853.9,382.7L855.4,378.6L858.7,377.4L858.4,372L954.3,355.2L963.2,369.8L953.9,356.7L951.9,357.2L957.6,364.9L954.7,361.8L955.4,363.3L950.2,361.6L952.8,364.3L949.2,364.1L950.5,365.9L946.3,364.7L949.1,366.2L944.9,369L941.9,363.7L943.3,370.6L953.5,367.4L955.6,374.4L957.1,367L960.7,373.9L955,381.6L949.2,381.8L946.9,379.3L948.8,378.9L948.6,377.9L946.1,379.4L947.7,381.8L939.6,380.7L950,384L945.7,391.3L940.8,388.7L946.5,392.1L950.9,387.8L952.4,389.7L954.9,388.6L951.5,396.2L949.5,394.4L948.9,396.4L951.8,397.1L954.1,391.8L958.1,386.7L951.7,398.2L948.9,396.5L943.7,398.1L935.2,405.2L930.7,418.5L926.7,417.7L920.7,420.2L897.9,403.8L878.9,406.6L878.8,404.2L875.6,401L874,402.6L873.6,400.4L850.6,402.5L839.2,408.7ZM958.7,385.6L965.5,380.5L963.4,370L965.9,381.6L958.7,385.6ZM961.6,369.7L959.3,367.4L960.8,367.8L961.6,369.7Z" style="--order:11;--score:81%" tabindex="0" role="button" aria-label="North Carolina, view demo score"/><text class="state-name" x="895.5" y="387.7" aria-hidden="true">NC</text><path class="us-state" id="state-ND" data-state="ND" d="M611,192.5L501.4,187.3L506.7,123.8L602.1,128.4L603.1,146.2L607.1,157.4L607.7,177.3L611,192.5Z" style="--order:12;--score:48%" tabindex="0" role="button" aria-label="North Dakota, view demo score"/><text class="state-name" x="555.5" y="158.1" aria-hidden="true">ND</text><path class="us-state" id="state-NE" data-state="NE" d="M630.4,317.7L522.6,314.6L523.9,293.5L492.5,291.2L496,249.1L581,253.8L588,259L591,256.8L599.2,257L606.9,260.5L609.6,264.6L613.3,265.4L613.9,271.9L618.3,279.8L617.8,285.2L621.3,290.3L621.1,302.5L630.4,317.7Z" style="--order:0;--score:65%" tabindex="0" role="button" aria-label="Nebraska, view demo score"/><text class="state-name" x="555.3" y="283.4" aria-hidden="true">NE</text><path class="us-state" id="state-NH" data-state="NH" d="M977.8,215.4L975.7,212.9L974.6,198.9L977.1,186.3L975.5,182.3L981.4,175.8L979.3,171L979.4,160.4L984.2,157.6L996.1,196.2L1002.1,201.8L1001.5,206.1L995.3,211.6L977.8,215.4Z" style="--order:1;--score:82%" tabindex="0" role="button" aria-label="New Hampshire, view demo score"/><path class="us-state" id="state-NJ" data-state="NJ" d="M958,302.8L958.1,297.8L954.1,298.2L946.5,293.8L945.4,290.4L956.1,276.7L946.1,267.2L947.6,263.1L945.8,260.8L950.8,251.7L964.8,256.3L961.4,268.1L966.2,268.1L967.7,282.5L960.4,300.9L958,302.8Z" style="--order:2;--score:49%" tabindex="0" role="button" aria-label="New Jersey, view demo score"/><path class="us-state" id="state-NM" data-state="NM" d="M493.9,482.3L430.6,476.7L432.1,481.1L402.3,477.6L401.1,487L386.2,485L402.6,366.4L502.7,377L493.9,482.3Z" style="--order:3;--score:66%" tabindex="0" role="button" aria-label="New Mexico, view demo score"/><text class="state-name" x="446.3" y="426.9" aria-hidden="true">NM</text><path class="us-state" id="state-NV" data-state="NV" d="M302.6,392.4L234.2,290.1L250.1,228.7L340.4,249L317.2,369.6L314.7,372.8L311.1,369.4L305,369.5L304.4,388.9L302.6,392.4Z" style="--order:4;--score:83%" tabindex="0" role="button" aria-label="Nevada, view demo score"/><text class="state-name" x="288.2" y="310.4" aria-hidden="true">NV</text><path class="us-state" id="state-NY" data-state="NY" d="M938,240.8L870.6,253.9L869.6,248.3L881.5,235.2L876.4,225.8L884.7,221.9L895.8,220.5L899.6,222.1L910.3,218.3L917.9,211.6L915.4,205.5L918.3,202.1L916.3,202.8L917.2,201.3L915.8,200.7L915.2,203.3L913.7,198.4L925.9,181.8L931.7,176.9L953.3,171.9L959,201.4L960.7,200.1L962.1,201.8L965.7,218L965.3,232.5L970.1,250.3L966.9,253.6L968.6,255.8L967.3,257.5L966.8,259.4L967.6,260L971.3,255.8L984.9,251.4L988.7,246.9L992.3,249.6L995.6,247L979.4,260L966.3,265.8L964.3,264.5L964.8,256.3L945.8,250.2L942.9,243.6L938,240.8ZM961.9,264.9L964.2,265.2L961.8,267.9L961.9,264.9Z" style="--order:5;--score:50%" tabindex="0" role="button" aria-label="New York, view demo score"/><text class="state-name" x="937.4" y="218.9" aria-hidden="true">NY</text><path class="us-state" id="state-OH" data-state="OH" d="M818.2,333.5L810.5,331.2L805.8,325.1L799.9,326.1L793.7,271.6L814.6,268.2L823.2,271.7L824.6,269.9L830.6,273.5L841.8,269.5L847.9,262.8L859,256.4L863.6,284.3L861.5,285.9L863.4,291.2L861.4,306.5L856.8,312.2L852.9,312.4L849.7,315.8L849.6,323.3L847.5,324.6L844.9,321.8L841.7,334.8L838,336L832,329.4L825.9,333.7L821.9,331.9L818.2,333.5Z" style="--order:6;--score:67%" tabindex="0" role="button" aria-label="Ohio, view demo score"/><text class="state-name" x="829.5" y="296.2" aria-hidden="true">OH</text><path class="us-state" id="state-OK" data-state="OK" d="M582.9,441.2L576.3,442.9L574.3,440.8L564.2,439.3L561.4,434.1L560.6,435.8L556.1,435.7L550.5,431.5L552.2,390.5L502,387.6L502.7,377L580.1,380.9L642.3,381.2L646,415.1L645.6,452.5L632.7,445.5L631.7,447.4L626.2,446.2L616.7,448.2L613.2,451.4L609.1,447L606.1,448.4L602.3,445.6L599.7,450.6L598.3,446.4L594.5,448.4L590.3,444.7L586.7,447.6L582.9,441.2Z" style="--order:7;--score:84%" tabindex="0" role="button" aria-label="Oklahoma, view demo score"/><text class="state-name" x="598.6" y="414.8" aria-hidden="true">OK</text><path class="us-state" id="state-OR" data-state="OR" d="M295,239.4L186.1,209.4L187,192.3L199.8,172.5L213.5,138.2L215.8,126.4L228.2,131.1L231.1,136.9L230.1,143.2L236.1,147.4L243.9,146L250.6,147.9L252.4,150.6L260.8,149.8L263.8,151.6L285.6,150.6L315.1,157.6L319.3,163.8L319.8,167.1L303,189.4L307,195.4L303.5,201.7L295,239.4Z" style="--order:8;--score:51%" tabindex="0" role="button" aria-label="Oregon, view demo score"/><text class="state-name" x="250.5" y="182.9" aria-hidden="true">OR</text><path class="us-state" id="state-PA" data-state="PA" d="M866.8,303.5L859,256.4L869.6,248.3L870.6,253.9L937.7,240.7L942.9,243.6L945.8,250.2L950.9,251.6L945.8,260.8L947.6,263.1L946.1,267.2L956.1,276.7L946.9,286.4L934.4,290.8L866.8,303.5Z" style="--order:9;--score:68%" tabindex="0" role="button" aria-label="Pennsylvania, view demo score"/><text class="state-name" x="905.5" y="272.1" aria-hidden="true">PA</text><path class="us-state" id="state-RI" data-state="RI" d="M994.3,242.2L991.5,227.6L997.7,225.8L1001.7,232.4L998.5,232.8L999.8,239.6L994.3,242.2ZM1002.4,232L1004.5,235.4L1003.5,236.4L1002.3,233.1L1002.8,236.3L1001.2,237.3L1001.6,236.6L1001.5,233.4L1002.4,232Z" style="--order:10;--score:85%" tabindex="0" role="button" aria-label="Rhode Island, view demo score"/><path class="us-state" id="state-SC" data-state="SC" d="M872.9,446.3L864,438L851.7,429.5L844.6,419.2L836.2,415.9L839.2,408.7L850.6,402.5L872.5,400.5L874,402.6L875.6,401L878.9,406.6L897.9,403.8L920.7,420.2L914.8,425.8L909.9,440.2L906.4,440.5L900.2,450.4L892.4,454.1L893.2,457.6L888.4,458.6L889.9,460.5L886.7,464.9L882.4,463.8L880,456.8L875.4,454L872.9,446.3Z" style="--order:11;--score:52%" tabindex="0" role="button" aria-label="South Carolina, view demo score"/><text class="state-name" x="884.8" y="432.7" aria-hidden="true">SC</text><path class="us-state" id="state-SD" data-state="SD" d="M581,253.8L496,249.1L501.4,187.3L611,192.5L606.7,199.4L612.6,205.9L612.4,243.7L610.1,244.8L612.6,251.8L609.5,259.8L612.5,265.1L600.3,257.3L591,256.8L588,259L581,253.8Z" style="--order:12;--score:69%" tabindex="0" role="button" aria-label="South Dakota, view demo score"/><text class="state-name" x="555.2" y="226.3" aria-hidden="true">SD</text><path class="us-state" id="state-TN" data-state="TN" d="M818.6,411.6L716.6,420.8L720.6,417.6L718.6,414.7L720.1,412.4L718.3,412.5L719.6,410.4L720.1,410.6L720.2,411.9L720.4,412.2L720.6,412.1L720.6,408.8L722.7,409.3L723.5,406.4L721.6,404.9L726.6,401.1L725,399L727.2,395.7L725.2,393.9L728,393.4L727.6,388.3L752.5,386.4L751.8,382.6L815.3,377.8L858.8,371.4L858.7,377.4L855.4,378.6L853.9,382.7L848.6,383.6L845.7,387.4L844,385.3L838.9,392.2L824.7,399.6L822.4,405.1L818.5,406.6L818.6,411.6Z" style="--order:0;--score:86%" tabindex="0" role="button" aria-label="Tennessee, view demo score"/><text class="state-name" x="779.9" y="396.1" aria-hidden="true">TN</text><path class="us-state" id="state-TX" data-state="TX" d="M504.2,527.7L497.4,530.2L493.2,540.7L487.4,545.5L471.8,537L463.3,528.8L458.2,508.7L450.2,502.7L430.2,478.6L431,476.4L493.9,482.3L501.3,387.5L552.2,390.5L550.5,431.5L556.1,435.7L560.6,435.8L561.4,434.1L564.2,439.3L574.3,440.8L576.3,442.9L582.8,441.1L585.2,446.9L587.5,447.5L590.3,444.7L594.5,448.4L598.3,446.4L599.7,450.6L602.3,445.6L606.1,448.4L609.1,447L613.2,451.4L616.7,448.2L626.2,446.2L631.7,447.4L632.8,445.5L647.4,454.1L653.4,453.9L654.1,486.8L658.1,491.3L658,495.2L664,506.8L660.2,517.2L661.2,527.2L657.1,532.6L658.8,535L641.7,542.2L647.1,538.2L641.6,538.7L642.4,533.3L638.2,535.2L637.3,538.5L640.2,542.1L634.7,547.5L641.1,542.4L642.8,542.9L630.7,552.7L612.3,562.8L619.7,557.3L615.1,558.7L615.2,556.2L610.3,558.9L607.3,556L611.8,561.6L606.8,563.8L603.7,561.8L604.4,566.1L596.7,568.9L600.2,568.5L597.1,574.4L596.4,574.3L595.9,573.3L595.5,573.2L591.6,573.6L595.8,577L592.9,584.5L589,585.5L587.4,583.7L588.6,586.4L592.5,586L589.7,594.7L594.6,610L596.1,612.4L597.3,611L597.4,613.3L593,615.6L587.8,611.7L577.4,610.8L565.9,604L560.7,603.2L554.3,590L553.5,578.6L547.5,574.3L546,569.7L539.5,563.2L531.2,542.6L523.1,536.4L519.5,530.7L504.2,527.7ZM597.3,610.9L593.1,595.2L593.1,588.2L593.7,584L598.1,574.4L599.6,574L602.9,568L611.9,562.7L601.3,571.8L594.8,583L593.4,593.4L596.6,606L597.3,610.9Z" style="--order:1;--score:53%" tabindex="0" role="button" aria-label="Texas, view demo score"/><text class="state-name" x="555.6" y="501.6" aria-hidden="true">TX</text><path class="us-state" id="state-UT" data-state="UT" d="M402.6,366.4L320.3,352.8L340.4,249L386.3,256.9L383,277.9L414.1,282.5L402.6,366.4Z" style="--order:2;--score:70%" tabindex="0" role="button" aria-label="Utah, view demo score"/><text class="state-name" x="369.9" y="307.4" aria-hidden="true">UT</text><path class="us-state" id="state-VA" data-state="VA" d="M894.4,367.1L825.2,376.4L833.7,372.2L839.5,363.4L850.6,352.8L851.8,356.5L856.4,359.1L877.8,349.3L877.4,345.3L884.6,324.7L891.2,327.3L894.1,317.5L896.5,318.9L902.4,309.1L902.1,302.7L911.7,308.1L912.5,304L915.1,303.7L916.6,307.4L925.3,311.1L922.9,322.1L927.2,320.8L929.3,324.4L935.2,324.7L942.4,328.8L941.5,335L933.6,331L938.6,335.4L942.8,335.8L944.3,340.9L941.6,339.5L943.2,341.9L940.9,343.3L944.8,344.8L945.1,347.4L943.2,348.5L938.6,344L934.1,345L938.1,344.6L942.9,350.4L945.4,348.1L950.5,348L954.3,355.2L894.4,367.1ZM954.4,328.1L950.1,344.5L948.4,339.9L950,326.8L957.7,322.5L954.4,328.1Z" style="--order:3;--score:87%" tabindex="0" role="button" aria-label="Virginia, view demo score"/><text class="state-name" x="910.8" y="339.6" aria-hidden="true">VA</text><path class="us-state" id="state-VT" data-state="VT" d="M975.7,212.5L977.8,215.4L965.5,218.1L962.1,201.8L960.7,200.1L959,201.4L953.2,172.4L980.3,165L979.3,171L981.4,175.8L975.5,182.3L977.1,186.3L974.6,197.8L975.7,212.5Z" style="--order:4;--score:54%" tabindex="0" role="button" aria-label="Vermont, view demo score"/><path class="us-state" id="state-WA" data-state="WA" d="M223.7,128L215.2,125.4L217.7,117.8L217.5,121.9L221.2,117.4L217.9,115.9L218.3,112.4L222.4,112.7L219.3,109.7L217.8,111.8L219.5,94.5L217.5,89L219.4,80.4L228.1,87.9L240.2,91L242.2,95.8L242.8,93.4L244.6,93.2L244.1,95.6L244.6,94.4L245.3,94.4L245.1,99L241.2,102.3L242.1,100.1L242,99.2L234.6,107.4L246.2,98.6L246.3,102.1L245.1,102L242.5,111.3L240.5,110.8L241.3,109.2L238.9,112.8L239.3,108.7L238.1,110.3L237.5,112.4L239.7,114.4L241.3,113.3L242.9,111.2L242.7,110.6L246,110.9L246.3,104.2L251.2,97.9L250,92.9L249.6,96.6L247.9,94.4L248.3,92L250.7,91.9L249.1,88L247.1,87L250.4,87.8L249.8,85.2L251.8,85.4L251.3,81.5L249.2,81.8L249.6,76.1L327.2,96.1L314.6,149.8L315.1,157.6L285.6,150.6L263.8,151.6L260.8,149.8L252.4,150.6L250.6,147.9L243.9,146L236.1,147.4L230.1,143.2L230.6,134L228.2,131.1L224.4,130.8L223.7,128ZM245.5,84.4L245.1,86.8L245.8,85.4L246.6,85.9L245.5,87.5L243.9,86.1L245.5,84.4ZM242.7,82.3L243.6,86.3L241.4,82.2L242.7,82.3ZM247.8,82.9L245.9,81.7L245.7,83.8L243.7,82.4L245.9,81.2L247.8,82.9ZM244.8,107L245.5,109.9L243.2,110.4L244.8,107ZM247,96.6L247.5,95.1L249.2,96.9L248.4,99.5L246.5,97.6L244.9,91.6L248.2,88.5L248.9,91.1L245.5,91.6L247,96.6Z" style="--order:5;--score:71%" tabindex="0" role="button" aria-label="Washington, view demo score"/><text class="state-name" x="271.6" y="116.9" aria-hidden="true">WA</text><path class="us-state" id="state-WI" data-state="WI" d="M702,262.1L695.4,257.9L693.8,254.4L694.7,247L692.2,244.8L689.3,232.8L667,216.6L668.9,202L665.2,198.9L667.6,192.6L673.6,188.5L673.1,176.1L675.7,174.3L680.4,175.3L693.6,169L695.2,170.5L692.8,176.9L695.6,174.5L703.4,178.1L705,181.4L733.8,187.5L735.3,190.7L739.8,192.1L739.2,199.6L742.6,199L741.8,203.2L744.2,204.8L740.7,208.4L739,216.8L744.3,210L747.6,209.2L749.2,202.7L752.9,200L744.2,230.3L742.7,243.8L745.7,259.6L702,262.1ZM695.2,173.3L697.1,170.7L697.9,171.1L695.2,173.3ZM753.9,199.5L753.1,196.9L755,196.7L753.9,199.5Z" style="--order:6;--score:88%" tabindex="0" role="button" aria-label="Wisconsin, view demo score"/><text class="state-name" x="703.0" y="215.7" aria-hidden="true">WI</text><path class="us-state" id="state-WV" data-state="WV" d="M853.3,357.8L840.7,345.8L837.6,341.3L837.7,335.9L841.9,334.7L843.9,331L842.6,327.2L844.9,321.8L847.5,324.6L849.6,323.3L849.7,315.8L852.9,312.4L856.8,312.2L861.4,306.5L863.4,291.2L862,285L863.6,284.3L866.8,303.5L883.3,300.7L885,311.4L890.2,304.8L892.5,305.1L894.8,300.2L898.4,302.3L903.9,297.4L909.7,298.4L912.6,303.8L911.7,308.1L902.1,302.7L902.4,309.1L896.5,318.9L894.1,317.5L891.2,327.3L884.6,324.7L877.4,345.3L877.8,349.3L870.7,353.2L869.1,352.3L868.8,354.8L863.7,357.3L861.1,355.5L858.3,358.7L853.3,357.8Z" style="--order:7;--score:55%" tabindex="0" role="button" aria-label="West Virginia, view demo score"/><text class="state-name" x="871.3" y="321.7" aria-hidden="true">WV</text><path class="us-state" id="state-WY" data-state="WY" d="M492.5,291.2L383,277.9L396.2,194.4L499.5,207.1L492.5,291.2Z" style="--order:8;--score:72%" tabindex="0" role="button" aria-label="Wyoming, view demo score"/><text class="state-name" x="442.6" y="242.8" aria-hidden="true">WY</text><path class="us-state" id="state-AK" data-state="AK" d="M69.8,622.7L67.6,623.1L67.8,621.6L69.8,622.7ZM73.1,623.2L74.5,625.1L71.6,625L73.1,623.2ZM69.5,623.6L71.6,622.7L72,623.2L71.2,624.2L69.5,623.6ZM83.5,625.5L87.4,627L85.1,626.7L83.5,625.5ZM83.3,625.6L80.7,625.4L78.5,624.6L82.2,624.9L83.5,623.7L83.3,625.6ZM102.9,626.3L108.7,623.2L105.6,625.4L102.9,626.3ZM114.1,621.7L113.5,622.9L115.1,622.8L112.4,624.4L108.2,624.4L112.4,623L111.9,621.1L114.1,621.7ZM122.5,582L123.9,585.1L121.8,586L118.5,583.3L122.5,582ZM103,577.9L102.5,575.9L104.1,578.3L103,577.9ZM115.1,559.4L118.8,562.6L118.4,563.3L115.7,564.2L113.8,561.1L110.5,559.6L111.3,557.6L113.1,559.5L115.1,559.4ZM137.3,619L138.8,616.5L138.9,617.5L137.3,619ZM139.4,613L133.2,615.5L133,613.8L130.2,617.3L129,615.4L129,617.5L126.9,616.4L127.3,617.4L126,618.2L127,619.1L120.3,619.5L122.1,616.7L125.7,616.5L126.3,617.6L126.5,616.2L132.4,612L135.7,611.7L135.2,612.3L135.8,613.4L136,612.5L137.7,613.4L136.7,611.9L137.8,610.1L143.8,607.5L145,604.6L147.7,603.3L148.2,597.7L150.2,594.1L146.1,596.2L145.6,593.3L143.8,597.4L141.7,593.8L140.6,594.7L139.4,592.8L134.6,595.5L133.3,594.7L134.7,594.1L134.1,591L135.4,589.7L133.6,584.4L134.8,582.4L133.3,584.6L133.3,586.2L129.5,587L128.1,586.4L126.2,581.7L125,581.7L127.1,578.3L125,577.9L124.3,573.2L125.8,573.2L125.6,571.8L128.9,569.1L130.5,565.4L134,567L136.7,564.2L139.9,564.8L141.1,562.9L139.4,559L141.6,557.3L140.7,555.9L136,559.2L135.2,557.1L135.1,558.6L133.4,557.2L130.1,557.6L126.7,555.7L125.9,552.4L127.5,551.7L123.4,548.6L133.9,544.6L135.2,544.7L135.8,545L134.2,547.2L134.9,548L139.8,548.9L142.1,547.8L140.9,546.7L139.8,547.4L138.5,543.5L139.3,543.1L140.9,546.4L141.3,543L136.1,541.6L135.5,538.3L129.9,532.8L132,529.8L138,529.4L142.7,522.6L145.1,522.5L148.9,519.6L151.7,519.9L154.5,517L156.5,518.2L155.6,520.4L157.6,518.3L159.4,520.7L163.4,520.2L164.3,522.7L169.4,521.9L173.4,523.5L179.5,524.3L182.3,522.7L188.4,524.8L199.7,582L202.9,582.1L205.4,580.5L205.5,582.2L211.6,586.2L212.3,588.2L214.1,586.1L214.9,585.9L215.1,582.8L218.1,581.5L219.7,583.8L226.1,587.4L234.7,596.6L241.3,597.4L243.6,602.1L242.4,606.3L240.7,605.1L240.7,604.6L241.4,604.3L241.5,604.1L241.5,603.9L240.2,604.4L241.2,602.8L238.2,599L239.8,604.1L239.3,603L238.8,604L237,603.4L237.4,602.6L236.8,601.5L237.4,601L236.8,600.3L235.9,601L236.5,603.3L235.6,603L235.4,598.9L234.6,599.6L234.6,601.6L233.2,600.9L232.9,599L234,599.5L233.1,597.9L234,598.2L232.5,595.9L231.1,596.2L230.5,594.8L227.9,595L228.7,593.9L226.6,591.9L228.4,592.1L224.7,590.2L224.3,588.5L222.5,589.7L218.2,583L219,585.3L218,584.5L221.3,590.4L219.7,589.5L218.2,590L216.6,586.7L216.6,588.1L215.3,587L213.7,586.9L213.8,588.2L215.4,587.8L217.6,589.7L216.2,591.7L204.2,586L204.8,585.6L205.1,584.8L204.6,582.7L202.6,585.4L198.9,584.9L199.1,583.5L190.1,585.5L189.9,584.5L187.7,584.2L187.8,583.1L187,583.4L186.5,584L184.5,583.5L184.9,583.1L185.2,582.1L183.4,582.6L183.9,581.6L182.1,582.3L183.5,581.2L181.6,581.6L183,579.5L179.8,581.4L179.2,579.8L179.2,581.6L177.6,582.1L178.6,579L176.1,582.6L177.5,583.3L176.5,583.7L176.1,584.4L178.3,583.9L177.2,585.7L178,586.8L175.1,586.9L174.5,588.2L174.3,586.9L174,586.6L173.8,589.3L173.1,587.8L171.5,591.2L171.5,589.8L170.4,590.5L169.4,592.7L167,593.1L166.5,591.4L169.4,589L166.5,589.3L167.7,583.2L170.7,581.1L174.9,582L171.6,580.3L173,578.1L166.7,582L163.7,586.4L163.8,588.4L159.4,591.9L159.2,594.1L162.2,595.1L159.1,599.6L156.5,600.3L151.2,604.5L151.1,606.6L144.5,609.6L145.5,611L144.3,612.5L143.9,611.5L143.4,612.7L140.5,612.8L140.3,614.3L139.6,614.8L139.4,613ZM159.1,602.6L160.4,604.5L160,601.6L161.4,602.2L161.4,600.6L162.8,601.3L162.2,600.4L163.5,602.1L165,600.5L164.9,602.9L165.9,602.7L165.3,604L163.3,603.4L164.4,604.6L162.4,605.4L163.6,605.7L162.1,606.8L162,605.5L159.3,608.3L160.5,605.7L158.7,607.7L157.1,604.9L159.1,602.6ZM166.4,599L161.7,600.1L165.2,596.4L164.7,598.2L166.4,599ZM220,592.7L221.3,593.4L222.5,592.9L223.3,594.5L220.3,593.9L220.2,596L216.7,592.4L218.8,590.5L219.9,592.2L220.3,591L222,591.3L222.1,592.8L220,592.7ZM179.1,587.6L180.8,584.5L181.6,584.8L180.2,587.7L179.1,587.6ZM235.7,608.9L233.1,607.3L233,606L235.7,608.9ZM225.6,601.9L222.7,599.2L222,596.4L220.7,596L221.2,594.5L223.6,595.3L225.6,601.9ZM228.1,597.6L227.8,601.8L228.3,602.6L227.1,600.7L227.8,600L225.8,597.9L226.1,597.2L228.1,597.6ZM226.6,596.2L232.4,597.5L230.9,598.4L230.8,597.9L229.5,596.9L230.7,598.4L229,599.5L228.2,597.2L226.6,596.2ZM224.3,590.3L226.4,592.9L224.1,590.7L223.9,590.9L224.3,591.6L226.6,594.2L224.8,597.1L221.2,589L222.5,590.2L224.3,590.3ZM56.7,619L58.1,621.3L55.7,618.4L56.7,619ZM38.6,601.1L40.4,601.6L41,603L39,602.5L38.6,601.1ZM232.6,604.8L230.9,601.2L231,602.5L230.7,601.8L229.4,602.7L229.3,600L230.9,599.7L231.6,600.8L235.9,603.6L234.5,603.4L234.4,604.1L236.9,604.7L237.9,608.1L234.7,605.6L232.6,605.9L232.6,604.8Z" style="--order:5;--score:68%" tabindex="0" role="button" aria-label="Alaska, view demo score"/><text class="state-name" x="155" y="591" aria-hidden="true">AK</text><path class="us-state" id="state-HI" data-state="HI" d="M389.9,647L391.9,649.5L388.8,651L388,652L387.1,651.4L386.9,649.4L386.2,648.3L387.3,647.1L387.1,645.8L389.9,647ZM386.3,644L384.5,644.3L384.4,643.4L383.4,643L383.6,642.3L386.6,643.5L386.3,644ZM376.8,640.9L376.1,639.8L377.5,639.2L378.1,640.3L379,641L376.8,640.9Z" style="--order:5;--score:68%" tabindex="0" role="button" aria-label="Hawaii, view demo score"/></g>
<circle id="mapHalo" class="map-halo" cx="488" cy="365" r="57" fill="url(#beam)" pointer-events="none"/>
<circle id="mapBeacon" cx="488" cy="365" r="6" fill="var(--primary)" stroke="#eafffa" stroke-width="2" pointer-events="none" filter="url(#brightGlow)"/>
</svg>
<aside class="map-flyout" id="mapFlyout" aria-live="polite" aria-hidden="true"><div class="flyout-top"><span class="eyebrow">Location spotlight</span><span class="flyout-rank" id="stateRank">NO. 06</span></div><h3 id="stateTitle">New Mexico</h3><div class="flyout-main"><strong id="stateScore">83.2</strong><div><b>DEMO INDEX SCORE</b><small>out of 100 · illustrative</small></div></div><div class="flyout-grid"><div><strong id="metric1">238</strong><small>OBSERVATIONS*</small></div><div><strong id="metric2">76</strong><small>CONDITIONS*</small></div><div><strong id="metric3">29</strong><small>SITES*</small></div><div><strong id="metric4">4.5</strong><small>MODEL RATING*</small></div></div><p id="stateNote">Explore the map to compare states. All example values are fictional.</p></aside>
<div class="atlas-foot"><span><i></i> Fully interactive US state geometry</span><span>Hover or focus · tap on mobile</span><span>*Fictional demo metrics</span></div>
</div></div>
<div class="geo-mode-panel geo-na-panel" id="northAmericaPanel" data-map-panel="na" hidden>
 <div class="na-stage" id="naStage">
  <div class="na-topline"><strong>US &amp; Canada · Regional Explorer</strong><span id="naRegionCount">50 US states + 13 Canadian provinces / territories</span></div>
  <div class="na-scale"><span>Lower score</span><b></b><span>Higher score</span></div>
  <div class="na-loading" id="naLoading">Loading state, province and territory boundaries…</div>
  <svg class="na-map" id="naMapSvg" viewBox="0 0 1060 620" role="img" tabindex="0" aria-label="US and Canada only: interactive map of 50 US states and 13 Canadian provinces and territories" hidden><g id="naRegions"></g><g id="naLabels"></g></svg>
  <aside class="na-tip" id="naTip" aria-hidden="true"></aside>
  <div class="na-foot"><span>US states and Canadian provinces / territories only</span><span>Hover, focus or tap a region</span><span>Fictional scores · boundaries from Click That Hood</span></div>
 </div>
</div>
<div class="geo-mode-panel geo-world-panel" id="globalMapPanel" data-map-panel="world" data-map-mode="world" hidden>
<div class="world-canvas" id="worldStage"><div class="world-map-clip"><svg class="world-map" viewBox="0 0 778 338" role="img" aria-label="Interactive country map with fictional scores. Use the geographic mode switcher above to change between North America and the world" tabindex="0"><defs><clipPath id="worldRegionClip" clipPathUnits="userSpaceOnUse"><rect id="worldClipRect" x="0" y="0" width="778" height="338"/></clipPath></defs><g id="worldCountries" clip-path="url(#worldRegionClip)">
 <path class="world-country" data-country="Fiji" d="M774.0,210.0 L774.0,211.1 L771.3,212.0 L771.0,211.2 L774.0,210.0Z M769.0,212.8 L770.9,214.4 L768.4,214.5 L769.0,212.8Z"/>
<path class="world-country" data-country="Tanzania" d="M459.9,178.0 L471.3,185.9 L470.3,188.5 L471.8,190.5 L471.3,193.9 L473.7,197.8 L472.0,199.1 L461.3,200.4 L459.5,195.9 L453.1,193.6 L450.7,189.8 L450.1,185.5 L453.1,183.1 L452.4,178.4 L459.9,178.0Z"/>
<path class="world-country" data-country="W. Sahara" d="M368.4,117.3 L368.3,121.1 L361.3,121.0 L361.3,126.4 L359.3,126.6 L359.2,130.7 L350.3,131.4 L355.3,130.4 L362.5,119.0 L368.1,118.5 L368.4,117.3Z"/>
<path class="world-country target" data-country="Canada" data-score="84" d="M122.9,72.1 L116.9,69.1 L113.0,68.2 L112.1,65.0 L106.4,60.9 L107.5,57.4 L103.8,56.1 L95.7,49.2 L91.5,51.1 L83.9,48.1 L83.9,28.2 L93.5,29.9 L107.9,27.1 L109.4,28.0 L111.5,26.5 L116.6,28.7 L119.5,27.2 L119.8,28.8 L125.8,28.0 L139.2,29.9 L142.1,31.0 L139.1,32.0 L143.0,32.5 L150.6,31.8 L152.9,33.1 L155.2,32.0 L153.1,31.1 L154.4,30.4 L158.8,30.1 L168.9,32.5 L175.3,32.3 L175.1,30.9 L177.0,30.6 L180.3,31.3 L180.3,33.3 L184.4,29.5 L179.6,27.4 L179.8,25.0 L182.3,23.5 L187.3,24.8 L190.2,27.2 L188.3,28.2 L192.3,28.6 L192.3,30.8 L195.2,29.1 L197.8,30.5 L197.1,32.1 L199.2,33.5 L203.0,30.1 L203.1,27.8 L209.4,28.3 L212.2,29.3 L210.8,31.5 L212.0,33.7 L202.6,34.9 L199.3,38.6 L192.0,41.1 L191.8,42.5 L189.3,42.7 L184.4,46.9 L183.4,51.0 L186.6,51.3 L188.6,54.9 L191.6,54.5 L204.2,58.7 L210.1,59.0 L210.4,63.0 L215.2,67.4 L218.0,64.5 L215.4,60.1 L222.4,56.1 L218.2,51.3 L220.7,49.1 L219.1,43.8 L228.2,43.6 L233.5,46.3 L237.4,46.5 L238.0,51.0 L241.6,52.6 L248.1,48.0 L255.0,55.2 L254.1,56.5 L263.7,60.2 L267.1,63.0 L267.3,65.4 L257.9,69.4 L244.2,69.5 L234.1,76.7 L239.4,73.6 L247.1,71.6 L249.0,72.6 L247.0,74.0 L248.4,77.9 L251.2,79.0 L254.7,78.7 L256.9,76.3 L258.4,78.6 L246.5,83.6 L244.8,83.5 L244.8,81.7 L248.5,79.9 L242.7,80.3 L241.3,76.2 L238.1,75.4 L233.3,80.5 L226.0,80.6 L221.8,83.5 L217.8,83.5 L217.3,85.1 L209.8,87.6 L208.2,87.0 L210.4,83.6 L209.5,79.8 L197.0,73.6 L190.0,73.9 L184.2,72.8 L183.1,71.3 L122.9,72.1Z M206.4,43.6 L208.0,42.6 L211.0,42.6 L208.4,44.2 L206.4,43.6Z M215.5,21.6 L213.2,19.7 L219.2,19.8 L223.1,21.6 L215.5,21.6Z M214.3,44.3 L215.2,43.7 L216.6,44.2 L215.7,45.3 L214.3,44.3Z M185.7,17.0 L184.6,17.8 L178.8,17.1 L183.1,15.6 L185.7,17.0Z M185.2,11.6 L180.2,11.5 L179.7,11.0 L184.0,11.0 L185.2,11.6Z M174.9,8.8 L181.5,9.7 L177.8,10.9 L174.9,8.8Z M197.5,18.2 L188.3,17.3 L185.1,14.2 L178.2,13.2 L190.0,13.2 L195.2,15.7 L212.6,15.4 L215.4,17.1 L197.5,18.2Z M144.6,10.5 L150.8,10.6 L142.9,11.2 L144.6,10.5Z M147.3,8.8 L151.2,9.3 L145.0,9.7 L147.3,8.8Z M267.5,67.2 L264.9,70.4 L272.0,71.6 L271.4,73.1 L272.9,72.7 L273.8,75.2 L272.9,77.1 L270.5,76.7 L270.4,74.7 L267.9,76.6 L266.6,76.5 L268.1,75.5 L266.1,75.0 L259.6,75.0 L259.7,73.1 L263.7,68.4 L267.5,67.2Z M202.3,36.6 L211.7,40.3 L214.8,40.9 L208.3,40.1 L203.1,42.3 L202.4,41.0 L199.5,41.3 L201.3,40.2 L202.3,36.6Z M213.4,23.2 L219.7,21.7 L227.7,24.7 L231.7,24.3 L239.1,26.4 L243.0,29.3 L239.1,30.3 L254.0,34.2 L249.6,38.2 L243.5,35.2 L240.8,35.5 L240.5,36.7 L246.6,39.5 L248.0,41.6 L247.2,43.1 L239.1,40.8 L244.7,44.7 L238.9,43.8 L226.1,38.8 L218.1,39.1 L219.5,37.5 L228.0,37.2 L228.0,35.4 L230.8,33.3 L229.4,31.7 L221.7,29.9 L223.1,29.4 L217.2,27.2 L212.2,28.1 L196.3,26.7 L194.5,25.9 L196.8,25.0 L193.7,25.0 L193.1,22.8 L196.9,20.1 L202.5,19.5 L200.9,20.9 L202.6,22.2 L204.6,20.5 L210.0,19.6 L213.7,21.8 L213.4,23.2Z M180.6,20.3 L188.3,18.9 L192.4,19.4 L181.9,23.2 L180.6,20.3Z M122.9,14.6 L130.9,11.6 L137.2,11.4 L135.2,13.7 L122.9,14.6Z M100.7,61.1 L103.7,61.2 L103.1,63.6 L105.0,65.3 L100.9,62.7 L100.7,61.1Z M160.2,7.8 L170.2,8.9 L172.7,10.8 L160.9,9.8 L162.9,9.2 L160.2,7.8Z M121.5,73.1 L116.8,72.5 L111.7,70.0 L111.0,68.3 L116.6,69.3 L121.5,73.1Z M118.4,18.5 L134.3,18.7 L138.7,20.2 L130.7,22.2 L128.0,24.6 L122.4,25.6 L116.3,23.6 L120.5,19.8 L118.4,18.5Z M155.2,15.2 L159.4,14.9 L159.7,15.9 L145.7,18.2 L142.2,17.6 L146.6,16.6 L133.9,16.5 L138.9,13.8 L152.5,16.0 L149.4,13.9 L151.4,13.2 L155.2,15.2Z M153.9,21.0 L160.4,21.9 L162.4,25.5 L169.7,28.4 L166.1,28.6 L166.8,30.2 L159.2,29.3 L143.4,30.7 L134.7,27.6 L145.3,26.8 L133.5,26.4 L132.4,25.6 L137.4,24.8 L130.3,24.3 L133.6,21.8 L139.3,20.5 L141.5,20.9 L140.5,21.9 L150.7,21.3 L154.4,24.1 L155.5,23.2 L153.9,21.0Z M171.1,21.8 L168.7,20.4 L177.6,19.6 L176.2,21.2 L179.4,22.1 L179.1,24.0 L175.5,24.9 L166.6,22.2 L171.1,21.8Z M157.8,19.9 L160.7,19.8 L162.3,20.3 L160.4,21.7 L157.8,19.9Z M175.2,13.3 L176.9,14.3 L176.0,17.0 L166.6,15.8 L166.5,14.1 L175.2,13.3Z M179.1,6.0 L188.3,3.7 L202.5,7.8 L195.6,10.0 L187.3,9.9 L185.0,9.0 L186.7,7.7 L179.1,6.0Z M190.1,2.3 L216.5,-0.3 L254.0,0.8 L241.5,3.2 L246.2,3.2 L234.0,6.8 L221.6,7.8 L224.6,8.1 L223.1,8.4 L224.9,9.5 L215.5,12.3 L219.5,13.2 L213.8,14.5 L194.6,13.8 L194.3,12.8 L198.3,12.3 L197.2,10.8 L204.3,11.6 L197.9,9.8 L204.0,7.7 L200.1,5.8 L211.0,5.4 L198.7,5.3 L190.1,2.3Z M225.3,33.0 L221.5,33.7 L220.9,32.7 L223.8,31.2 L225.3,33.0Z M175.8,27.3 L181.4,29.5 L180.0,30.2 L172.4,28.8 L175.8,27.3Z M248.3,70.2 L251.9,70.6 L254.1,71.9 L250.3,71.2 L248.3,70.2Z M249.4,76.2 L250.1,77.3 L253.7,77.5 L251.8,78.5 L249.1,77.6 L249.4,76.2Z"/>
<path class="world-country target" data-country="United States of America" data-score="65" d="M122.9,72.1 L183.1,71.3 L184.2,72.8 L190.0,73.9 L197.0,73.6 L209.5,79.8 L210.4,83.6 L208.3,86.8 L209.2,87.6 L217.3,85.1 L217.8,83.5 L221.8,83.5 L226.0,80.6 L233.3,80.5 L238.1,75.4 L241.3,76.2 L241.2,79.1 L243.0,81.0 L236.3,83.3 L234.7,86.2 L236.6,87.7 L228.5,89.2 L232.3,89.2 L228.0,89.6 L226.0,93.4 L224.6,92.2 L225.6,94.5 L223.7,97.1 L222.8,93.0 L222.9,95.2 L221.5,94.9 L223.0,95.6 L224.2,100.6 L212.1,109.3 L214.9,119.0 L214.2,122.5 L211.3,121.1 L207.0,112.5 L204.0,113.1 L201.2,111.5 L194.4,112.0 L194.8,114.1 L183.4,113.5 L178.1,117.0 L177.3,121.2 L174.1,120.1 L169.9,113.7 L163.5,113.9 L158.0,108.6 L148.3,109.5 L140.3,106.6 L135.2,107.0 L132.2,103.8 L127.7,102.6 L119.5,90.5 L120.6,79.5 L118.9,73.8 L122.3,74.1 L123.4,76.1 L122.9,72.1Z M52.9,133.4 L54.2,134.6 L52.3,135.9 L51.4,134.2 L52.9,133.4Z M51.6,131.9 L50.7,132.3 L50.1,131.6 L50.3,131.4 L51.6,131.9Z M27.0,48.3 L30.8,48.1 L31.0,49.0 L27.0,48.3Z M54.5,54.1 L59.9,53.9 L54.8,55.1 L54.5,54.1Z M83.9,28.2 L83.9,48.1 L91.5,51.1 L95.7,49.2 L103.8,56.1 L107.5,57.4 L106.3,59.8 L103.3,58.3 L98.7,52.7 L93.2,52.6 L86.3,49.7 L70.7,46.9 L68.3,47.3 L68.8,48.8 L60.8,50.5 L63.2,46.0 L55.9,50.1 L57.4,51.2 L55.4,52.7 L46.4,57.3 L32.4,60.3 L45.8,55.1 L49.4,51.1 L38.8,51.6 L39.0,49.5 L37.6,48.8 L31.5,47.7 L29.8,45.6 L30.7,44.4 L33.2,42.1 L41.3,40.8 L39.7,39.4 L41.3,38.6 L32.3,39.3 L25.6,36.7 L33.4,34.8 L39.4,35.8 L28.5,31.0 L29.7,29.9 L50.4,24.7 L83.9,28.2Z M17.8,40.7 L20.4,40.9 L24.3,41.8 L22.5,42.4 L17.8,40.7Z"/>
<path class="world-country" data-country="Kazakhstan" d="M574.8,71.6 L571.4,73.2 L570.1,76.3 L565.8,75.6 L564.3,79.4 L558.9,80.7 L560.9,84.4 L559.6,86.2 L546.6,84.2 L545.0,85.9 L540.1,85.4 L534.6,89.7 L530.4,88.7 L529.1,84.8 L526.5,83.3 L520.3,83.7 L512.8,79.3 L507.2,80.6 L507.3,88.4 L503.3,86.2 L499.9,87.4 L499.9,85.2 L497.4,84.5 L495.2,81.4 L501.0,80.0 L501.0,76.6 L492.6,77.6 L486.9,73.4 L489.2,69.0 L491.4,70.2 L491.7,68.7 L496.1,66.4 L506.8,68.6 L518.9,68.3 L519.4,67.3 L515.9,65.8 L519.7,63.6 L518.1,62.2 L519.1,61.5 L535.5,58.5 L539.4,59.0 L540.0,61.2 L545.0,61.4 L544.9,62.6 L552.3,60.4 L551.5,61.1 L559.1,68.1 L560.2,67.0 L566.3,67.7 L574.8,71.6Z"/>
<path class="world-country" data-country="Uzbekistan" d="M507.3,88.4 L507.2,80.6 L512.8,79.3 L520.3,83.7 L526.5,83.3 L529.1,84.8 L530.4,88.7 L533.8,89.8 L539.6,86.4 L538.4,87.9 L544.1,89.3 L541.3,90.9 L538.8,90.7 L538.9,89.1 L536.1,89.6 L534.4,92.1 L532.6,92.0 L534.0,95.1 L532.8,97.2 L530.0,96.8 L530.1,95.5 L513.1,85.3 L509.4,87.3 L509.8,88.4 L507.3,88.4Z"/>
<path class="world-country" data-country="Papua New Guinea" d="M690.2,181.5 L697.9,184.1 L700.9,187.5 L704.4,188.9 L703.5,191.6 L711.0,198.4 L705.0,197.4 L701.0,193.1 L698.2,192.1 L693.7,195.7 L690.2,195.3 L690.2,181.5Z M715.2,183.7 L715.6,186.1 L710.9,181.8 L711.5,181.3 L715.2,183.7Z M714.5,186.3 L708.9,189.4 L705.9,188.1 L709.8,186.6 L711.2,187.5 L714.1,184.8 L714.5,186.3Z M719.7,187.3 L722.4,189.8 L722.1,190.4 L720.6,189.8 L719.7,187.3Z"/>
<path class="world-country" data-country="Indonesia" d="M690.2,181.5 L690.2,195.3 L688.3,193.5 L682.9,193.8 L685.1,191.5 L683.5,187.4 L674.4,183.5 L672.9,184.7 L670.8,181.9 L674.4,180.7 L671.3,180.7 L667.6,177.9 L671.6,176.7 L675.1,177.6 L676.0,181.8 L678.2,183.1 L682.5,179.6 L690.2,181.5Z M655.7,194.8 L654.5,197.5 L652.4,197.7 L653.6,195.7 L655.7,194.8Z M675.6,190.6 L675.3,189.0 L676.2,187.5 L676.7,189.1 L675.6,190.6Z M640.4,167.2 L639.2,169.1 L642.8,174.0 L640.3,174.3 L636.7,184.5 L624.0,182.2 L621.2,175.1 L622.8,171.7 L624.6,174.3 L631.7,173.4 L633.4,172.9 L636.1,166.8 L640.4,167.2Z M662.0,183.2 L667.5,182.5 L668.3,184.1 L662.0,183.2Z M659.8,184.0 L658.3,183.6 L657.9,182.7 L660.1,182.6 L659.8,184.0Z M662.1,171.3 L663.7,173.6 L662.4,177.9 L660.9,173.8 L662.1,171.3Z M651.3,174.1 L656.3,172.9 L652.9,175.5 L645.4,175.5 L645.1,177.1 L647.0,178.9 L652.2,177.3 L648.2,180.0 L651.8,187.3 L649.8,187.2 L650.8,185.4 L648.2,185.7 L647.1,181.5 L645.7,182.2 L645.9,187.7 L644.6,188.0 L643.9,183.4 L642.4,181.9 L644.6,175.6 L646.9,173.2 L651.3,174.1Z M646.7,197.1 L642.8,196.2 L644.8,195.8 L646.7,197.1Z M644.8,194.6 L649.3,193.9 L651.2,193.1 L650.9,194.3 L644.8,194.6Z M640.5,193.1 L643.1,194.4 L638.0,195.1 L640.5,193.1Z M615.0,188.5 L629.1,190.7 L635.8,193.7 L633.3,194.5 L613.5,190.5 L615.0,188.5Z M609.4,177.5 L615.1,182.5 L614.5,188.4 L612.1,188.4 L607.6,184.9 L591.9,164.3 L596.6,164.8 L603.4,171.5 L607.4,173.0 L610.3,175.7 L609.4,177.5Z"/>
<path class="world-country" data-country="Argentina" d="M239.4,287.5 L241.3,290.1 L247.1,291.9 L244.1,293.1 L239.4,292.3 L239.4,287.5Z M263.1,240.0 L261.2,249.0 L264.0,250.8 L264.9,254.2 L262.8,256.9 L259.7,258.0 L253.0,258.3 L253.4,262.2 L252.1,262.9 L247.0,263.0 L247.3,265.1 L250.6,266.2 L246.9,268.2 L246.0,271.4 L242.3,272.5 L241.7,274.1 L245.9,276.1 L238.4,283.5 L240.5,286.9 L232.4,286.2 L229.2,280.5 L231.5,278.2 L233.9,270.9 L231.9,265.5 L234.7,257.7 L234.1,253.7 L236.9,248.5 L235.3,242.5 L237.2,236.3 L240.2,233.0 L239.9,227.9 L242.2,226.9 L244.5,222.2 L248.6,224.3 L249.4,222.6 L251.9,222.7 L256.2,226.6 L262.8,229.3 L261.0,233.5 L267.3,234.0 L270.6,230.1 L271.7,233.0 L263.1,240.0Z"/>
<path class="world-country" data-country="Chile" d="M239.4,287.5 L239.4,292.3 L243.0,292.3 L240.5,293.9 L234.3,292.7 L226.5,288.0 L234.1,290.6 L235.9,288.2 L239.4,287.5Z M237.4,213.2 L239.8,217.1 L239.2,219.2 L241.2,224.5 L243.0,224.7 L242.2,226.9 L239.9,227.9 L240.2,233.0 L237.2,236.3 L235.3,242.5 L236.9,248.5 L234.1,253.7 L234.7,257.7 L231.9,265.5 L233.9,270.9 L231.5,278.2 L229.2,280.5 L232.4,286.2 L239.6,286.8 L234.7,288.1 L233.4,290.1 L225.9,286.8 L224.4,279.1 L227.6,275.5 L224.4,274.9 L227.1,269.5 L229.5,270.2 L230.7,265.8 L229.2,265.2 L228.5,267.9 L227.2,267.6 L229.6,259.2 L228.8,254.7 L233.4,244.7 L233.3,237.1 L236.3,221.3 L235.7,214.9 L237.4,213.2Z"/>
<path class="world-country" data-country="Dem. Rep. Congo" d="M449.4,182.0 L453.1,193.6 L448.8,194.0 L448.0,201.0 L450.7,201.8 L450.9,204.1 L445.4,200.6 L434.6,199.5 L433.7,191.4 L430.2,190.7 L427.9,192.9 L424.6,193.1 L422.1,188.4 L413.2,188.2 L416.2,185.5 L418.4,186.5 L421.4,183.5 L422.3,179.7 L424.9,176.9 L426.9,167.1 L428.9,165.3 L435.2,167.4 L436.1,166.0 L442.1,164.8 L445.9,164.9 L448.1,166.9 L450.9,166.2 L454.0,171.3 L451.2,174.7 L449.4,182.0Z"/>
<path class="world-country" data-country="Somalia" d="M476.4,179.5 L475.1,177.8 L475.1,170.1 L477.6,167.0 L483.7,165.4 L492.2,155.9 L492.2,151.8 L496.9,150.5 L495.7,156.5 L491.5,164.6 L476.4,179.5Z"/>
<path class="world-country" data-country="Kenya" d="M471.3,185.9 L459.9,178.0 L462.3,171.9 L460.1,167.0 L462.9,164.3 L469.0,168.3 L477.0,167.7 L475.1,170.1 L475.1,177.8 L476.4,179.5 L473.6,181.4 L471.3,185.9Z"/>
<path class="world-country" data-country="Sudan" d="M439.8,158.5 L438.2,157.6 L437.4,157.0 L437.6,154.6 L434.2,149.3 L436.5,142.7 L438.4,142.9 L438.3,133.6 L440.8,133.6 L440.8,129.3 L466.3,129.3 L467.6,136.5 L469.6,137.8 L466.2,140.0 L465.0,147.2 L460.7,153.4 L460.0,157.5 L457.4,150.0 L454.4,155.2 L451.5,154.1 L449.3,156.0 L444.5,155.9 L440.9,154.2 L438.4,157.7 L439.8,158.5Z"/>
<path class="world-country" data-country="Chad" d="M438.3,134.4 L438.4,142.9 L436.5,142.7 L434.2,149.3 L436.2,152.3 L425.6,159.2 L419.9,160.2 L419.2,157.3 L417.0,155.7 L420.3,154.8 L418.4,147.7 L416.1,145.5 L419.8,140.7 L421.2,132.7 L418.9,127.5 L421.1,126.3 L438.3,134.4Z"/>
<path class="world-country" data-country="Haiti" d="M232.8,134.2 L232.8,137.7 L226.9,137.1 L231.5,136.4 L229.6,133.7 L232.8,134.2Z"/>
<path class="world-country" data-country="Dominican Rep." d="M233.5,138.7 L233.1,133.8 L240.1,136.5 L235.1,136.9 L233.5,138.7Z"/>
<path class="world-country" data-country="Russia" d="M771.3,25.2 L774.0,24.3 L774.0,25.8 L771.3,25.2Z M492.6,77.6 L487.4,81.4 L491.5,87.3 L489.8,88.7 L484.8,85.9 L472.9,83.9 L465.9,80.0 L469.2,77.9 L468.0,77.1 L471.2,76.2 L469.2,75.2 L472.4,74.4 L473.1,70.8 L463.0,68.7 L459.6,65.0 L455.3,65.5 L454.3,63.4 L457.3,62.9 L453.1,59.8 L453.4,58.2 L447.6,56.9 L445.7,54.1 L446.0,51.5 L449.6,48.7 L447.4,47.7 L454.8,42.7 L451.6,41.2 L452.5,39.8 L450.5,38.3 L452.0,36.5 L449.5,34.0 L451.5,32.4 L448.2,31.0 L448.5,29.5 L456.1,27.8 L475.3,33.0 L475.4,34.4 L469.5,36.0 L458.3,34.7 L461.9,36.3 L462.1,39.4 L466.6,40.6 L465.6,38.7 L466.9,37.9 L472.1,39.2 L473.9,38.7 L472.5,37.1 L477.5,35.0 L481.5,35.9 L482.7,34.4 L480.4,30.6 L486.4,31.3 L487.7,32.5 L484.9,32.7 L485.0,33.9 L486.7,34.6 L502.5,30.0 L504.1,30.1 L502.0,31.4 L513.4,29.9 L515.9,31.2 L518.3,29.8 L516.1,28.6 L517.2,27.9 L534.3,31.6 L535.7,30.5 L530.9,28.7 L530.4,25.4 L537.4,21.1 L543.1,21.7 L543.5,22.9 L541.5,24.6 L543.5,26.7 L543.0,29.6 L545.4,30.9 L540.3,35.4 L542.7,35.7 L548.4,32.3 L547.1,31.1 L548.1,29.7 L545.2,28.3 L547.0,26.2 L544.2,24.5 L548.0,23.1 L547.5,21.6 L549.7,22.7 L548.9,24.7 L551.2,25.1 L550.2,23.6 L553.8,22.8 L562.2,23.8 L560.1,19.8 L573.7,19.2 L571.9,18.1 L574.4,16.7 L603.6,13.9 L611.4,11.2 L617.6,13.8 L625.8,13.3 L632.4,15.2 L622.2,18.7 L630.0,19.1 L631.1,20.5 L635.5,19.6 L651.9,21.3 L652.0,19.6 L660.0,20.0 L663.5,21.1 L664.5,22.5 L663.2,23.4 L669.3,25.9 L671.3,23.7 L687.7,24.4 L686.2,22.4 L689.0,21.5 L708.4,22.9 L715.9,25.8 L728.8,25.7 L730.6,26.6 L730.4,28.1 L733.0,28.8 L747.8,28.4 L751.6,30.3 L754.3,29.7 L752.5,28.3 L753.5,27.4 L774.0,29.8 L774.0,38.2 L768.4,39.0 L772.6,42.4 L772.3,43.9 L760.4,45.3 L753.2,49.0 L750.1,47.5 L738.6,49.0 L735.3,52.5 L737.9,53.8 L737.6,56.9 L735.6,57.0 L734.7,58.8 L735.6,59.7 L731.8,60.8 L731.0,63.2 L727.8,63.7 L727.2,65.8 L724.1,67.8 L721.2,58.6 L722.2,55.6 L724.1,53.4 L727.5,52.9 L738.9,46.3 L740.6,43.4 L731.3,47.6 L729.5,45.0 L723.9,45.7 L718.6,49.3 L720.3,50.6 L712.2,51.3 L712.4,49.8 L709.0,49.5 L692.7,50.8 L677.5,59.9 L684.1,62.0 L687.8,61.1 L690.9,63.4 L688.1,73.3 L677.0,84.0 L674.1,85.2 L671.4,84.2 L668.2,86.5 L668.7,80.6 L673.2,80.3 L677.3,73.2 L668.6,74.6 L665.2,71.1 L661.5,70.5 L657.8,64.0 L652.7,62.6 L645.4,64.1 L646.6,65.8 L640.4,71.0 L632.9,69.4 L624.9,71.8 L620.2,71.5 L616.8,69.4 L609.9,69.8 L606.9,68.9 L606.4,67.3 L599.6,65.6 L596.1,70.5 L585.3,68.3 L574.8,71.6 L566.3,67.7 L560.2,67.0 L559.1,68.1 L551.5,61.1 L552.3,60.4 L544.9,62.6 L545.0,61.4 L540.0,61.2 L539.4,59.0 L535.5,58.5 L519.1,61.5 L518.1,62.2 L519.7,63.6 L515.9,65.8 L519.4,67.3 L518.9,68.3 L506.8,68.6 L496.1,66.4 L491.7,68.7 L491.4,70.2 L489.2,69.0 L486.9,73.4 L492.6,77.6Z M583.0,5.6 L593.3,3.7 L602.4,6.8 L601.9,8.7 L597.2,9.0 L583.0,5.6Z M604.7,8.0 L613.6,9.1 L600.8,10.8 L604.7,8.0Z M685.5,14.6 L691.2,14.6 L698.9,15.8 L697.2,17.3 L685.8,17.8 L681.5,16.4 L685.5,14.6Z M705.7,16.2 L711.1,16.8 L701.2,16.6 L705.7,16.2Z M687.7,20.4 L692.4,19.4 L695.7,20.7 L692.5,20.8 L687.7,20.4Z M483.4,5.1 L494.6,4.4 L497.8,4.9 L489.3,6.3 L483.4,5.1Z M435.9,60.8 L431.9,60.8 L429.3,60.6 L432.7,59.0 L435.9,59.7 L435.9,60.8Z M502.0,19.6 L507.2,17.7 L506.6,16.8 L518.5,14.3 L535.0,13.7 L512.7,18.4 L506.2,22.5 L506.6,24.3 L510.7,26.0 L497.9,24.4 L499.8,21.7 L504.0,19.9 L502.0,19.6Z M694.3,62.1 L698.0,72.1 L694.8,71.4 L693.5,74.5 L695.5,78.1 L693.9,76.9 L692.5,78.5 L691.6,63.0 L693.6,62.0 L692.8,61.0 L694.3,62.1Z M10.9,33.5 L12.2,35.3 L11.7,33.8 L17.5,34.1 L21.7,36.1 L16.1,37.2 L15.1,39.7 L3.5,37.3 L2.8,35.8 L0.2,36.3 L1.2,37.3 L0.0,38.2 L0.0,29.8 L10.9,33.5Z M5.2,24.9 L0.0,25.8 L0.0,24.3 L5.2,24.9Z M456.8,79.9 L459.5,78.0 L465.5,79.6 L459.8,81.9 L456.8,79.9Z"/>
<path class="world-country" data-country="Bahamas" d="M217.3,119.9 L219.6,119.1 L219.7,119.6 L217.3,119.9Z M219.8,118.6 L221.4,119.6 L221.1,121.1 L220.7,119.7 L219.8,118.6Z M218.4,123.9 L219.5,122.6 L220.3,125.6 L218.4,123.9Z"/>
<path class="world-country" data-country="Falkland Is." d="M255.4,285.9 L261.1,284.3 L262.8,285.2 L259.3,286.6 L255.4,285.9Z"/>
<path class="world-country" data-country="Norway" d="M409.5,7.1 L423.5,6.3 L433.3,8.6 L427.9,9.4 L423.8,13.1 L421.2,13.2 L416.6,11.9 L418.5,11.2 L409.5,7.1Z M453.9,28.5 L448.5,29.5 L449.4,28.1 L446.6,27.2 L440.2,30.4 L432.7,28.9 L430.1,29.5 L429.7,30.9 L425.7,30.6 L416.1,38.6 L416.2,40.2 L414.0,40.1 L412.7,42.1 L414.2,46.0 L413.4,48.5 L410.7,51.2 L409.3,49.9 L405.0,52.3 L399.2,51.8 L397.7,44.6 L409.6,39.2 L418.7,32.2 L428.2,27.9 L447.6,25.0 L454.3,26.6 L451.5,27.2 L453.9,28.5Z M445.9,6.2 L436.5,7.6 L424.3,5.7 L436.3,5.0 L445.9,6.2Z M440.2,10.9 L435.4,11.8 L431.6,11.3 L433.0,10.7 L431.7,10.1 L436.2,9.6 L440.2,10.9Z"/>
<path class="world-country" data-country="Greenland" d="M286.5,0.8 L304.0,-1.2 L328.7,-1.1 L342.2,0.6 L318.4,1.7 L339.5,2.7 L337.2,3.9 L353.1,2.3 L360.8,3.6 L343.9,6.0 L348.9,6.1 L344.6,9.0 L344.7,11.4 L347.3,12.8 L340.4,13.5 L344.4,14.6 L344.9,16.4 L342.6,16.6 L345.3,18.5 L340.6,18.6 L343.1,19.5 L342.4,20.2 L336.3,20.5 L339.1,22.9 L333.7,22.6 L339.4,24.4 L340.2,26.2 L336.4,26.6 L332.1,24.5 L332.8,26.0 L330.3,27.1 L338.9,27.3 L327.3,30.8 L318.7,31.5 L313.5,34.6 L301.4,37.2 L298.4,41.4 L294.9,43.1 L295.8,44.7 L293.7,48.6 L283.2,46.9 L276.0,41.1 L271.0,33.5 L273.1,31.0 L276.3,30.3 L277.6,27.7 L269.4,28.4 L270.1,25.8 L276.5,26.4 L267.0,24.1 L269.4,22.1 L261.0,15.9 L239.7,14.7 L233.5,12.7 L243.5,11.9 L229.4,10.5 L245.7,7.6 L246.6,6.9 L240.8,6.1 L253.2,3.6 L252.3,2.6 L278.7,1.2 L291.3,2.8 L286.5,0.8Z"/>
<path class="world-country" data-country="Fr. S. Antarctic Lands" d="M535.2,279.0 L538.6,280.0 L538.7,280.4 L534.8,281.5 L535.2,279.0Z"/>
<path class="world-country" data-country="Timor-Leste" d="M655.9,195.9 L657.8,193.8 L660.8,193.8 L655.9,195.9Z"/>
<path class="world-country" data-country="South Africa" d="M422.1,236.5 L423.2,235.5 L426.7,237.5 L429.8,236.3 L429.8,228.5 L431.9,232.8 L433.5,232.6 L437.1,229.5 L442.2,230.0 L450.3,222.8 L454.1,223.1 L455.7,227.6 L455.5,230.7 L453.7,230.5 L453.0,232.7 L454.3,233.8 L457.6,232.7 L456.2,236.9 L447.7,245.4 L442.4,247.9 L435.5,247.8 L430.2,249.7 L426.5,248.3 L426.2,243.1 L422.1,236.5Z"/>
<path class="world-country" data-country="Lesotho" d="M449.3,237.3 L447.4,240.7 L445.0,239.3 L447.4,237.1 L449.3,237.3Z"/>
<path class="world-country" data-country="Mexico" d="M135.2,107.0 L140.3,106.6 L148.3,109.5 L158.0,108.6 L163.5,113.9 L165.3,114.5 L168.4,112.8 L174.1,120.1 L178.1,121.1 L176.6,128.4 L180.8,136.0 L184.0,137.5 L190.5,135.9 L192.9,131.4 L199.8,130.3 L198.2,137.2 L191.3,138.2 L190.4,139.4 L192.5,141.9 L189.7,141.9 L188.7,145.1 L185.2,142.2 L179.4,142.8 L164.5,137.2 L160.2,133.7 L160.7,130.5 L159.0,127.7 L145.7,114.6 L143.7,109.9 L139.9,109.4 L149.1,124.4 L151.8,126.4 L150.8,127.6 L145.8,123.5 L145.6,120.8 L139.6,117.2 L141.6,115.4 L138.6,113.3 L135.2,107.0Z"/>
<path class="world-country" data-country="Uruguay" d="M263.1,240.0 L271.4,243.9 L272.6,245.3 L271.3,248.9 L266.1,249.9 L261.4,247.8 L263.1,240.0Z"/>
<path class="world-country" data-country="Brazil" d="M272.2,247.5 L271.4,243.9 L263.1,240.0 L271.7,233.0 L271.7,231.3 L269.6,230.5 L270.3,226.9 L267.9,226.7 L267.0,223.4 L262.4,222.8 L263.4,214.5 L261.8,210.5 L257.7,210.4 L256.9,205.2 L246.4,200.5 L246.5,196.7 L240.2,199.3 L235.3,199.3 L235.5,196.1 L231.8,197.3 L229.6,196.0 L227.9,191.9 L230.3,187.1 L236.7,185.1 L237.7,178.3 L236.5,174.8 L238.2,173.9 L236.9,172.3 L241.8,171.6 L242.8,173.6 L246.1,174.3 L250.8,171.3 L248.8,170.7 L247.6,167.4 L251.3,168.0 L256.4,164.9 L258.0,165.3 L258.1,170.1 L260.1,173.2 L266.6,172.1 L266.7,170.6 L273.2,171.5 L276.7,167.0 L279.6,172.3 L278.7,176.1 L282.5,176.5 L282.5,178.6 L284.2,177.2 L290.5,179.2 L291.1,181.7 L301.0,182.1 L307.0,186.2 L310.5,186.9 L312.3,191.5 L311.5,195.0 L303.9,203.6 L302.6,213.8 L299.0,222.5 L296.7,224.7 L291.0,225.5 L284.6,228.7 L282.7,230.8 L281.9,236.7 L272.2,247.5Z"/>
<path class="world-country" data-country="Bolivia" d="M237.5,199.2 L246.5,196.7 L246.4,200.5 L256.9,205.2 L257.7,210.4 L261.8,210.5 L263.4,214.5 L262.6,218.3 L259.9,217.0 L254.2,217.6 L252.2,223.1 L249.4,222.6 L248.6,224.3 L244.5,222.2 L241.2,224.5 L239.2,219.2 L239.8,217.1 L237.4,213.2 L239.4,202.6 L237.5,199.2Z"/>
<path class="world-country" data-country="Peru" d="M236.7,185.1 L230.3,187.1 L227.9,191.9 L229.6,196.0 L231.8,197.3 L235.5,196.1 L235.3,199.3 L237.5,199.2 L239.4,202.6 L237.9,207.7 L238.7,210.9 L235.7,214.9 L223.6,207.0 L215.5,191.2 L212.3,189.0 L212.0,186.0 L214.3,183.2 L214.0,185.3 L217.9,185.6 L219.6,182.3 L224.6,179.3 L225.5,176.1 L229.9,180.9 L236.4,181.7 L235.0,183.9 L236.7,185.1Z"/>
<path class="world-country" data-country="Colombia" d="M243.2,173.3 L241.8,171.6 L236.9,172.3 L238.2,173.9 L236.5,174.8 L237.7,178.3 L236.7,185.1 L235.0,183.9 L236.4,181.7 L229.9,180.9 L225.5,176.1 L220.5,175.1 L217.2,172.4 L221.2,167.8 L219.6,160.6 L220.4,157.9 L224.3,155.9 L226.0,152.5 L233.5,149.7 L229.4,156.6 L232.3,161.1 L242.2,163.0 L241.2,170.0 L243.2,173.3Z"/>
<path class="world-country" data-country="Panama" d="M220.7,157.6 L219.6,160.6 L216.9,156.9 L213.1,160.7 L211.3,158.8 L208.9,158.8 L208.7,155.9 L211.9,157.3 L217.1,155.7 L220.7,157.6Z"/>
<path class="world-country" data-country="Costa Rica" d="M209.5,155.7 L208.6,158.5 L204.3,154.6 L204.0,155.7 L202.8,154.9 L202.2,152.9 L207.1,152.8 L209.5,155.7Z"/>
<path class="world-country" data-country="Nicaragua" d="M207.1,152.8 L202.7,152.5 L198.5,148.6 L204.4,144.6 L208.2,144.2 L207.1,152.8Z"/>
<path class="world-country" data-country="Honduras" d="M208.2,144.2 L204.4,144.6 L199.3,148.4 L194.9,145.4 L198.0,142.3 L204.3,142.0 L208.2,144.2Z"/>
<path class="world-country" data-country="El Salvador" d="M194.9,145.4 L198.4,146.7 L198.0,148.1 L193.3,146.8 L194.9,145.4Z"/>
<path class="world-country" data-country="Guatemala" d="M188.7,145.1 L189.7,141.9 L192.5,141.9 L190.4,139.4 L191.3,138.2 L195.3,138.2 L195.2,142.3 L197.3,142.6 L194.9,145.4 L193.3,146.8 L188.7,145.1Z"/>
<path class="world-country" data-country="Belize" d="M195.3,138.2 L197.6,137.1 L195.8,142.3 L195.2,142.3 L195.3,138.2Z"/>
<path class="world-country" data-country="Venezuela" d="M256.4,164.9 L251.3,168.0 L247.6,167.4 L248.8,170.7 L250.8,171.3 L244.4,174.4 L241.2,170.0 L242.2,163.0 L232.3,161.1 L229.4,156.6 L230.3,153.8 L232.3,151.3 L233.6,151.0 L232.0,155.0 L233.8,156.6 L233.5,152.7 L236.2,151.8 L236.6,150.2 L240.4,153.6 L247.5,154.6 L254.0,153.2 L252.1,153.9 L258.5,158.2 L255.0,163.3 L256.4,164.9Z"/>
<path class="world-country" data-country="Guyana" d="M265.4,171.9 L261.1,173.3 L258.8,172.2 L258.0,165.3 L255.0,163.3 L258.5,158.2 L264.1,163.3 L262.2,167.4 L265.4,171.9Z"/>
<path class="world-country" data-country="Suriname" d="M269.8,171.1 L266.7,170.6 L266.6,172.1 L265.4,171.9 L263.2,168.9 L262.2,167.4 L264.1,163.3 L271.0,163.8 L269.8,171.1Z"/>
<path class="world-country" data-country="France" d="M275.9,167.1 L273.2,171.5 L269.8,171.1 L271.0,163.8 L275.9,167.1Z M392.4,67.5 L404.4,72.0 L403.1,75.0 L400.0,76.9 L403.0,83.3 L390.9,86.2 L382.9,83.9 L384.4,78.4 L377.3,74.3 L377.1,72.7 L383.5,72.8 L382.8,70.4 L384.9,71.3 L392.4,67.5Z M405.9,87.8 L407.2,84.8 L406.8,88.2 L405.9,87.8Z"/>
<path class="world-country" data-country="Ecuador" d="M224.9,176.3 L224.6,179.3 L219.6,182.3 L217.9,185.6 L214.0,185.3 L215.5,181.6 L212.9,180.7 L213.0,178.2 L214.8,174.3 L217.5,173.0 L224.9,176.3Z"/>
<path class="world-country" data-country="Puerto Rico" d="M242.7,136.7 L246.0,137.3 L242.6,137.9 L242.7,136.7Z"/>
<path class="world-country" data-country="Jamaica" d="M218.6,137.3 L221.7,137.0 L223.2,138.0 L218.6,137.3Z"/>
<path class="world-country" data-country="Cuba" d="M210.1,126.8 L218.6,128.2 L227.5,133.0 L219.8,133.9 L221.3,132.7 L217.8,130.2 L210.3,128.5 L211.1,128.0 L204.3,129.5 L210.1,126.8Z"/>
<path class="world-country" data-country="Zimbabwe" d="M454.1,223.1 L447.2,221.5 L441.3,213.6 L445.1,214.0 L452.1,208.8 L457.6,211.4 L457.2,219.0 L454.1,223.1Z"/>
<path class="world-country" data-country="Botswana" d="M450.3,222.8 L442.2,230.0 L437.1,229.5 L433.5,232.6 L431.9,232.8 L429.8,228.5 L429.8,222.3 L431.9,222.2 L432.0,214.7 L441.3,213.6 L447.2,221.5 L450.3,222.8Z"/>
<path class="world-country" data-country="Namibia" d="M429.8,222.3 L429.8,236.3 L426.7,237.5 L423.2,235.5 L422.1,236.5 L419.7,233.4 L417.7,222.8 L412.2,212.6 L440.9,213.2 L437.7,214.7 L432.0,214.7 L431.9,222.2 L429.8,222.3Z"/>
<path class="world-country" data-country="Senegal" d="M351.1,147.1 L349.1,144.7 L352.3,141.1 L355.7,140.8 L360.8,145.0 L362.2,149.6 L351.1,149.7 L350.8,148.1 L357.2,147.3 L351.1,147.1Z"/>
<path class="world-country" data-country="Mali" d="M362.2,149.6 L360.8,145.0 L361.9,143.3 L375.1,143.1 L373.1,123.1 L376.4,123.0 L393.8,134.2 L393.8,135.6 L396.2,135.4 L394.8,143.0 L384.7,144.2 L378.4,147.4 L375.4,154.0 L369.7,154.3 L367.4,149.9 L365.1,150.9 L362.2,149.6Z"/>
<path class="world-country" data-country="Mauritania" d="M350.3,131.4 L359.2,130.7 L359.3,126.6 L361.3,126.4 L361.3,121.0 L368.3,121.1 L368.3,117.9 L376.4,123.0 L373.1,123.1 L375.1,143.1 L361.9,143.3 L360.8,145.0 L355.7,140.8 L351.6,141.8 L352.0,133.4 L350.3,131.4Z"/>
<path class="world-country" data-country="Benin" d="M392.8,162.7 L391.0,162.9 L390.6,156.6 L388.7,153.8 L393.1,150.0 L395.2,153.2 L392.9,157.9 L392.8,162.7Z"/>
<path class="world-country" data-country="Niger" d="M418.9,127.5 L421.2,132.7 L419.8,140.7 L416.1,145.5 L418.4,147.7 L417.5,149.5 L415.1,147.1 L406.4,148.8 L398.7,146.6 L395.8,147.3 L394.8,151.2 L389.2,148.7 L387.8,144.3 L394.8,143.0 L396.2,135.4 L412.8,126.2 L417.4,128.3 L418.9,127.5Z"/>
<path class="world-country" data-country="Nigeria" d="M392.8,162.7 L392.9,157.9 L395.0,154.6 L394.9,149.3 L396.4,146.8 L406.4,148.8 L415.1,147.1 L418.3,150.3 L412.3,161.2 L406.9,162.3 L405.3,165.8 L399.7,166.9 L396.3,162.7 L392.8,162.7Z"/>
<path class="world-country" data-country="Cameroon" d="M418.2,148.7 L420.3,154.8 L417.0,155.7 L420.2,159.7 L418.1,165.9 L421.1,169.6 L421.3,172.3 L407.7,171.1 L408.1,169.4 L405.3,166.4 L405.8,164.3 L408.8,161.0 L412.3,161.2 L418.0,151.4 L418.2,148.7Z"/>
<path class="world-country" data-country="Togo" d="M388.9,152.6 L391.0,162.9 L389.3,163.4 L386.9,153.3 L388.9,152.6Z"/>
<path class="world-country" data-country="Ghana" d="M387.1,152.6 L389.3,163.4 L382.8,166.0 L380.9,165.4 L380.7,152.7 L387.1,152.6Z"/>
<path class="world-country" data-country="Côte d&#x27;Ivoire" d="M369.7,154.3 L373.7,153.6 L380.9,155.5 L380.9,165.4 L370.4,166.7 L370.7,163.9 L368.5,162.2 L369.7,154.3Z"/>
<path class="world-country" data-country="Guinea" d="M357.5,149.3 L365.1,150.9 L367.4,149.9 L369.7,154.3 L369.2,159.7 L367.2,160.5 L366.0,157.9 L364.4,158.3 L363.1,154.7 L358.5,157.1 L354.5,152.6 L357.5,150.9 L357.5,149.3Z"/>
<path class="world-country" data-country="Guinea-Bissau" d="M351.1,149.7 L357.5,149.3 L357.5,150.9 L354.5,152.6 L351.1,149.7Z"/>
<path class="world-country" data-country="Liberia" d="M368.9,159.7 L368.5,162.2 L370.7,163.9 L370.4,166.7 L362.4,161.6 L365.0,158.1 L367.2,160.5 L368.9,159.7Z"/>
<path class="world-country" data-country="Sierra Leone" d="M358.5,157.1 L363.1,154.7 L365.0,158.1 L362.4,161.6 L359.2,159.4 L358.5,157.1Z"/>
<path class="world-country" data-country="Burkina Faso" d="M375.4,154.0 L377.8,147.9 L384.7,144.2 L387.8,144.3 L389.2,148.7 L391.7,149.2 L388.9,152.6 L380.7,152.7 L380.9,155.5 L375.4,154.0Z"/>
<path class="world-country" data-country="Central African Rep." d="M445.9,164.9 L439.5,165.1 L435.2,167.4 L428.9,165.3 L426.7,168.5 L423.8,168.1 L421.4,171.2 L418.1,164.4 L419.9,160.2 L425.6,159.2 L436.2,152.3 L437.4,157.0 L445.9,164.9Z"/>
<path class="world-country" data-country="Congo" d="M426.7,168.5 L424.9,176.9 L422.3,179.7 L421.4,183.5 L418.4,186.5 L414.1,185.4 L412.6,186.6 L410.9,184.4 L412.5,183.2 L411.7,181.8 L414.0,180.1 L417.1,181.2 L418.0,178.8 L416.8,175.9 L417.7,173.4 L415.6,173.2 L415.1,171.2 L421.3,172.3 L423.8,168.1 L426.7,168.5Z"/>
<path class="world-country" data-country="Gabon" d="M411.2,171.2 L414.8,171.0 L415.6,173.2 L417.7,173.4 L416.8,175.9 L418.0,178.8 L417.1,181.2 L414.0,180.1 L411.7,181.8 L412.5,183.2 L410.9,184.4 L405.9,178.3 L407.4,173.8 L411.3,173.7 L411.2,171.2Z"/>
<path class="world-country" data-country="Eq. Guinea" d="M407.7,171.1 L411.2,171.2 L411.3,173.7 L407.4,173.8 L407.7,171.1Z"/>
<path class="world-country" data-country="Zambia" d="M453.1,193.6 L458.4,196.5 L457.3,205.0 L458.4,205.6 L451.9,207.3 L452.1,208.8 L445.1,214.0 L436.9,213.1 L434.1,210.1 L434.2,203.3 L438.6,203.3 L438.4,199.1 L442.4,200.9 L445.4,200.6 L450.9,204.1 L450.7,201.8 L448.0,201.0 L448.2,195.4 L449.4,193.8 L453.1,193.6Z"/>
<path class="world-country" data-country="Malawi" d="M457.4,195.5 L460.7,197.5 L461.3,204.7 L463.7,206.9 L462.3,211.6 L460.9,210.3 L461.1,206.9 L457.3,205.0 L459.0,198.3 L457.4,195.5Z"/>
<path class="world-country" data-country="Mozambique" d="M461.3,200.4 L467.6,200.5 L473.7,197.8 L474.7,207.1 L471.8,211.4 L461.8,217.9 L463.2,227.1 L458.0,229.7 L457.6,232.7 L456.0,232.6 L454.1,223.1 L457.2,219.0 L457.6,211.4 L452.2,209.6 L451.9,207.3 L458.4,205.6 L461.1,206.9 L460.9,210.3 L462.3,211.6 L463.7,206.9 L461.3,204.7 L461.3,200.4Z"/>
<path class="world-country" data-country="eSwatini" d="M456.0,232.6 L454.3,233.8 L453.0,232.7 L453.7,230.5 L455.5,230.7 L456.0,232.6Z"/>
<path class="world-country" data-country="Angola" d="M412.6,186.6 L414.2,186.5 L413.2,188.2 L412.6,186.6Z M413.5,188.9 L422.1,188.4 L424.6,193.1 L427.9,192.9 L430.2,190.7 L433.7,191.4 L434.6,199.5 L438.6,199.8 L438.6,203.3 L434.2,203.3 L434.1,210.1 L436.9,213.1 L412.2,212.6 L413.2,206.6 L416.5,199.9 L413.5,188.9Z"/>
<path class="world-country" data-country="Burundi" d="M452.5,181.1 L453.1,183.1 L450.1,185.5 L449.4,182.0 L452.5,181.1Z"/>
<path class="world-country" data-country="Israel" d="M464.0,105.4 L462.2,108.4 L463.2,110.0 L462.1,113.4 L460.7,109.8 L462.5,105.8 L464.0,105.4Z"/>
<path class="world-country" data-country="Lebanon" d="M465.7,103.5 L462.5,105.8 L465.4,102.6 L465.7,103.5Z"/>
<path class="world-country" data-country="Madagascar" d="M492.8,201.5 L495.3,209.3 L493.8,209.3 L488.3,228.8 L484.6,230.2 L481.7,228.9 L480.2,224.2 L482.6,217.2 L481.5,212.9 L482.6,210.3 L486.6,209.4 L492.8,201.5Z"/>
<path class="world-country" data-country="Palestine" d="M463.4,107.3 L462.1,109.5 L462.6,107.0 L463.4,107.3Z"/>
<path class="world-country" data-country="Gambia" d="M350.8,148.1 L354.6,146.5 L357.2,147.3 L350.8,148.1Z"/>
<path class="world-country" data-country="Tunisia" d="M407.4,111.7 L403.2,103.7 L405.1,97.6 L407.4,96.8 L408.9,98.1 L410.7,97.3 L410.2,102.1 L408.8,103.2 L411.7,105.7 L407.4,111.7Z"/>
<path class="world-country" data-country="Algeria" d="M368.3,117.9 L368.4,114.8 L384.2,107.6 L382.3,101.4 L384.4,100.2 L390.2,98.4 L405.1,97.6 L403.2,103.7 L406.5,107.9 L408.1,113.6 L407.0,120.6 L409.2,124.3 L412.8,126.2 L399.2,134.4 L393.8,135.6 L393.8,134.2 L368.3,117.9Z"/>
<path class="world-country" data-country="Jordan" d="M463.4,107.3 L466.2,107.5 L470.4,105.2 L471.3,107.8 L466.6,109.2 L468.7,111.3 L464.5,114.1 L462.1,113.4 L463.4,107.3Z"/>
<path class="world-country" data-country="United Arab Emirates" d="M497.9,124.6 L503.1,124.8 L508.0,121.4 L505.3,128.3 L498.8,127.2 L497.9,124.6Z"/>
<path class="world-country" data-country="Qatar" d="M496.2,123.5 L496.1,121.9 L497.3,120.6 L498.0,122.5 L496.2,123.5Z"/>
<path class="world-country" data-country="Kuwait" d="M490.1,112.4 L491.1,115.4 L487.1,114.3 L488.7,112.2 L490.1,112.4Z"/>
<path class="world-country" data-country="Iraq" d="M471.3,107.8 L470.4,105.2 L475.2,103.0 L475.8,98.9 L479.0,96.7 L483.3,97.2 L486.1,100.3 L484.6,103.9 L488.8,107.1 L491.4,112.5 L483.1,114.1 L471.3,107.8Z"/>
<path class="world-country" data-country="Oman" d="M505.7,127.8 L508.3,123.1 L515.6,128.7 L511.3,133.0 L511.0,135.8 L504.8,140.0 L501.2,140.7 L498.8,135.7 L505.2,133.6 L506.7,129.3 L505.7,127.8Z"/>
<path class="world-country" data-country="Vanuatu" d="M746.5,209.7 L747.9,210.9 L747.2,211.1 L746.5,209.7Z M746.6,209.3 L745.3,208.6 L745.3,207.0 L746.6,209.3Z"/>
<path class="world-country" data-country="Cambodia" d="M609.5,153.4 L607.0,147.6 L608.4,145.8 L615.0,146.5 L616.0,145.1 L618.4,147.3 L618.1,149.8 L614.5,151.4 L615.4,152.7 L609.5,153.4Z"/>
<path class="world-country" data-country="Thailand" d="M613.2,145.7 L608.4,145.8 L607.0,147.6 L607.6,150.1 L602.2,147.5 L600.3,156.4 L606.6,162.8 L604.5,163.9 L598.0,158.3 L601.1,150.7 L598.1,143.9 L599.6,141.7 L596.4,136.9 L598.2,134.2 L602.2,132.7 L604.8,134.7 L604.3,138.8 L608.9,137.1 L612.1,139.0 L614.0,143.0 L613.2,145.7Z"/>
<path class="world-country" data-country="Laos" d="M617.9,145.9 L613.2,145.7 L614.0,143.0 L610.5,137.3 L604.3,138.8 L604.8,134.7 L602.2,132.7 L604.5,130.5 L605.9,131.1 L605.6,128.6 L606.7,128.3 L608.9,131.9 L611.5,132.0 L612.4,133.8 L610.4,135.1 L617.7,142.2 L617.9,145.9Z"/>
<path class="world-country" data-country="Myanmar" d="M602.2,132.7 L598.2,134.2 L596.4,136.9 L599.6,141.7 L598.1,143.9 L601.1,150.7 L598.9,154.9 L598.8,148.1 L595.9,140.1 L592.0,142.6 L589.5,142.0 L589.8,137.3 L585.5,130.4 L591.5,119.6 L595.8,118.5 L596.3,116.0 L599.2,117.6 L596.9,125.3 L599.1,124.9 L601.0,127.3 L600.4,129.1 L604.5,129.6 L602.2,132.7Z"/>
<path class="world-country" data-country="Vietnam" d="M611.3,153.7 L615.4,152.7 L614.5,151.4 L618.1,149.8 L618.3,143.7 L613.0,136.4 L610.4,135.1 L612.4,133.8 L611.5,132.0 L608.9,131.9 L606.7,128.3 L613.5,126.5 L619.3,130.3 L614.2,135.6 L621.1,143.6 L621.8,151.2 L613.1,157.7 L612.9,154.9 L611.3,153.7Z"/>
<path class="world-country" data-country="North Korea" d="M667.9,86.1 L665.9,89.3 L661.2,91.7 L662.6,94.6 L656.3,96.1 L655.1,95.2 L656.6,92.5 L654.2,91.3 L655.9,90.0 L659.8,87.3 L662.6,88.1 L662.3,86.9 L666.5,84.8 L667.9,86.1Z"/>
<path class="world-country" data-country="South Korea" d="M658.3,95.9 L663.0,94.1 L665.3,98.0 L664.5,101.6 L658.9,103.1 L658.2,98.1 L659.7,97.7 L658.3,95.9Z"/>
<path class="world-country" data-country="Mongolia" d="M575.7,71.4 L585.3,68.3 L596.1,70.5 L599.6,65.6 L606.4,67.3 L606.9,68.9 L609.9,69.8 L616.8,69.4 L620.2,71.5 L624.9,71.8 L632.9,69.4 L637.9,70.2 L635.8,74.8 L640.8,74.1 L644.5,76.2 L630.9,81.0 L627.5,80.3 L626.4,81.7 L627.4,83.2 L624.4,85.1 L612.7,87.8 L603.8,85.5 L594.2,85.4 L591.9,82.2 L582.5,80.0 L582.6,76.6 L575.7,71.4Z"/>
<path class="world-country target" data-country="India" data-score="56" d="M596.3,116.0 L595.8,118.5 L591.5,119.6 L586.2,129.2 L585.1,125.9 L584.2,127.2 L583.0,126.1 L585.6,123.0 L580.3,122.4 L580.1,120.9 L577.4,119.9 L576.7,121.3 L578.2,122.5 L576.4,124.0 L577.7,124.6 L578.1,130.0 L574.0,130.4 L573.0,133.2 L563.7,140.9 L559.7,142.3 L558.7,154.0 L553.7,159.1 L545.1,142.1 L543.2,130.7 L538.5,131.7 L533.6,125.7 L535.0,124.3 L539.7,124.3 L536.5,118.8 L538.8,116.6 L541.3,116.8 L548.8,107.5 L545.6,103.2 L552.3,102.5 L554.4,100.7 L556.7,103.2 L556.3,109.1 L561.4,112.0 L559.2,114.9 L566.1,117.9 L576.3,120.0 L576.5,116.9 L577.8,116.4 L578.0,118.5 L580.0,119.3 L584.9,119.1 L584.1,117.1 L593.7,113.5 L593.9,115.7 L596.3,116.0Z"/>
<path class="world-country" data-country="Bangladesh" d="M585.1,125.9 L585.6,132.1 L583.5,127.7 L581.6,127.6 L581.1,129.7 L578.4,129.2 L577.7,124.6 L576.4,124.0 L578.2,122.5 L576.7,121.3 L577.4,119.9 L580.1,120.9 L580.3,122.4 L585.6,123.0 L583.0,126.1 L584.2,127.2 L585.1,125.9Z"/>
<path class="world-country" data-country="Bhutan" d="M584.1,117.1 L584.9,119.1 L578.0,118.5 L580.5,116.0 L584.1,117.1Z"/>
<path class="world-country" data-country="Nepal" d="M576.5,116.9 L576.3,120.0 L574.5,120.0 L559.2,114.9 L562.3,111.5 L571.5,116.2 L576.5,116.9Z"/>
<path class="world-country" data-country="Pakistan" d="M554.4,100.7 L552.3,102.5 L545.6,103.2 L548.8,107.5 L541.3,116.8 L538.8,116.6 L536.5,118.8 L539.7,124.3 L535.0,124.3 L533.6,125.7 L529.7,122.1 L519.2,122.8 L520.0,120.3 L523.1,119.2 L521.9,116.0 L517.9,112.7 L521.5,113.8 L529.6,112.6 L530.9,109.6 L536.0,108.3 L538.2,105.2 L537.4,103.8 L539.4,103.9 L541.5,98.6 L548.6,97.2 L550.8,99.9 L554.4,100.7Z"/>
<path class="world-country" data-country="Afghanistan" d="M526.2,97.3 L535.8,97.2 L539.2,94.4 L541.5,98.1 L544.5,96.5 L548.6,97.2 L540.2,99.5 L541.0,101.4 L539.4,103.9 L537.4,103.8 L538.2,105.2 L536.0,108.3 L530.9,109.6 L529.6,112.6 L521.5,113.8 L517.9,112.7 L519.8,110.8 L517.2,106.0 L518.6,100.4 L522.4,100.9 L526.2,97.3Z"/>
<path class="world-country" data-country="Tajikistan" d="M532.8,97.2 L534.0,95.1 L532.6,92.0 L538.9,89.1 L539.7,90.6 L536.6,90.9 L536.3,92.2 L545.4,92.4 L548.2,96.6 L541.5,98.1 L539.2,94.4 L535.8,97.2 L532.8,97.2Z"/>
<path class="world-country" data-country="Kyrgyzstan" d="M538.4,87.9 L541.5,85.1 L545.0,85.9 L546.6,84.2 L559.6,86.2 L545.4,92.4 L536.3,92.2 L536.6,90.9 L544.1,89.3 L538.4,87.9Z"/>
<path class="world-country" data-country="Turkmenistan" d="M499.9,87.4 L503.3,86.2 L506.2,88.5 L509.8,88.4 L509.4,87.3 L513.1,85.3 L530.1,95.5 L530.0,96.8 L528.4,96.1 L520.8,101.2 L518.6,100.4 L518.4,98.6 L510.3,95.3 L502.9,97.1 L502.8,93.4 L500.3,91.1 L500.8,89.3 L504.7,89.1 L502.5,86.7 L500.6,88.8 L499.9,87.4Z"/>
<path class="world-country" data-country="Iran" d="M491.4,112.5 L488.8,107.1 L484.6,103.9 L486.1,100.3 L482.1,95.5 L481.8,92.4 L483.3,91.8 L486.2,93.8 L490.3,92.0 L492.8,96.3 L496.3,97.8 L502.7,97.6 L508.7,95.1 L518.4,98.6 L517.2,106.0 L519.8,110.8 L517.9,112.7 L521.9,116.0 L523.1,119.2 L520.0,120.3 L519.2,122.8 L510.4,121.4 L509.5,118.8 L502.0,119.1 L497.8,116.9 L494.7,112.0 L491.4,112.5Z"/>
<path class="world-country" data-country="Syria" d="M463.8,106.6 L465.7,103.5 L464.2,100.9 L466.0,97.9 L478.1,97.0 L475.8,98.9 L475.2,103.0 L466.2,107.5 L463.8,106.6Z"/>
<path class="world-country" data-country="Armenia" d="M487.0,93.8 L480.9,90.6 L480.7,88.8 L485.0,89.4 L487.0,93.8Z"/>
<path class="world-country" data-country="Sweden" d="M410.7,51.2 L414.2,46.0 L412.7,42.1 L414.0,40.1 L416.2,40.2 L416.1,38.6 L423.1,31.8 L429.7,30.9 L431.4,29.5 L437.6,31.9 L438.4,36.0 L434.7,36.6 L432.6,38.1 L432.9,39.4 L425.4,42.9 L423.8,45.9 L427.4,48.6 L423.2,51.5 L421.1,57.0 L414.8,58.6 L410.7,51.2Z"/>
<path class="world-country" data-country="Belarus" d="M447.6,56.9 L453.4,58.2 L453.1,59.8 L457.3,62.9 L454.3,63.4 L455.3,65.5 L452.7,67.2 L437.6,66.6 L437.5,61.7 L441.9,60.9 L444.0,58.1 L447.6,56.9Z"/>
<path class="world-country" data-country="Ukraine" d="M452.7,67.2 L459.6,65.0 L463.0,68.7 L473.1,70.8 L472.4,74.4 L462.2,77.9 L462.3,79.0 L455.1,76.9 L448.7,79.9 L447.7,79.5 L449.1,77.5 L451.6,77.5 L448.6,73.9 L446.2,73.2 L440.5,74.8 L434.5,73.3 L438.4,69.1 L437.6,66.6 L452.7,67.2Z"/>
<path class="world-country" data-country="Poland" d="M437.5,61.7 L438.2,64.3 L436.9,64.7 L438.7,68.5 L435.4,71.1 L436.0,72.0 L421.8,69.1 L419.3,67.6 L417.3,63.6 L417.4,62.0 L424.9,59.7 L437.5,61.7Z"/>
<path class="world-country" data-country="Austria" d="M423.5,73.9 L421.4,77.0 L418.5,77.5 L407.4,76.1 L414.8,75.3 L416.2,72.3 L422.5,72.5 L423.5,73.9Z"/>
<path class="world-country" data-country="Hungary" d="M434.5,73.3 L435.8,74.4 L432.2,77.8 L426.7,78.9 L421.8,76.6 L423.5,73.9 L434.5,73.3Z"/>
<path class="world-country" data-country="Moldova" d="M444.2,73.7 L448.6,73.9 L451.6,77.5 L449.1,77.5 L447.7,79.5 L447.5,76.7 L444.2,73.7Z"/>
<path class="world-country" data-country="Romania" d="M447.7,79.5 L450.6,79.9 L448.4,83.3 L436.3,83.1 L430.5,78.2 L436.8,74.0 L444.2,73.7 L447.5,76.7 L447.7,79.5Z"/>
<path class="world-country" data-country="Lithuania" d="M444.0,58.1 L441.9,60.9 L437.5,61.7 L435.9,59.7 L432.7,59.0 L432.3,57.2 L440.5,56.5 L444.0,58.1Z"/>
<path class="world-country" data-country="Latvia" d="M445.7,54.1 L447.6,56.9 L444.0,58.1 L440.5,56.5 L432.3,57.2 L433.4,54.2 L435.4,53.5 L437.1,55.1 L441.1,53.1 L445.7,54.1Z"/>
<path class="world-country" data-country="Estonia" d="M447.2,49.9 L445.7,54.1 L439.3,53.4 L437.2,50.5 L447.2,49.9Z"/>
<path class="world-country" data-country="Germany" d="M417.4,62.0 L419.3,67.6 L413.3,69.4 L416.2,72.3 L414.8,75.3 L403.1,75.0 L404.4,72.0 L401.3,71.7 L400.0,69.7 L399.9,66.0 L401.7,65.2 L402.3,62.1 L404.5,62.5 L405.9,61.4 L405.3,59.4 L408.3,59.4 L410.5,61.5 L413.9,60.5 L417.4,62.0Z"/>
<path class="world-country" data-country="Bulgaria" d="M435.7,82.2 L436.3,83.1 L448.4,83.3 L446.5,85.7 L447.2,86.9 L436.3,88.3 L435.1,86.2 L436.4,84.4 L435.7,82.2Z"/>
<path class="world-country" data-country="Greece" d="M443.5,101.1 L440.2,101.9 L437.6,101.2 L438.0,100.3 L443.5,101.1Z M432.2,89.4 L444.2,87.8 L443.0,89.4 L438.0,89.7 L439.5,90.9 L435.6,90.6 L438.7,96.1 L436.7,95.6 L436.8,98.7 L435.4,98.8 L430.3,92.0 L432.2,89.4Z"/>
<path class="world-country" data-country="Turkey" d="M483.3,97.2 L466.0,97.9 L464.7,100.0 L464.7,98.3 L461.6,98.0 L460.2,99.2 L452.8,98.2 L450.9,99.3 L446.4,98.2 L443.6,95.0 L444.6,93.3 L443.3,92.3 L445.7,90.3 L449.0,90.2 L449.9,88.6 L454.0,88.9 L459.1,86.9 L469.4,89.1 L478.6,87.8 L483.3,91.8 L481.8,92.4 L483.3,97.2Z M443.2,87.3 L447.2,86.9 L449.3,88.4 L443.7,90.8 L443.2,87.3Z"/>
<path class="world-country" data-country="Albania" d="M432.2,89.4 L430.3,92.0 L428.7,90.6 L429.4,85.5 L432.2,89.4Z"/>
<path class="world-country" data-country="Croatia" d="M422.6,77.4 L428.7,80.1 L420.9,80.9 L426.7,85.9 L421.4,83.7 L419.0,80.4 L416.4,80.3 L422.6,77.4Z"/>
<path class="world-country" data-country="Switzerland" d="M407.6,75.2 L409.3,77.4 L402.6,78.9 L399.9,77.9 L401.5,75.2 L407.6,75.2Z"/>
<path class="world-country" data-country="Luxembourg" d="M399.4,69.8 L400.3,71.1 L399.2,71.0 L399.4,69.8Z"/>
<path class="world-country" data-country="Belgium" d="M400.2,68.3 L399.2,71.0 L392.4,67.5 L397.7,66.8 L400.2,68.3Z"/>
<path class="world-country" data-country="Netherlands" d="M401.8,62.6 L400.2,68.3 L394.1,67.1 L397.1,63.4 L401.8,62.6Z"/>
<path class="world-country" data-country="Portugal" d="M367.6,87.2 L369.2,86.3 L373.3,88.2 L370.9,91.9 L371.9,95.2 L370.1,97.9 L367.9,97.8 L368.0,94.8 L366.5,93.8 L367.6,87.2Z"/>
<path class="world-country" data-country="Spain" d="M371.0,97.3 L370.9,91.9 L373.3,88.2 L369.2,86.3 L367.6,87.2 L366.8,84.7 L369.8,83.2 L393.4,85.9 L391.5,88.6 L388.7,89.0 L386.4,92.6 L387.2,93.8 L382.4,98.2 L377.6,98.2 L375.4,99.8 L371.0,97.3Z"/>
<path class="world-country" data-country="Ireland" d="M373.7,61.8 L372.4,65.2 L365.5,66.1 L367.3,63.9 L366.2,61.7 L370.7,59.1 L370.7,61.4 L373.7,61.8Z"/>
<path class="world-country" data-country="New Caledonia" d="M739.7,218.6 L746.3,222.9 L742.8,221.9 L739.7,218.6Z"/>
<path class="world-country" data-country="Solomon Is." d="M735.1,198.1 L734.7,198.9 L733.8,197.6 L735.1,198.1Z M733.0,193.6 L734.3,196.7 L732.2,193.6 L733.0,193.6Z M732.8,196.9 L730.7,196.7 L730.4,195.6 L731.8,195.9 L732.8,196.9Z M727.5,191.5 L730.8,194.1 L727.2,191.7 L727.5,191.5Z"/>
<path class="world-country" data-country="New Zealand" d="M770.8,255.9 L765.4,263.5 L762.5,263.5 L763.7,261.7 L760.7,259.7 L762.6,255.2 L758.2,249.2 L761.8,250.7 L765.3,255.6 L770.8,255.9Z M746.1,271.6 L758.5,261.8 L759.5,263.6 L761.6,263.6 L758.3,267.9 L759.1,268.9 L755.6,269.8 L753.8,273.3 L751.1,274.8 L745.4,273.9 L746.1,271.6Z"/>
<path class="world-country target" data-country="Australia" data-score="90" d="M698.2,262.3 L705.8,262.6 L705.0,267.6 L701.0,268.3 L698.2,262.3Z M669.4,242.7 L654.1,245.8 L652.9,247.8 L644.8,248.0 L640.8,250.3 L634.3,248.5 L636.0,244.2 L630.7,231.3 L631.6,232.2 L630.9,230.3 L632.6,231.7 L630.8,227.7 L631.5,223.6 L637.9,219.8 L646.8,217.7 L651.5,210.7 L653.3,212.1 L652.5,211.1 L657.2,206.1 L660.2,205.3 L665.7,207.7 L667.8,202.5 L672.0,201.6 L670.4,199.9 L671.6,199.6 L677.9,201.9 L680.5,201.1 L681.4,202.1 L678.3,207.8 L688.5,213.5 L690.7,210.7 L693.4,198.6 L696.4,206.8 L697.8,206.0 L699.6,207.7 L701.7,216.2 L707.0,219.2 L708.8,223.3 L711.1,223.5 L711.4,225.7 L715.6,229.5 L717.2,235.6 L715.7,243.0 L710.2,251.6 L709.5,255.3 L701.6,258.7 L698.5,257.4 L698.8,256.3 L695.8,258.2 L689.4,256.6 L687.1,252.6 L684.0,251.5 L684.1,248.9 L681.2,250.7 L683.3,245.7 L679.4,249.9 L675.7,245.1 L669.4,242.7Z"/>
<path class="world-country" data-country="Sri Lanka" d="M562.8,160.0 L562.5,162.2 L559.7,163.3 L558.3,158.6 L559.3,155.1 L562.8,160.0Z"/>
<path class="world-country target" data-country="China" data-score="69" d="M622.4,137.4 L620.6,136.7 L620.5,134.9 L625.2,133.4 L622.4,137.4Z M559.6,86.2 L560.9,84.4 L558.9,80.7 L564.3,79.4 L565.8,75.6 L570.1,76.3 L571.4,73.2 L575.7,71.4 L582.6,76.6 L582.5,80.0 L591.9,82.2 L594.2,85.4 L603.8,85.5 L612.7,87.8 L621.9,85.8 L627.4,83.2 L626.4,81.7 L627.5,80.3 L630.9,81.0 L639.5,77.0 L644.3,77.0 L640.8,74.1 L635.3,73.9 L637.9,70.2 L640.4,71.0 L643.5,69.7 L646.6,65.8 L645.4,64.1 L649.8,62.7 L657.8,64.0 L661.5,70.5 L665.2,71.1 L668.6,74.6 L677.3,73.2 L673.2,80.3 L668.7,80.6 L667.9,86.1 L666.5,84.8 L662.3,86.9 L662.6,88.1 L659.8,87.3 L654.2,91.3 L647.3,93.5 L649.7,90.3 L648.5,89.2 L639.7,93.8 L644.4,97.2 L646.8,95.7 L650.1,96.6 L650.4,97.7 L647.4,98.3 L643.2,102.0 L645.5,103.1 L649.1,108.8 L647.7,110.9 L649.5,112.7 L648.6,116.1 L642.1,123.9 L636.2,127.7 L625.2,130.6 L624.5,132.8 L623.3,133.0 L623.2,130.6 L617.1,129.7 L616.5,127.6 L613.5,126.5 L605.6,128.6 L605.9,131.1 L600.4,129.1 L601.0,127.3 L599.1,124.9 L596.9,125.3 L599.2,117.6 L597.5,115.9 L593.9,115.7 L593.7,113.5 L590.3,113.9 L585.9,116.8 L580.5,116.0 L578.0,118.1 L577.8,116.4 L571.5,116.2 L556.3,109.1 L556.7,103.2 L554.4,100.7 L550.8,99.9 L545.4,92.4 L559.6,86.2Z"/>
<path class="world-country" data-country="Taiwan" d="M648.2,122.3 L647.5,127.6 L646.6,129.4 L645.2,126.0 L648.2,122.3Z"/>
<path class="world-country" data-country="Italy" d="M409.5,76.5 L416.7,77.4 L417.0,79.3 L413.5,79.8 L414.1,82.5 L426.5,90.4 L426.3,91.6 L423.3,90.2 L422.4,91.6 L423.7,93.5 L420.7,95.6 L421.6,93.4 L420.1,91.1 L411.1,86.2 L408.9,82.8 L406.1,81.9 L403.0,83.3 L401.7,78.5 L406.3,78.4 L409.5,76.5Z M414.0,95.1 L420.4,94.9 L419.5,98.3 L413.7,96.2 L414.0,95.1Z M404.5,89.1 L406.8,88.6 L408.1,90.1 L407.8,92.9 L405.9,93.5 L404.5,89.1Z"/>
<path class="world-country" data-country="Denmark" d="M408.3,59.4 L405.3,59.4 L404.4,56.1 L409.7,53.6 L409.0,55.4 L410.5,56.3 L407.7,58.4 L408.3,59.4Z M413.6,57.0 L413.0,59.8 L410.7,58.6 L410.4,57.7 L413.6,57.0Z"/>
<path class="world-country target" data-country="United Kingdom" data-score="78" d="M373.7,61.8 L370.7,61.4 L370.7,59.1 L374.8,60.3 L373.7,61.8Z M380.3,62.7 L379.2,60.2 L376.1,59.2 L376.1,57.7 L375.0,58.7 L373.8,55.6 L376.2,51.7 L380.5,51.7 L378.2,53.9 L382.8,53.7 L380.3,57.3 L382.5,57.4 L388.0,63.7 L390.6,64.2 L389.3,66.1 L390.1,67.2 L374.6,69.6 L379.7,66.9 L375.7,65.7 L377.9,65.1 L377.2,62.6 L380.3,62.7Z"/>
<path class="world-country" data-country="Iceland" d="M355.8,35.1 L355.3,36.4 L357.7,37.9 L346.9,41.3 L338.1,40.4 L340.2,39.4 L335.5,38.4 L339.2,37.4 L334.7,36.9 L339.4,35.2 L342.8,36.6 L355.8,35.1Z"/>
<path class="world-country" data-country="Azerbaijan" d="M486.8,87.2 L489.8,88.7 L491.5,87.3 L495.3,90.6 L493.6,90.8 L492.1,94.7 L490.2,93.7 L490.3,92.0 L487.0,93.8 L485.1,91.4 L483.7,88.5 L487.0,88.9 L486.8,87.2Z M486.2,93.8 L484.7,93.5 L483.3,91.8 L485.3,92.3 L486.2,93.8Z"/>
<path class="world-country" data-country="Georgia" d="M472.9,83.9 L484.8,85.9 L487.3,88.7 L476.3,87.9 L476.1,85.6 L472.9,83.9Z"/>
<path class="world-country" data-country="Philippines" d="M647.7,150.1 L645.7,147.4 L648.3,148.3 L647.7,150.1Z M651.4,156.8 L651.3,152.9 L652.5,152.8 L652.2,154.2 L653.8,152.1 L651.4,156.8Z M656.6,155.3 L659.1,160.7 L658.3,162.7 L657.5,160.5 L656.5,161.6 L656.6,164.1 L654.1,162.9 L652.8,159.4 L649.1,160.7 L652.5,157.5 L653.3,158.5 L656.8,156.9 L656.6,155.3Z M644.3,153.6 L638.9,158.2 L643.9,151.9 L644.3,153.6Z M650.0,137.3 L648.7,145.6 L653.5,146.7 L653.8,149.4 L651.3,147.2 L646.4,146.6 L647.1,145.2 L644.8,143.3 L646.5,136.7 L650.0,137.3Z M649.3,153.8 L649.0,150.7 L651.7,151.4 L649.3,153.8Z M656.8,150.2 L657.4,152.5 L655.8,152.0 L655.3,154.5 L654.2,149.3 L656.8,150.2Z"/>
<path class="world-country" data-country="Malaysia" d="M602.2,162.3 L608.4,164.2 L611.1,173.2 L605.0,170.1 L602.2,162.3Z M640.4,167.2 L636.1,166.8 L633.4,172.9 L624.6,174.3 L623.1,173.1 L622.8,171.7 L626.0,172.0 L626.4,170.2 L629.9,169.4 L632.5,166.4 L635.0,166.8 L638.0,161.3 L643.2,164.5 L640.4,167.2Z"/>
<path class="world-country" data-country="Brunei" d="M635.2,164.4 L635.0,166.8 L633.5,167.5 L632.5,166.4 L635.2,164.4Z"/>
<path class="world-country" data-country="Slovenia" d="M416.7,77.4 L421.8,76.6 L422.6,77.4 L420.0,79.6 L416.5,79.5 L416.7,77.4Z"/>
<path class="world-country" data-country="Finland" d="M449.4,28.1 L448.2,31.0 L451.5,32.4 L449.5,34.0 L452.0,36.5 L450.5,38.3 L452.5,39.8 L451.6,41.2 L454.8,42.7 L454.0,43.8 L447.4,47.7 L436.2,49.1 L432.8,47.2 L433.3,42.0 L441.6,37.9 L437.7,35.2 L437.6,31.9 L431.4,29.5 L440.2,30.4 L446.6,27.2 L449.4,28.1Z"/>
<path class="world-country" data-country="Slovakia" d="M435.5,71.9 L434.0,73.5 L425.4,74.7 L423.3,73.2 L426.9,71.0 L435.5,71.9Z"/>
<path class="world-country" data-country="Czechia" d="M419.3,67.6 L424.7,69.2 L427.5,71.0 L423.5,72.9 L419.8,72.0 L417.8,73.0 L413.9,70.9 L413.3,69.4 L419.3,67.6Z"/>
<path class="world-country" data-country="Eritrea" d="M465.3,145.4 L466.2,140.0 L469.6,137.8 L471.4,142.2 L479.6,149.0 L478.1,149.4 L473.1,145.2 L468.5,144.2 L467.8,145.8 L465.3,145.4Z"/>
<path class="world-country target" data-country="Japan" data-score="74" d="M692.1,92.9 L690.1,95.0 L688.5,101.5 L682.0,102.6 L679.0,105.0 L677.4,102.6 L668.6,104.1 L670.8,105.7 L669.4,109.3 L666.9,109.4 L667.5,107.4 L665.2,105.4 L672.1,100.8 L678.7,100.6 L681.0,96.9 L682.4,97.9 L686.8,94.9 L688.7,88.6 L690.9,88.2 L692.1,92.9Z M697.9,82.8 L699.4,81.9 L699.9,84.2 L696.7,84.8 L694.8,86.9 L691.5,85.5 L690.3,87.8 L687.9,87.8 L687.6,85.7 L691.0,84.0 L692.2,79.4 L697.9,82.8Z M671.6,105.0 L674.9,103.1 L676.7,104.3 L673.0,106.6 L671.6,105.0Z"/>
<path class="world-country" data-country="Paraguay" d="M261.9,218.7 L262.4,222.8 L267.0,223.4 L267.9,226.7 L270.3,226.9 L269.2,232.4 L267.3,234.0 L261.0,233.5 L262.8,229.3 L256.2,226.6 L252.2,223.1 L254.2,217.6 L259.9,217.0 L261.9,218.7Z"/>
<path class="world-country" data-country="Yemen" d="M498.8,135.7 L501.2,140.7 L499.2,142.9 L480.5,149.2 L478.6,143.7 L480.3,138.7 L488.1,140.0 L492.6,136.5 L498.8,135.7Z"/>
<path class="world-country" data-country="Saudi Arabia" d="M462.2,113.7 L467.6,112.4 L468.7,111.3 L466.6,109.2 L471.3,107.8 L483.1,114.1 L489.0,114.5 L494.8,119.4 L498.8,127.2 L505.7,127.8 L506.7,129.3 L505.2,133.6 L492.6,136.5 L488.1,140.0 L480.3,138.7 L479.0,141.3 L471.1,130.8 L469.8,125.7 L461.5,116.5 L462.2,113.7Z"/>
<path class="world-country" data-country="N. Cyprus" d="M460.0,101.6 L457.8,100.9 L461.3,100.3 L460.0,101.6Z"/>
<path class="world-country" data-country="Cyprus" d="M456.4,101.5 L458.8,101.4 L460.1,101.8 L457.9,102.7 L456.4,101.5Z"/>
<path class="world-country" data-country="Morocco" d="M382.3,101.4 L384.2,107.6 L368.4,114.8 L368.1,118.5 L362.5,119.0 L355.3,130.4 L350.4,130.5 L356.0,120.3 L366.4,112.5 L365.9,109.9 L368.4,105.5 L372.1,103.6 L374.3,100.1 L382.3,101.4Z"/>
<path class="world-country" data-country="Egypt" d="M466.3,129.3 L440.8,129.3 L441.1,109.0 L449.2,110.5 L453.6,109.1 L455.7,110.4 L460.7,109.8 L462.1,113.4 L460.4,117.0 L456.5,112.9 L463.7,125.2 L463.4,127.0 L466.3,129.3Z"/>
<path class="world-country" data-country="Libya" d="M440.6,108.3 L440.8,133.6 L438.3,134.4 L421.1,126.3 L417.4,128.3 L409.2,124.3 L407.0,120.6 L408.4,109.4 L411.6,107.3 L411.7,105.7 L419.8,107.6 L420.8,109.4 L428.0,111.8 L431.8,106.6 L440.6,108.3Z"/>
<path class="world-country" data-country="Ethiopia" d="M489.7,159.0 L483.7,165.4 L477.0,167.7 L474.7,166.9 L472.1,168.7 L464.7,166.5 L457.9,159.5 L459.7,158.2 L460.7,153.4 L465.3,145.4 L467.8,145.8 L468.5,144.2 L476.4,147.4 L478.1,149.4 L476.8,152.5 L479.0,152.8 L480.9,156.5 L489.7,159.0Z"/>
<path class="world-country" data-country="Djibouti" d="M478.1,149.4 L480.1,149.7 L479.0,152.8 L476.8,152.5 L478.1,149.4Z"/>
<path class="world-country" data-country="Somaliland" d="M492.2,151.8 L492.2,155.9 L489.7,159.0 L480.9,156.5 L478.5,153.5 L479.8,151.7 L481.9,153.8 L492.2,151.8Z"/>
<path class="world-country" data-country="Uganda" d="M459.9,178.0 L450.6,178.8 L454.2,167.9 L460.1,167.0 L461.1,168.4 L462.3,171.9 L459.9,178.0Z"/>
<path class="world-country" data-country="Rwanda" d="M452.4,178.4 L453.1,180.8 L449.4,182.0 L450.0,179.4 L452.4,178.4Z"/>
<path class="world-country" data-country="Bosnia and Herz." d="M426.9,85.5 L422.4,82.6 L421.3,80.1 L428.6,80.9 L428.8,83.6 L426.9,85.5Z"/>
<path class="world-country" data-country="Macedonia" d="M435.1,86.2 L436.3,88.3 L431.3,88.9 L431.6,86.8 L435.1,86.2Z"/>
<path class="world-country" data-country="Serbia" d="M427.5,78.6 L430.5,78.2 L435.8,81.5 L435.5,85.9 L433.4,86.4 L431.8,84.2 L430.6,85.2 L428.3,83.7 L429.1,82.6 L427.5,78.6Z"/>
<path class="world-country" data-country="Montenegro" d="M430.2,85.7 L428.6,87.2 L426.7,85.9 L428.3,83.7 L430.2,85.7Z"/>
<path class="world-country" data-country="Kosovo" d="M431.3,87.2 L430.2,85.7 L431.4,84.3 L433.8,85.5 L431.3,87.2Z"/>
<path class="world-country" data-country="Trinidad and Tobago" d="M253.8,154.6 L256.1,152.9 L256.0,154.5 L253.8,154.6Z"/>
<path class="world-country" data-country="S. Sudan" d="M453.3,168.5 L450.9,166.2 L447.2,166.6 L438.4,157.7 L442.4,153.9 L444.5,155.9 L449.3,156.0 L451.5,154.1 L454.4,155.2 L456.7,152.5 L456.0,150.6 L458.4,150.1 L460.0,157.5 L457.9,159.5 L462.9,164.3 L458.8,167.9 L453.3,168.5Z"/>
 </g></svg></div><div class="world-tooltip" id="worldTooltip" aria-hidden="true"><small>COUNTRY SPOTLIGHT</small><strong id="worldName">Canada</strong><em id="worldScore">84</em><small>Illustrative index / 100</small></div><div class="world-foot"><span>World: 7 sample countries highlighted</span><span>Hover or focus · tap on mobile</span><span>Fictional scores</span></div></div>
</div></div></section>
<section class="widget reveal" data-widget="table_ranking"><div class="widget-head"><div><div class="widget-title">Ranking table</div><div class="widget-description">Search the sample data or sort by rank, place or score.</div></div><span class="tag">Build (must - ranking table)</span></div><div class="widget-body"><div class="mini-tools"><input class="search" id="tableSearch" type="search" placeholder="Search locations…" aria-label="Search demo ranking table"></div><table><thead><tr><th data-sort="rank"># ↕</th><th data-sort="city">Location ↕</th><th data-sort="score">Score ↕</th></tr></thead><tbody id="tableRows"></tbody></table><div class="tab-foot" id="tableStatus">Showing 5 demo rows</div></div></section>
<section class="widget reveal" data-widget="ranking"><div class="widget-head"><div><div class="widget-title">Animated ranking bars</div><div class="widget-description">Rows and bars reveal smoothly; hover for individual scores.</div></div><span class="tag">Build (must - bar chart)</span></div><div class="widget-body" id="bars"><div class="bar-row" title="Seattle: 92.4"><span class="bar-name">Seattle</span><div class="bar-track"><div class="bar-fill" style="--value:92.4%;--delay:80ms"></div></div><strong class="bar-amt">92.4</strong></div><div class="bar-row" title="Denver: 88.7"><span class="bar-name">Denver</span><div class="bar-track"><div class="bar-fill" style="--value:88.7%;--delay:160ms"></div></div><strong class="bar-amt">88.7</strong></div><div class="bar-row" title="Austin: 85.3"><span class="bar-name">Austin</span><div class="bar-track"><div class="bar-fill" style="--value:85.3%;--delay:240ms"></div></div><strong class="bar-amt">85.3</strong></div><div class="bar-row" title="Atlanta: 81.5"><span class="bar-name">Atlanta</span><div class="bar-track"><div class="bar-fill" style="--value:81.5%;--delay:320ms"></div></div><strong class="bar-amt">81.5</strong></div><div class="bar-row" title="Boston: 78.9"><span class="bar-name">Boston</span><div class="bar-track"><div class="bar-fill" style="--value:78.9%;--delay:400ms"></div></div><strong class="bar-amt">78.9</strong></div><div class="chart-axis"><span>0</span><span>Illustrative index score / 100</span><span>100</span></div></div></section>
<section class="widget reveal" data-widget="comparison"><div class="widget-head"><div><div class="widget-title">Side-by-side comparison</div><div class="widget-description">Select either city to highlight its comparative result.</div></div><span class="tag">Build (must - comparison)</span></div><div class="widget-body"><div class="metric-split"><button class="measure selected" data-city="Seattle"><div class="m-label">Seattle</div><div class="m-number">92.4</div><div class="m-bar"><span style="--value:92.4%"></span></div><div class="m-note">Index score</div></button><button class="measure" data-city="Denver"><div class="m-label">Denver</div><div class="m-number">88.7</div><div class="m-bar"><span style="--value:88.7%"></span></div><div class="m-note">Index score</div></button></div><div class="compare-summary" id="compareSummary">Seattle is 3.7 points higher than Denver in this fictional example.</div></div></section>
<section class="widget reveal" data-widget="scatter"><div class="widget-head"><div><div class="widget-title">Scatterplot</div><div class="widget-description">Hover over points to explore the relationship between two measures.</div></div><span class="tag">Build (must - scatterplot)</span></div><div class="widget-body"><svg class="scatter-svg" viewBox="0 0 450 215" role="img" aria-label="Scatterplot comparing fictional access and index scores"><g class="scatter-grid"><path d="M45 20H432 M45 68H432 M45 116H432 M45 164H432 M45 20V183 M144 20V183 M243 20V183 M342 20V183 M432 20V183"/></g><path class="scatter-trend" d="M53 166L420 35"/><g id="plotPoints"></g><g class="scatter-label"><text x="45" y="208">Lower access</text><text x="353" y="208">Higher access</text><text x="8" y="18">Score</text></g></svg><div class="tooltip" id="scatterTooltip" aria-live="polite">Hover over a plotted location for details.</div></div></section>
<section class="widget reveal" data-widget="heatmap"><div class="widget-head"><div><div class="widget-title">Metric heatmap</div><div class="widget-description">Hover over any cell to reveal its illustrative value.</div></div><span class="tag">Build (must - heatmap)</span></div><div class="widget-body"><div class="heat-grid" id="heatGrid"></div><div class="tooltip" id="heatTooltip" aria-live="polite">Hover over a square to inspect a value.</div></div></section>
<section class="widget reveal" data-widget="metric_cards"><div class="widget-head"><div><div class="widget-title">Metric cards</div><div class="widget-description">Animated, clearly labelled headline figures.</div></div><span class="tag">Build (must - metric cards)</span></div><div class="widget-body"><div class="stat-grid"><div class="stat"><div class="number" data-count="5">5</div><div class="stat-name">Locations</div></div><div class="stat"><div class="number" data-count="92.4">92.4</div><div class="stat-name">Highest score</div></div><div class="stat"><div class="number" data-count="13.5">13.5</div><div class="stat-name">Score spread</div></div></div><div class="stat-note">Values are illustrative. The published landing page will use verified research figures.</div></div></section>
<section class="widget reveal" data-widget="callout"><div class="widget-head"><div><div class="widget-title">Editorial callout</div><div class="widget-description">A focused, branded explanation that connects the data to the story.</div></div><span class="tag">Build (must - callout)</span></div><div class="widget-body"><div class="callout"><div class="eyebrow" style="margin-bottom:11px">Research insight</div><h4>What makes the top-ranked location stand out?</h4><p>A short editorial interpretation that explains the underlying factors, rather than simply repeating a ranking number. This is placeholder copy and not a real study finding.</p></div></div></section>

<section class="widget reveal" data-widget="hybrid_ranking">
 <div class="widget-head"><div><div class="widget-title">Hybrid ranking: chart + table</div><div class="widget-description">Scores, ranks and animated bars together, without switching views.</div><div class="preview-card-label">Suggested name: hybrid ranking</div></div><span class="status-chip">New preview · engine pending</span></div>
 <div class="widget-body"><div class="mini-tools"><input type="search" class="search" id="hybridSearch" placeholder="Filter locations…" aria-label="Filter hybrid ranking"/></div>
 <table class="hybrid-table"><thead><tr><th>Rank</th><th>Location</th><th>Score ↕</th><th>Visual</th></tr></thead><tbody id="hybridRows"></tbody></table>
 <div class="tab-foot" id="hybridStatus">Sample index / 100</div></div>
</section>
<section class="widget reveal" data-widget="donut">
 <div class="widget-head"><div><div class="widget-title">Animated donut / pie chart</div><div class="widget-description">Show shares of a total. Switch chart style or select a segment.</div><div class="preview-card-label">Suggested name: donut chart</div></div><span class="status-chip">New preview · engine pending</span></div>
 <div class="widget-body"><div class="choice-tools"><button id="viewDonut" class="active" type="button" aria-pressed="true">Donut</button><button id="viewPie" type="button" aria-pressed="false">Pie</button></div>
 <div class="donut-flex"><svg class="donut-wheel" id="donutWheel" viewBox="0 0 150 150" role="img" aria-label="Fictional distribution shares"><circle cx="75" cy="75" r="41" fill="none" stroke="var(--brand-line)" stroke-width="22"></circle><g id="donutArcs"></g><circle class="donut-center" cx="75" cy="75" r="29"></circle><text x="75" y="84" class="donut-total" id="donutCentre">100%</text></svg><div class="legend-list" id="donutLegend"></div></div><div class="mini-tooltip" id="donutHint" aria-live="polite">Select a category to highlight its share.</div></div>
</section>
<section class="widget reveal" data-widget="heatmap_table">
 <div class="widget-head"><div><div class="widget-title">Heatmap ranking table</div><div class="widget-description">Combine exact values, column explanations and colour intensity.</div><div class="preview-card-label">Suggested name: heatmap table</div></div><span class="status-chip">New preview · engine pending</span></div>
 <div class="widget-body"><div style="overflow-x:auto"><table class="heat-table"><thead><tr><th data-htsort="city" title="Place included in the illustrative study">City ↕</th><th data-htsort="score" title="Illustrative overall score out of 100">Score ↕ ⓘ</th><th data-htsort="access" title="Illustrative access rating out of 100">Access ↕ ⓘ</th><th data-htsort="value" title="Illustrative value rating out of 100">Value ↕ ⓘ</th></tr></thead><tbody id="heatTableRows"></tbody></table></div><div class="mini-tooltip" id="heatTableHint" aria-live="polite">Hover on a numeric cell, or a header for its meaning.</div></div>
</section>
<section class="widget reveal" data-widget="trend_line">
 <div class="widget-head"><div><div class="widget-title">Animated trend lines</div><div class="widget-description">Compare how two series change across multiple years.</div><div class="preview-card-label">Suggested name: line chart</div></div><span class="status-chip">New preview · engine pending</span></div>
 <div class="widget-body"><svg class="trend-svg" viewBox="0 0 470 220" role="img" aria-label="Illustrative scores for two cities over five periods"><g class="mini-grid"><path d="M45 20H447M45 70H447M45 120H447M45 170H447"></path></g><g class="mini-axis"><text x="4" y="23">100</text><text x="11" y="73">75</text><text x="11" y="123">50</text><text x="11" y="173">25</text><text x="44" y="201">2022</text><text x="141" y="201">2023</text><text x="242" y="201">2024</text><text x="342" y="201">2025</text><text x="424" y="201">2026</text></g><path id="trendA" class="trend-series" stroke="var(--primary)" d="M47 147 L146 118 L245 124 L344 76 L442 40" style="--dly:70ms"></path><path id="trendB" class="trend-series" stroke="var(--pale)" d="M47 164 L146 139 L245 109 L344 125 L442 92" style="--dly:280ms"></path><g id="trendPoints"></g></svg><div class="stack-legend"><span><i style="background:var(--primary)"></i>Seattle</span><span><i style="background:var(--pale)"></i>Denver</span></div><div class="mini-tooltip" id="trendHint" aria-live="polite">Hover over a point to read an illustrative score.</div></div>
</section>
<section class="widget reveal" data-widget="stacked_bar">
 <div class="widget-head"><div><div class="widget-title">Animated stacked bars</div><div class="widget-description">Compare how three components contribute to each total.</div><div class="preview-card-label">Suggested name: stacked bars</div></div><span class="status-chip">New preview · engine pending</span></div>
 <div class="widget-body"><div class="stack-grid" id="stackBars"></div><div class="stack-legend" id="stackLegend"></div><div class="mini-tooltip" id="stackHint" aria-live="polite">Hover over a segment to inspect its contribution.</div></div>
</section>
<section class="widget reveal" data-widget="slope_chart">
 <div class="widget-head"><div><div class="widget-title">Before / after slope chart</div><div class="widget-description">Highlight places gaining or losing ground between two periods.</div><div class="preview-card-label">Suggested name: slope chart</div></div><span class="status-chip">New preview · engine pending</span></div>
 <div class="widget-body"><svg class="slope-svg" id="slopeSvg" viewBox="0 0 470 220" role="img" aria-label="Illustrative rankings in two periods"><g class="mini-grid"><path d="M117 20V192M345 20V192"></path></g><g class="mini-axis"><text x="73" y="12">Before</text><text x="311" y="12">After</text><text x="24" y="213">2024</text><text x="315" y="213">2026</text></g><g id="slopeLines"></g></svg><div class="mini-tooltip" id="slopeHint" aria-live="polite">Hover over a line to view a fictional ranking change.</div></div>
</section>

<section class="widget reveal" data-widget="route_arcs"><div class="widget-head"><div><div class="widget-title">Travel / route arcs</div><div class="widget-description">Animated origin-to-destination curves for flights, travel, and schedules.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="route-stage"><svg viewBox="0 0 480 225" role="img" aria-label="Illustrative route arcs from Honolulu to five destinations"><g class="route-grid"><path d="M25 196H455 M25 146H455 M25 96H455 M25 46H455 M110 14V196 M240 14V196 M370 14V196"/></g><g id="routeLines"></g><circle cx="47" cy="184" r="7" class="route-dot"/><text class="route-text" x="20" y="212">Honolulu</text></svg></div><div class="infographic-foot" id="routeHint">Hover or focus a route to see its distance.</div></div></section>
<section class="widget reveal" data-widget="sparkline_kpi"><div class="widget-head"><div><div class="widget-title">KPI card + sparkline</div><div class="widget-description">Headline metric with a fine-grained animated trend and changing values.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="spark-card"><div class="spark-meta">ILLUSTRATIVE MONTHLY REVENUE</div><div class="spark-top"><strong class="spark-number" id="sparkNumber">$317,911</strong><span class="spark-delta">+2.0% ↗</span></div><svg class="spark-svg" viewBox="0 0 430 118" role="img" aria-label="Animated fictional revenue sparkline"><defs><linearGradient id="sparkFade" x1="0" x2="0" y1="0" y2="1"><stop stop-color="var(--primary)" stop-opacity=".25"/><stop offset="1" stop-color="var(--primary)" stop-opacity="0"/></linearGradient></defs><path class="spark-area" d="M8 97 L8 84 L45 67 L78 76 L109 42 L146 59 L180 64 L210 40 L248 55 L277 89 L312 59 L344 28 L377 41 L417 19 L417 97Z"/><path class="spark-line" id="sparkLine" d="M8 84 L45 67 L78 76 L109 42 L146 59 L180 64 L210 40 L248 55 L277 89 L312 59 L344 28 L377 41 L417 19"/><line class="spark-cursor" id="sparkCursor" x1="8" x2="8" y1="8" y2="96"/><circle class="spark-point" id="sparkPoint" cx="8" cy="84" r="6"/></svg><div class="range-ends"><span>Jan</span><span>Mar</span><span>May</span><span>Jul</span><span>Sep</span><span>Dec</span></div></div><div class="infographic-foot" id="sparkHint">Move over the line to inspect a sample value.</div></div></section>
<section class="widget reveal" data-widget="range_spectrum"><div class="widget-head"><div><div class="widget-title">Price range / benchmark spectrum</div><div class="widget-description">Compare low, average and high prices on one animated scale.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="infographic-canvas"><div class="range-chart"><div class="range-heading">$1,378.69 price spread</div><div class="range-sub">Family-of-four arena cost · fictional comparison</div><div class="range-rail"><span class="range-marker" id="rangeMarker" data-label="NBA average" style="--x:29%"></span></div><div class="range-ends"><span><b>$551.86</b> · lowest</span><span><b>$1,930.55</b> · highest</span></div><div class="range-actions" id="rangeActions"><button type="button" data-range="0">Lowest</button><button type="button" data-range="1" class="active">Average</button><button type="button" data-range="2">Highest</button></div></div></div><div class="infographic-foot" id="rangeHint">NBA average: $954.64 in this fictional illustration.</div></div></section>
<section class="widget reveal" data-widget="waterfall"><div class="widget-head"><div><div class="widget-title">Waterfall change breakdown</div><div class="widget-description">Show which factors push a total up or down.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="infographic-canvas" style="min-height:255px"><div class="waterfall-graph" id="waterfallGraph"></div></div><div class="infographic-foot">Changes bridge a starting value of 60 to an ending value of 82.</div></div></section>
<section class="widget reveal" data-widget="bubble"><div class="widget-head"><div><div class="widget-title">Bubble magnitude explorer</div><div class="widget-description">Size encodes magnitude; select a bubble to reveal its exact value.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="infographic-canvas"><div class="bubble-canvas" id="bubbleCanvas"></div></div><div class="infographic-foot" id="bubbleHint">Select a bubble to compare sample event volumes.</div></div></section>
<section class="widget reveal" data-widget="radar"><div class="widget-head"><div><div class="widget-title">Radar / profile comparison</div><div class="widget-description">Compare performance across several related dimensions.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="choice-tools"><button id="radarOne" class="active" type="button">Seattle</button><button id="radarTwo" type="button">Denver</button></div><svg class="radar-svg" viewBox="0 0 350 245" role="img" aria-label="Interactive five-axis radar chart of sample profiles" id="radarChart"><g id="radarScaffold"></g><polygon class="radar-area" id="radarPoly" points=""/><g id="radarDots"></g></svg><div class="infographic-foot" id="radarHint">Choose a city to compare its fictional performance profile.</div></div></section>
<section class="widget reveal" data-widget="funnel"><div class="widget-head"><div><div class="widget-title">Conversion funnel</div><div class="widget-description">Show how participants or opportunities progress through stages.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="funnel-wrap" id="funnelStages"></div><div class="infographic-foot" id="funnelHint">Hover a stage to reveal conversion from the previous step.</div></div></section>
<section class="widget reveal" data-widget="waffle"><div class="widget-head"><div><div class="widget-title">Waffle / percentage grid</div><div class="widget-description">Explain percentages as 100 individually animated squares.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="choice-tools"><button class="active" type="button" data-waffle="63">63%</button><button type="button" data-waffle="78">78%</button><button type="button" data-waffle="42">42%</button></div><div class="waffle-wrap" id="waffleGrid" role="img" aria-label="One hundred cells coloured to illustrate a percentage"></div><div class="waffle-caption" id="waffleCaption">63% <span> of the fictional sample</span></div></div></section>
<section class="widget reveal" data-widget="timeline"><div class="widget-head"><div><div class="widget-title">Interactive event timeline</div><div class="widget-description">Tell a research story through chronological milestones.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="timeline-wrap" id="timelineList"></div><div class="infographic-foot" id="timelineHint">Select an event to expand its illustrative context.</div></div></section>
<section class="widget reveal" data-widget="diverging"><div class="widget-head"><div><div class="widget-title">Diverging sentiment bars</div><div class="widget-description">Compare negative and positive sentiment around a zero line.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="diverge-bars" id="divergingBars"></div><div class="infographic-foot" id="divergingHint">Left = negative · right = positive · fictional percentages.</div></div></section>
<section class="widget reveal" data-widget="lollipop"><div class="widget-head"><div><div class="widget-title">Animated lollipop ranking</div><div class="widget-description">A compact alternative to bars for comparison across categories.</div></div><span class="preview-only">New concept</span></div><div class="widget-body"><div class="lolli-wrap" id="lollipopChart"></div><div class="infographic-foot" id="lolliHint">Select a dot to inspect a sample ranking.</div></div></section>

</div>
<script>
(()=>{'use strict';
const places=[{city:'Seattle',score:92.4},{city:'Denver',score:88.7},{city:'Austin',score:85.3},{city:'Atlanta',score:81.5},{city:'Boston',score:78.9}],$=s=>document.querySelector(s),all=s=>Array.from(document.querySelectorAll(s));
const stateNames={"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"};
const stateScores=Object.fromEntries(Object.keys(stateNames).map((s,i)=>[s,+(52+((i*29+13)%420)/10).toFixed(1)]));
stateScores.NM=83.2;stateScores.CA=93.7;stateScores.WA=91.2;stateScores.TX=70.6;stateScores.FL=78.4;
const orderedStates=Object.entries(stateScores).sort((a,b)=>b[1]-a[1]).map(([s])=>s);
let selectedState=null;
const stage=$('#atlasStage'),flyout=$('#mapFlyout');
function hideState(){
  selectedState=null;
  stage.classList.remove('is-inspecting');
  flyout.classList.remove('is-visible');
  flyout.setAttribute('aria-hidden','true');
  all('.us-state').forEach(el=>el.classList.remove('chosen'));
}
const mapSvg=$('.state-atlas');
const clamp=(value,min,max)=>Math.min(Math.max(value,min),Math.max(min,max));
function positionFlyout(state, event){
  // Place by pointer on hover/tap; for keyboard focus use the visible state's bounding box.
  const stageRect=stage.getBoundingClientRect();
  const svgRect=mapSvg.getBoundingClientRect();
  const stateRect=$('#state-'+state).getBoundingClientRect();
  const usePointer=event&&Number.isFinite(event.clientX)&&Number.isFinite(event.clientY)
     &&(event.type!=='focus');
  const x=(usePointer?event.clientX:(stateRect.left+stateRect.right)/2)-stageRect.left;
  const y=(usePointer?event.clientY:(stateRect.top+stateRect.bottom)/2)-stageRect.top;
  const cardWidth=flyout.offsetWidth, cardHeight=flyout.offsetHeight;
  const padding=8, offset=16;
  // Flip to left of pointer at right edge. Keep the map header/legend unobstructed.
  let tx=x+offset;
  if(tx+cardWidth>stageRect.width-padding)tx=x-cardWidth-offset;
  tx=clamp(tx,padding,stageRect.width-cardWidth-padding);
  const mapTop=clamp(svgRect.top-stageRect.top+3,padding,stageRect.height-cardHeight-padding);
  const maxY=Math.max(mapTop,stageRect.height-cardHeight-padding);
  let ty=clamp(y-cardHeight/2,mapTop,maxY);
  // On narrow maps, favor positioning below the point where there is enough room.
  if(stageRect.width<=700 && y+cardHeight+offset<maxY){ty=clamp(y+offset,mapTop,maxY);}
  flyout.style.setProperty('--tooltip-x',`${Math.round(tx)}px`);
  flyout.style.setProperty('--tooltip-y',`${Math.round(ty)}px`);
}
function showState(state,event){
  if(!stateNames[state])return;
  selectedState=state;
  const score=stateScores[state],rank=orderedStates.indexOf(state)+1;
  $('#stateTitle').textContent=stateNames[state];
  $('#stateRank').textContent='NO. '+String(rank).padStart(2,'0');
  $('#stateScore').textContent=score.toFixed(1);
  $('#metric1').textContent=String(130+((rank*13)%270));
  $('#metric2').textContent=String(42+((rank*7)%52));
  $('#metric3').textContent=String(7+((rank*11)%34));
  $('#metric4').textContent=(2.1+((rank*17)%29)/10).toFixed(1);
  $('#stateNote').textContent=`${stateNames[state]} ranks #${rank} in this fictional 50-state example. Values illustrate the interactive layout only.`;
  all('.us-state').forEach(el=>el.classList.toggle('chosen',el.dataset.state===state));
  const el=$('#state-'+state),box=el.getBBox();
  const cx=(box.x+box.width/2).toFixed(1),cy=(box.y+box.height/2).toFixed(1);
  $('#mapHalo').setAttribute('cx',cx);$('#mapHalo').setAttribute('cy',cy);
  $('#mapBeacon').setAttribute('cx',cx);$('#mapBeacon').setAttribute('cy',cy);
  stage.classList.add('is-inspecting');
  flyout.classList.add('is-visible');
  flyout.setAttribute('aria-hidden','false');
  positionFlyout(state,event);
}
let tapSelection=false;
all('.us-state').forEach(el=>{
  const state=el.dataset.state;
  el.addEventListener('mouseenter',e=>{if(!tapSelection)showState(state,e);});
  el.addEventListener('mousemove',e=>{if(!tapSelection && selectedState===state)positionFlyout(state,e);});
  el.addEventListener('mouseleave',()=>{if(!tapSelection)hideState();});
  el.addEventListener('focus',e=>showState(state,e));
  el.addEventListener('blur',()=>{if(!tapSelection)hideState();});
  el.addEventListener('click',e=>{
    // Touchscreens have no hover. One tap positions details near the touched state.
    if(matchMedia('(hover: none)').matches)tapSelection=true;
    showState(state,e);
  });
  el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showState(state);}if(e.key==='Escape'){tapSelection=false;hideState();el.blur();}});
});
window.addEventListener('resize',()=>{if(selectedState)positionFlyout(selectedState);});
stage.addEventListener('mouseleave',()=>{if(!tapSelection)hideState();});
document.addEventListener('pointerdown',e=>{
  if(tapSelection&&!e.target.closest('.us-state')){tapSelection=false;hideState();}
});
hideState();
let sortKey='rank',sortDir=1;function drawTable(){const q=$('#tableSearch').value.toLowerCase().trim();const rows=places.map((p,i)=>({...p,rank:i+1})).filter(p=>p.city.toLowerCase().includes(q));rows.sort((a,b)=>{let v=a[sortKey],w=b[sortKey];return(typeof v==='number'?v-w:String(v).localeCompare(String(w)))*sortDir});$('#tableRows').innerHTML=rows.map(p=>`<tr><td class="rank-id">${String(p.rank).padStart(2,'0')}</td><td>${p.city}</td><td><strong>${p.score.toFixed(1)}</strong></td></tr>`).join('')||'<tr><td colspan="3">No matching locations.</td></tr>';$('#tableStatus').textContent=`Showing ${rows.length} of ${places.length} fictional example rows`;all('#tableRows tr').forEach((r,i)=>r.style.setProperty('--ri',i))}
$('#tableSearch').addEventListener('input',drawTable);all('th[data-sort]').forEach(th=>th.addEventListener('click',()=>{let k=th.dataset.sort;if(k===sortKey)sortDir*=-1;else{sortKey=k;sortDir=k==='city'?1:-1}drawTable()}));drawTable();
all('.measure').forEach(b=>b.addEventListener('click',()=>{all('.measure').forEach(x=>x.classList.toggle('selected',x===b));$('#compareSummary').textContent=b.dataset.city==='Seattle'?'Seattle is 3.7 points higher than Denver in this fictional example.':'Denver is 3.7 points below Seattle in this fictional example.'}));
const pts=[['Seattle',66,43,92],['Denver',142,106,75],['Austin',194,76,84],['Atlanta',267,86,80],['Boston',345,47,88],['Phoenix',309,134,60]];const ns='http://www.w3.org/2000/svg';pts.forEach(([city,x,y,score],i)=>{const group=document.createElementNS(ns,'g');group.setAttribute('class','plotgroup');group.style.setProperty('--delay',`${100+i*90}ms`);const circle=document.createElementNS(ns,'circle');circle.setAttribute('class','scatter-dot');circle.setAttribute('cx',x);circle.setAttribute('cy',y);circle.setAttribute('r',7);circle.setAttribute('tabindex','0');circle.setAttribute('aria-label',`${city}: example score ${score}`);group.appendChild(circle);$('#plotPoints').appendChild(group);for(const event of ['mouseenter','focus'])circle.addEventListener(event,()=>$('#scatterTooltip').textContent=`${city} · Illustrative relationship score: ${score}`)});
const heatData=[[24,56,82,38,91],[74,92,48,82,65],[95,43,79,52,86]];const days=['Mon','Tue','Wed','Thu','Fri'],periods=['Morning','Afternoon','Evening'];$('#heatGrid').innerHTML='<span></span>'+days.map(d=>`<span class="heat-label">${d}</span>`).join('')+heatData.map((r,i)=>`<span class="heat-row">${periods[i]}</span>`+r.map((v,j)=>`<div class="heat" role="img" tabindex="0" aria-label="${periods[i]} ${days[j]} value ${v}" style="--intensity:${v}%;--delay:${(i*5+j)*35}ms" data-hint="${periods[i]}, ${days[j]}: ${v} (demo)"></div>`).join('')).join('');all('.heat').forEach(el=>{for(const ev of ['mouseenter','focus'])el.addEventListener(ev,()=>$('#heatTooltip').textContent=el.dataset.hint)});
all('.stat').forEach((el,i)=>el.style.setProperty('--ci',i));
let numberRun=0;
function animateNumbers(){
  const run=++numberRun;
  all('.stat .number').forEach(el=>{
    const target=Number(el.dataset.count||'0'),decimal=target%1!==0,start=performance.now();
    el.textContent=decimal?'0.0':'0';
    function tick(now){
      if(run!==numberRun)return;
      const frac=Math.min(1,(now-start)/920),ease=1-Math.pow(1-frac,3);
      el.textContent=decimal?(target*ease).toFixed(1):String(Math.round(target*ease));
      if(frac<1)requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
}

// v7.9: six interactive demonstrations. The main renderer remains unchanged.
const rawHybrid=[...places];let hybReverse=false;
function drawHybrid(){const q=$('#hybridSearch').value.trim().toLowerCase();const arr=rawHybrid.filter(p=>p.city.toLowerCase().includes(q)).sort((a,b)=>hybReverse?a.score-b.score:b.score-a.score);
 $('#hybridRows').innerHTML=arr.map((p,i)=>`<tr><td class="rank-id">${String(i+1).padStart(2,'0')}</td><td>${p.city}</td><td class="hybrid-score">${p.score.toFixed(1)}</td><td><div class="hybrid-meter"><i style="--w:${p.score}%;--dly:${i*90}ms"></i></div></td></tr>`).join('')||'<tr><td colspan="4">No matching places</td></tr>';
 $('#hybridStatus').textContent=`Showing ${arr.length} of 5 illustrative records · click Score to reverse`;
 const card=$('[data-widget="hybrid_ranking"]');if(card.classList.contains('animated')){card.classList.remove('animated');void card.offsetHeight;card.classList.add('animated');}}
$('#hybridSearch').addEventListener('input',drawHybrid);all('.hybrid-table th').forEach(th=>{if(th.textContent.includes('Score'))th.addEventListener('click',()=>{hybReverse=!hybReverse;drawHybrid();});});drawHybrid();

const donutData=[{name:'Tickets',pct:39,color:'var(--primary)'},{name:'Food',pct:28,color:'var(--pale)'},{name:'Travel',pct:19,color:'color-mix(in srgb,var(--primary) 52%,white)'},{name:'Other',pct:14,color:'color-mix(in srgb,var(--primary) 42%,var(--secondary))'}];
let cursor=0;
$('#donutArcs').innerHTML=donutData.map((d,i)=>{const length=d.pct/100*257.61;const markup=`<circle class="donut-arc" data-donut="${i}" cx="75" cy="75" r="41" stroke="${d.color}" style="--arc:${length.toFixed(3)};--offset:${(-cursor*257.61/100).toFixed(3)};--dly:${i*110}ms" tabindex="0" role="button" aria-label="${d.name}: ${d.pct} percent"></circle>`;cursor+=d.pct;return markup;}).join('');
$('#donutLegend').innerHTML=donutData.map((d,i)=>`<button class="legend-row" type="button" data-donut="${i}"><i class="legend-swatch" style="background:${d.color}"></i><span>${d.name}</span><strong>${d.pct}%</strong></button>`).join('');
function chooseDonut(i){all('[data-donut]').forEach(el=>el.classList.toggle('active',Number(el.dataset.donut)===i));const d=donutData[i];$('#donutCentre').textContent=`${d.pct}%`;$('#donutHint').textContent=`${d.name} represents ${d.pct}% of this fictional total.`;}
all('[data-donut]').forEach(el=>{el.addEventListener('mouseenter',()=>chooseDonut(+el.dataset.donut));el.addEventListener('click',()=>chooseDonut(+el.dataset.donut));el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();chooseDonut(+el.dataset.donut)}})});
const setDonutMode=pie=>{$('#donutWheel').classList.toggle('pie',pie);$('#viewPie').classList.toggle('active',pie);$('#viewDonut').classList.toggle('active',!pie);$('#viewPie').setAttribute('aria-pressed',String(pie));$('#viewDonut').setAttribute('aria-pressed',String(!pie));};$('#viewDonut').addEventListener('click',()=>setDonutMode(false));$('#viewPie').addEventListener('click',()=>setDonutMode(true));

const heatRows=[{city:'Seattle',score:92,access:84,value:63},{city:'Denver',score:89,access:72,value:88},{city:'Austin',score:85,access:95,value:73},{city:'Atlanta',score:82,access:68,value:91},{city:'Boston',score:79,access:89,value:56}];let htKey='score',htOrder=-1;
function drawHeatTable(){const rows=[...heatRows].sort((a,b)=>(typeof a[htKey]==='number'?a[htKey]-b[htKey]:a[htKey].localeCompare(b[htKey]))*htOrder);
 $('#heatTableRows').innerHTML=rows.map((r,i)=>`<tr><td>${r.city}</td>`+['score','access','value'].map(k=>`<td><span class="heat-value" tabindex="0" data-explain="${r.city}: ${k} ${r[k]}/100, illustrative" style="--shade:${(r[k]*.7).toFixed(1)}%;--dly:${i*65}ms">${r[k]}</span></td>`).join('')+'</tr>').join('');
 all('.heat-value').forEach(el=>{for(const event of ['mouseenter','focus'])el.addEventListener(event,()=>$('#heatTableHint').textContent=el.dataset.explain);});}
all('[data-htsort]').forEach(th=>{th.addEventListener('click',()=>{const k=th.dataset.htsort;if(k===htKey)htOrder*=-1;else{htKey=k;htOrder=k==='city'?1:-1}drawHeatTable()});th.addEventListener('mouseenter',()=>$('#heatTableHint').textContent=th.title)});drawHeatTable();

const makeSvg=(tag,attrs)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);return el;};
for(const [city,col,coords] of [['Seattle','var(--primary)',[[47,147,45],[146,118,60],[245,124,58],[344,76,77],[442,40,92]]],['Denver','var(--pale)',[[47,164,37],[146,139,49],[245,109,64],[344,125,57],[442,92,71]]]]){
 coords.forEach(([x,y,val])=>{const dot=makeSvg('circle',{cx:x,cy:y,r:5,class:'trend-point',stroke:col,tabindex:0,'aria-label':`${city} illustrative ${val}`});$('#trendPoints').appendChild(dot);for(const event of ['mouseenter','focus'])dot.addEventListener(event,()=>$('#trendHint').textContent=`${city}: ${val} illustrative points.`);});}
all('.trend-series').forEach(line=>line.style.setProperty('--path-len',line.getTotalLength()));

const stackData=[['Seattle',[42,36,22]],['Denver',[31,40,29]],['Austin',[37,28,35]],['Boston',[52,25,23]]];const segments=['Events','Weather','Value'];const segColors=['var(--primary)','var(--pale)','color-mix(in srgb,var(--primary) 35%,var(--secondary))'];
$('#stackBars').innerHTML=stackData.map(([city,shares])=>`<div class="stack-row"><b>${city}</b><div class="stack-track">${shares.map((v,i)=>`<span class="stack-piece" tabindex="0" role="img" aria-label="${city} ${segments[i]} ${v}%" data-tip="${city} · ${segments[i]}: ${v}%" style="--w:${v}%;--dly:${(stackData.findIndex(a=>a[0]===city)*75)+i*100}ms;background:${segColors[i]}"></span>`).join('')}</div><b class="stack-value">100%</b></div>`).join('');
$('#stackLegend').innerHTML=segments.map((t,i)=>`<span><i style="background:${segColors[i]}"></i>${t}</span>`).join('');all('.stack-piece').forEach(el=>{for(const ev of ['mouseenter','focus'])el.addEventListener(ev,()=>$('#stackHint').textContent=el.dataset.tip)});

const slopeData=[['Seattle',1,7,'var(--primary)'],['Denver',4,1,'var(--pale)'],['Austin',7,10,'color-mix(in srgb,var(--primary) 50%,white)'],['Boston',10,4,'color-mix(in srgb,var(--pale) 60%,var(--primary))']];
$('#slopeLines').innerHTML=slopeData.map(([city,before,after,color],i)=>{const y1=24+(before-1)*16,y2=24+(after-1)*16;return `<path tabindex="0" role="img" aria-label="${city} from ${before} to ${after}" class="slope-line" data-city="${city}" data-delta="${(after-before)>0?'+':''}${after-before}" d="M117 ${y1} L345 ${y2}" stroke="${color}" style="--dly:${i*100}ms"/><circle class="slope-dot" cx="117" cy="${y1}" r="5" fill="${color}"/><circle class="slope-dot" cx="345" cy="${y2}" r="5" fill="${color}"/><text class="slope-lbl" x="108" y="${y1+4}" text-anchor="end">${before}</text><text class="slope-lbl" x="354" y="${y2+4}">${after} ${city}</text>`}).join('');
all('.slope-line').forEach(line=>{line.style.setProperty('--path-len',line.getTotalLength());for(const ev of ['mouseenter','focus'])line.addEventListener(ev,()=>$('#slopeHint').textContent=`${line.dataset.city}: ${line.dataset.delta} illustrative points between periods.`)});

$('#widgetCount').textContent=`${all('.gallery>.widget').length} widgets`;


// v7.10 — interactive infographic extensions. No runtime network requests.
const $maybe=(sel)=>document.querySelector(sel);
const worldStage=$('#worldStage'),worldTip=$('#worldTooltip');
const worldNames={"United States of America":"United States","United Kingdom":"United Kingdom"};
function worldHide(){worldTip.classList.remove('visible');worldTip.setAttribute('aria-hidden','true');all('.world-country.active').forEach(p=>p.classList.remove('active'))}
function worldHover(el,x,y){let name=el.dataset.country,score=el.dataset.score;if(!score||(geoMode==='na'&&!(['Canada','United States of America'].includes(name)))){worldHide();return};all('.world-country.active').forEach(p=>p.classList.remove('active'));el.classList.add('active');$('#worldName').textContent=worldNames[name]||name;$('#worldScore').textContent=score;worldTip.classList.add('visible');worldTip.setAttribute('aria-hidden','false');const box=worldStage.getBoundingClientRect();let lx=x-box.left+13,ly=y-box.top+13;if(lx+worldTip.offsetWidth>box.width-6)lx=x-box.left-worldTip.offsetWidth-12;if(ly+worldTip.offsetHeight>box.height-8)ly=box.height-worldTip.offsetHeight-8;worldTip.style.left=Math.max(6,lx)+'px';worldTip.style.top=Math.max(6,ly)+'px'}
all('.world-country').forEach(el=>{if(!el.dataset.score)return;el.style.setProperty('--strength',String(Math.max(30,+el.dataset.score)));el.setAttribute('tabindex','0');el.setAttribute('role','button');el.setAttribute('aria-label',`${el.dataset.country}: fictional score ${el.dataset.score}`);el.addEventListener('pointermove',e=>worldHover(el,e.clientX,e.clientY));el.addEventListener('pointerenter',e=>worldHover(el,e.clientX,e.clientY));el.addEventListener('pointerleave',worldHide);el.addEventListener('blur',worldHide);el.addEventListener('focus',()=>{const b=el.getBoundingClientRect();worldHover(el,b.left+b.width/2,b.top+b.height/2)});el.addEventListener('click',e=>worldHover(el,e.clientX,e.clientY));el.addEventListener('keydown',e=>{if(e.key==='Enter'){const b=el.getBoundingClientRect();worldHover(el,b.left+b.width/2,b.top+b.height/2)}})});worldStage.addEventListener('pointerleave',worldHide);worldStage.addEventListener('focusout',e=>{if(!worldStage.contains(e.relatedTarget))worldHide()});


// Dedicated administrative-level US/Canada map; world geometry is never shown in this mode.
const mapViewButtons=all('[data-geo-mode]');
const usMapPanel=$('#usMapPanel'),northAmericaPanel=$('#northAmericaPanel'),globalMapPanel=$('#globalMapPanel');
const geoMapDescription=$('#geoMapModeDescription');
const mapModeDescriptions={us:'50 US states · state-level fictional rankings',canada:'Canada · 10 provinces + 3 territories · 13 regions',na:'US states + Canadian provinces and territories · 63 regions',world:'World · seven highlighted fictional country scores'};
let naLoaded=false,naLoadingPromise=null,naTouchSelected=false;
const naSvg=$('#naMapSvg'),naGroup=$('#naRegions'),naLabels=$('#naLabels'),naTip=$('#naTip'),naStage=$('#naStage');
all('.world-country.target').forEach((el,i)=>el.style.setProperty('--reveal-index',i%9));
function closeNaTip(){naTouchSelected=false;naTip.classList.remove('visible');naTip.setAttribute('aria-hidden','true');all('.na-region.active').forEach(el=>el.classList.remove('active'))}
// Only the 50 US states, not DC or outlying possessions. Canadian data contains 10 provinces and 3 territories.
const naStateNames=new Set('Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|'));
const naCanNames=new Set('Alberta|British Columbia|Manitoba|New Brunswick|Newfoundland and Labrador|Nova Scotia|Ontario|Prince Edward Island|Quebec|Saskatchewan|Nunavut|Northwest Territories|Yukon Territory'.split('|'));
const naAbbr={Alberta:'AB','British Columbia':'BC',Manitoba:'MB','New Brunswick':'NB','Newfoundland and Labrador':'NL','Nova Scotia':'NS',Ontario:'ON','Prince Edward Island':'PE',Quebec:'QC',Saskatchewan:'SK',Nunavut:'NU','Northwest Territories':'NT','Yukon Territory':'YT',Alabama:'AL',Alaska:'AK',Arizona:'AZ',Arkansas:'AR',California:'CA',Colorado:'CO',Connecticut:'CT',Delaware:'DE',Florida:'FL',Georgia:'GA',Hawaii:'HI',Idaho:'ID',Illinois:'IL',Indiana:'IN',Iowa:'IA',Kansas:'KS',Kentucky:'KY',Louisiana:'LA',Maine:'ME',Maryland:'MD',Massachusetts:'MA',Michigan:'MI',Minnesota:'MN',Mississippi:'MS',Missouri:'MO',Montana:'MT',Nebraska:'NE',Nevada:'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND',Ohio:'OH',Oklahoma:'OK',Oregon:'OR',Pennsylvania:'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD',Tennessee:'TN',Texas:'TX',Utah:'UT',Vermont:'VT',Virginia:'VA',Washington:'WA','West Virginia':'WV',Wisconsin:'WI',Wyoming:'WY'};
const naRemoteBase=[
  'https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/',
  'https://cdn.jsdelivr.net/gh/codeforgermany/click_that_hood@main/public/data/'
];
async function naFetchGeo(file){
 let lastError;
 for(const base of naRemoteBase){
  try{const control=new AbortController(),t=setTimeout(()=>control.abort(),12000);let response;
   try{response=await fetch(base+file,{signal:control.signal,cache:'force-cache'})}finally{clearTimeout(t)}
   if(!response.ok)throw Error('HTTP '+response.status);
   const geo=await response.json();if(!Array.isArray(geo.features))throw Error('Invalid feature collection');return geo;
  }catch(e){lastError=e}
 }
 throw new Error('Boundary data unavailable: '+(lastError?.message||'network error'));
}
// Equirectangular North-American view. No Mexico/South America or world features are rendered.
function naXY(c){let lon=c[0],lat=c[1];if(lon>0)lon-=360;return [30+(lon+179)*7.93, 24+(84-lat)*8.45]}
function naRingD(ring){if(!Array.isArray(ring)||ring.length<3)return '';const parts=[];for(let i=0;i<ring.length;i++){const v=naXY(ring[i]);parts.push((i?'L':'M')+v[0].toFixed(1)+','+v[1].toFixed(1))}return parts.join(' ')+' Z'}
function naGeometryD(g){if(!g)return '';const polygons=g.type==='MultiPolygon'?g.coordinates:g.type==='Polygon'?[g.coordinates]:[];return polygons.map(poly=>poly.map(naRingD).join(' ')).join(' ')}
function naTooltipAt(clientX,clientY){const rect=naStage.getBoundingClientRect(),w=naTip.offsetWidth||175,h=naTip.offsetHeight||100;
 let x=clientX-rect.left+14,y=clientY-rect.top-h-12;
 if(x+w>rect.width-8)x=clientX-rect.left-w-14;
 if(x<8)x=8;if(y<9)y=clientY-rect.top+14;
 if(y+h>rect.height-8)y=Math.max(8,rect.height-h-8);
 naTip.style.left=x+'px';naTip.style.top=y+'px';
}
function naSelect(el,e){if(geoMode!=='na'&&geoMode!=='canada')return;all('.na-region.active').forEach(x=>x.classList.remove('active'));el.classList.add('active');
 naTip.innerHTML='<b>'+el.dataset.name+'</b><small>'+el.dataset.country+' · illustrative result</small><strong>'+el.dataset.score+' / 100</strong><small>Fictional score, for gallery demonstration only</small>';
 naTip.classList.add('visible');naTip.setAttribute('aria-hidden','false');
 const r=el.getBoundingClientRect();naTooltipAt(e?.clientX??(r.left+r.width/2),e?.clientY??(r.top+r.height/2));
}
// Draw geographic regions from the boundary dataset. The Click That Hood
// United States collection contains the contiguous 48; Alaska and Hawaii
// are provided by our bundled, verified 50-state atlas as scaled insets.
function naRenderRegion(name,country,geometry,i,inset=null){
 const ns='http://www.w3.org/2000/svg',path=document.createElementNS(ns,'path');
 const base=inset?document.getElementById('state-'+inset.code):null;
 const d=inset?base?.getAttribute('d'):naGeometryD(geometry);
 if(!d)throw new Error('Missing map geometry for '+name);
 const h=[...name].reduce((a,c)=>a*31+c.charCodeAt(0),7)>>>0,score=(49+(h%510)/10).toFixed(1),shade=(24+(score-49)*1.35).toFixed(0)+'%';
 path.setAttribute('d',d);path.setAttribute('class','na-region');path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',name+', '+country+', fictional score '+score);
 path.dataset.name=name;path.dataset.country=country;path.dataset.score=score;path.style.setProperty('--shade',shade);path.style.setProperty('--i',i);
 const show=e=>naSelect(path,e);path.addEventListener('pointerenter',e=>{if(e.pointerType!=='touch')show(e)});path.addEventListener('pointermove',e=>{if(naTip.classList.contains('visible'))naTooltipAt(e.clientX,e.clientY)});
 path.addEventListener('pointerleave',()=>{if(!naTouchSelected)closeNaTip()});path.addEventListener('focus',show);path.addEventListener('blur',closeNaTip);path.addEventListener('click',e=>{e.stopPropagation();naTouchSelected=matchMedia('(hover:none)').matches;show(e)});
 path.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show(e)}if(e.key==='Escape')closeNaTip()});naGroup.appendChild(path);
 if(inset){
   // Alaska and Hawaii are retained as real outlines, not approximate squares.
   // Insets make all 63 regions legible without including Mexico or other countries.
   const bbox=path.getBBox();
   if(!(bbox.width>0&&bbox.height>0))throw new Error(name+' inset has invalid geometry');
   const s=Math.min(inset.w/bbox.width,inset.h/bbox.height);
   const dx=inset.x+(inset.w-bbox.width*s)/2-bbox.x*s;
   const dy=inset.y+(inset.h-bbox.height*s)/2-bbox.y*s;
   path.setAttribute('transform',`translate(${dx.toFixed(3)},${dy.toFixed(3)}) scale(${s.toFixed(5)})`);
   const label=document.createElementNS(ns,'text');label.textContent=inset.code+' · inset';label.setAttribute('x',String(inset.x+inset.w/2));label.setAttribute('y',String(inset.y-8));label.setAttribute('class','na-map-label na-inset-label');label.dataset.country=country;naLabels.appendChild(label);
 }else{
   try{const bbox=path.getBBox();if(bbox.width>31&&bbox.height>23&&bbox.width*bbox.height>1450){const label=document.createElementNS(ns,'text');label.textContent=naAbbr[name]||name.slice(0,2).toUpperCase();label.setAttribute('x',(bbox.x+bbox.width/2).toFixed(1));label.setAttribute('y',(bbox.y+bbox.height/2).toFixed(1));label.setAttribute('class','na-map-label');label.dataset.country=country;naLabels.appendChild(label)}}catch(_e){}
 }
}
async function naLoad(){if(naLoaded)return;if(naLoadingPromise)return naLoadingPromise;
 naLoadingPromise=(async()=>{try{
  const [us,ca]=await Promise.all([naFetchGeo('united-states.geojson'),naFetchGeo('canada.geojson')]);
  const usRegions=us.features.filter(f=>naStateNames.has(f.properties?.name)),caRegions=ca.features.filter(f=>naCanNames.has(f.properties?.name));
  const foundUS=new Set(usRegions.map(f=>f.properties.name));
  const missingUS=[...naStateNames].filter(name=>!foundUS.has(name));
  const missingCA=[...naCanNames].filter(name=>!caRegions.some(f=>f.properties.name===name));
  // The source normally omits Alaska and Hawaii; they are already bundled in
  // our US map SVG, so add them as separate clickable geographic insets.
  const unexpected=missingUS.filter(name=>name!=='Alaska'&&name!=='Hawaii');
  if(unexpected.length||missingCA.length)throw new Error('Missing administrative boundaries: '+[...unexpected,...missingCA].join(', '));
  // Draw with all regions visible first so label placement and inset bounds work.
  northAmericaPanel.dataset.mapMode='na';
  naGroup.innerHTML='';naLabels.innerHTML='';naSvg.hidden=false;let i=0;
  [...usRegions.map(f=>[f,'United States']),...caRegions.map(f=>[f,'Canada'])].forEach(([f,country])=>naRenderRegion(f.properties.name,country,f.geometry,i++));
  if(missingUS.includes('Alaska'))naRenderRegion('Alaska','United States',null,i++,{code:'AK',x:58,y:445,w:222,h:122});
  if(missingUS.includes('Hawaii'))naRenderRegion('Hawaii','United States',null,i++,{code:'HI',x:308,y:552,w:84,h:42});
  const actual=naGroup.querySelectorAll('.na-region').length;
  if(actual!==63)throw new Error('Expected 63 regions but rendered '+actual);
  $('#naRegionCount').textContent='50 US states · 10 provinces · 3 territories';$('#naLoading').hidden=true;naSvg.hidden=false;naLoaded=true;naApplyMode();
 }catch(error){
  $('#naLoading').hidden=false;
  const msg=String(error.message||error);
  $('#naLoading').textContent=(msg.startsWith('Boundary data unavailable')?'The geographic data service could not be reached. ':'Unable to render the full regional map. ')+msg;
  naLoadingPromise=null;
 }
 })();return naLoadingPromise;
}
let geoMode='us';
// Crop the existing combined choropleth to Canadian provincial geometry.
// No second fetch, duplicate map instance or invented boundaries are necessary.
function naApplyMode(){
 const canadaOnly=geoMode==='canada';
 northAmericaPanel.dataset.mapMode=canadaOnly?'canada':'na';
 $('#naRegionCount').textContent=canadaOnly?'10 provinces · 3 territories':'50 US states · 10 provinces · 3 territories';
 northAmericaPanel.querySelector('.na-topline strong').textContent=canadaOnly?'Canada · Provincial & Territorial Explorer':'US & Canada · Regional Explorer';
 northAmericaPanel.querySelector('.na-foot span').textContent=canadaOnly?'All 10 provinces and 3 territories':'US states and Canadian provinces / territories only';
 naSvg.setAttribute('aria-label',canadaOnly?'Canada only: interactive map of 10 provinces and 3 territories':'US and Canada: interactive map of 50 states and 13 Canadian regions');
 if(!canadaOnly){naSvg.setAttribute('viewBox','0 0 1060 620');return}
 if(!naLoaded)return;
 const regions=all('.na-region[data-country="Canada"]',naGroup);
 if(regions.length!==13)return;
 const boxes=regions.map(p=>p.getBBox()).filter(b=>b.width>0&&b.height>0);
 if(boxes.length!==13)return;
 const minX=Math.min(...boxes.map(b=>b.x)),minY=Math.min(...boxes.map(b=>b.y));
 const maxX=Math.max(...boxes.map(b=>b.x+b.width)),maxY=Math.max(...boxes.map(b=>b.y+b.height));
 const padx=24,pady=30;
 naSvg.setAttribute('viewBox',`${(minX-padx).toFixed(1)} ${(minY-pady).toFixed(1)} ${(maxX-minX+padx*2).toFixed(1)} ${(maxY-minY+pady*2).toFixed(1)}`);
}
function changeGeographicView(mode){
 if(!['us','canada','na','world'].includes(mode))return;
 geoMode=mode;worldHide();hideState();closeNaTip();tapSelection=false;
 usMapPanel.hidden=mode!=='us';northAmericaPanel.hidden=!['na','canada'].includes(mode);globalMapPanel.hidden=mode!=='world';
 mapViewButtons.forEach(button=>{const active=button.dataset.geoMode===mode;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active))});
 geoMapDescription.textContent=mapModeDescriptions[mode];
 if(mode==='na'||mode==='canada'){naApplyMode();naLoad().then(()=>{if(geoMode==='na'||geoMode==='canada')naApplyMode()});}
 const visible=mode==='us'?usMapPanel:['na','canada'].includes(mode)?northAmericaPanel:globalMapPanel;
 for(const p of [usMapPanel,northAmericaPanel,globalMapPanel])p.classList.remove('is-entering');
 if(!matchMedia('(prefers-reduced-motion: reduce)').matches){void visible.offsetWidth;visible.classList.add('is-entering')}
}
mapViewButtons.forEach(button=>button.addEventListener('click',()=>changeGeographicView(button.dataset.geoMode)));
naStage.addEventListener('pointerleave',()=>{if(!naTouchSelected)closeNaTip()});
naStage.addEventListener('click',e=>{if(e.target.closest('.na-region'))return;closeNaTip()});
changeGeographicView('us');
const routeData=[['Stanford',4799,210,167],['Reno',5130,225,142],['Tempe',5825,265,115],['El Paso',6448,310,94],['Laramie',6843,365,64],['DeKalb',8377,419,35]];
$('#routeLines').innerHTML=routeData.map(([name,mi,x,y],i)=>{const arcTop=20+i*2;return `<path tabindex="0" role="button" aria-label="Honolulu to ${name}, ${mi} round-trip miles" class="route-path" data-route="${name}" data-mi="${mi}" d="M48 184 Q${(48+x)/2} ${arcTop} ${x} ${y}" style="--dly:${i*90}ms"/><circle cx="${x}" cy="${y}" r="5" fill="var(--primary)" stroke="var(--ink)" stroke-width="2" pointer-events="none"/><text class="route-text" x="${Math.min(x+8,405)}" y="${y-4}">${name}</text>`}).join('');
all('.route-path').forEach(p=>{for(const ev of ['mouseenter','focus','click'])p.addEventListener(ev,()=>{all('.route-path').forEach(x=>x.classList.remove('active'));p.classList.add('active');$('#routeHint').textContent=`Honolulu → ${p.dataset.route}: ${(+p.dataset.mi).toLocaleString()} illustrative round-trip miles.`})});
$('#sparkLine').style.setProperty('--len',$('#sparkLine').getTotalLength());
const sparkPoints=[[8,84,281500],[45,67,295400],[78,76,288200],[109,42,310100],[146,59,301700],[180,64,298400],[210,40,312400],[248,55,302800],[277,89,278700],[312,59,299500],[344,28,316400],[377,41,308800],[417,19,317911]];
$('#sparkLine').addEventListener('pointermove',e=>{const svg=$('#sparkLine').ownerSVGElement,b=svg.getBoundingClientRect();const sx=(e.clientX-b.left)/b.width*430;const p=sparkPoints.reduce((best,a)=>Math.abs(a[0]-sx)<Math.abs(best[0]-sx)?a:best,sparkPoints[0]);$('#sparkCursor').setAttribute('x1',p[0]);$('#sparkCursor').setAttribute('x2',p[0]);$('#sparkCursor').style.opacity=1;$('#sparkPoint').setAttribute('cx',p[0]);$('#sparkPoint').setAttribute('cy',p[1]);$('#sparkPoint').style.opacity=1;$('#sparkHint').textContent='Illustrative monthly value: $'+p[2].toLocaleString();$('#sparkNumber').textContent='$'+p[2].toLocaleString()});$('#sparkLine').addEventListener('pointerleave',()=>{$('#sparkCursor').style.opacity=0;$('#sparkPoint').style.opacity=0;$('#sparkNumber').textContent='$317,911'});
const rangeData=[['Lowest',551.86,0],['Average',954.64,29.21],['Highest',1930.55,100]];
all('[data-range]').forEach(btn=>btn.addEventListener('click',()=>{all('[data-range]').forEach(x=>x.classList.toggle('active',x===btn));const [name,val,pct]=rangeData[+btn.dataset.range];$('#rangeMarker').style.setProperty('--x',`${Math.max(2,Math.min(98,pct))}%`);$('#rangeMarker').dataset.label=name;$('#rangeHint').textContent=`${name}: $${val.toLocaleString('en-US',{minimumFractionDigits:2})} (fictional reference values).` }));
const waterfall=[['Start','60','60',0,60],['Tickets','+18','18',60,18],['Parking','+9','9',78,9],['Discount','−5','5',82,5],['End','82','82',0,82]];
$('#waterfallGraph').innerHTML=waterfall.map(([label,tag,height,bottom,size],i)=>{const isneg=label==='Discount';return `<div class="wf-col"><div class="wf-float ${isneg?'negative':''}" title="${label}: ${tag}" style="--height:${size*.93}%;--bottom:${isneg?(bottom-5)*.93:bottom*.93}%;--dly:${i*130}ms"></div><span class="wf-value" style="--height:${size*.93}%;--bottom:${isneg?(bottom-5)*.93:bottom*.93}%">${tag}</span><span class="wf-label">${label}</span></div>`}).join('');
const bubbles=[['Seattle',92,25,50,105],['Denver',69,54,35,84],['Austin',51,78,66,74],['Boston',36,51,80,62],['Miami',21,83,24,49]];
$('#bubbleCanvas').innerHTML=bubbles.map(([city,val,x,y,diam],i)=>`<button class="bubble" type="button" data-bubble="${city}" data-bval="${val}" style="left:${x}%;top:${y}%;width:${diam}px;height:${diam}px;--dly:${i*95}ms" aria-label="${city}, fictional volume ${val}">${city}</button>`).join('');all('.bubble').forEach(el=>el.addEventListener('click',()=>{all('.bubble').forEach(x=>x.classList.toggle('active',x===el));$('#bubbleHint').textContent=`${el.dataset.bubble}: ${el.dataset.bval} illustrative events. Circle area indicates magnitude.`}));
const radarLabels=['Value','Access','Interest','Growth','Quality'];const radial=(val,i)=>{const theta=(-Math.PI/2)+i*2*Math.PI/5;return [175+val*Math.cos(theta),114+val*Math.sin(theta)]};
$('#radarScaffold').innerHTML=[18,36,54,72,90].map(rad=>`<polygon class="radar-grid" points="${radarLabels.map((_,i)=>radial(rad,i).map(n=>n.toFixed(1)).join(',')).join(' ')}"/>`).join('')+radarLabels.map((t,i)=>{const [x,y]=radial(106,i),[ax,ay]=radial(90,i);return `<line class="radar-axis" x1="175" y1="114" x2="${ax}" y2="${ay}"/><text class="radar-axis-text" x="${x}" y="${y+4}">${t}</text>`}).join('');
function radarDraw(which){const dat=which===0?[89,63,78,52,93]:[76,84,60,91,70];$('#radarPoly').setAttribute('points',dat.map((v,i)=>radial(v*.9,i).map(n=>n.toFixed(1)).join(',')).join(' '));$('#radarDots').innerHTML=dat.map((v,i)=>{const [x,y]=radial(v*.9,i);return `<circle class="radar-dot" cx="${x}" cy="${y}" r="5" tabindex="0" data-rad="${radarLabels[i]}: ${v}"/>`}).join('');all('[data-rad]').forEach(el=>{for(const ev of ['mouseenter','focus'])el.addEventListener(ev,()=>$('#radarHint').textContent=el.dataset.rad+' / 100 (illustrative)')});$('#radarOne').classList.toggle('active',which===0);$('#radarTwo').classList.toggle('active',which===1)};$('#radarOne').addEventListener('click',()=>radarDraw(0));$('#radarTwo').addEventListener('click',()=>radarDraw(1));radarDraw(0);
const funnel=[['Reached',10000,100],['Engaged',6400,86],['Clicked',3100,69],['Converted',850,53]];
$('#funnelStages').innerHTML=funnel.map(([name,v,w],i)=>`<button class="funnel-level" type="button" style="--width:${w}%;--shade:${25+i*15}%;--dly:${i*160}ms" data-step="${i}"><span>${name}</span><strong>${v.toLocaleString()}</strong></button>`).join('');all('[data-step]').forEach(el=>el.addEventListener('click',()=>{const i=+el.dataset.step;$('#funnelHint').textContent=`${funnel[i][0]}: ${(funnel[i][1]/funnel[0][1]*100).toFixed(1)}% of the fictional starting cohort.`}));
function wafflePaint(pct){$('#waffleGrid').innerHTML=Array.from({length:100},(_,i)=>`<span class="waffle-cell ${i<pct?'filled':''}" style="--dly:${Math.min(i*8,750)}ms"></span>`).join('');$('#waffleCaption').innerHTML=`${pct}% <span>of the fictional sample</span>`;if($('#waffleGrid').closest('.widget').classList.contains('animated'))$('#waffleGrid').classList.add('animated');}all('[data-waffle]').forEach(btn=>btn.addEventListener('click',()=>{all('[data-waffle]').forEach(x=>x.classList.toggle('active',x===btn));wafflePaint(+btn.dataset.waffle)}));wafflePaint(63);
const timeline=[['January','Research begins','Team selects a topic and defines transparent measures.'],['March','Data collection','Sources are gathered and validated.'],['June','Model complete','Metrics are combined into a consistent ranking.'],['September','Publication','Interactive findings are published and shared.']];
$('#timelineList').innerHTML=timeline.map(([date,title,detail],i)=>`<button class="timeline-event" type="button" data-event="${i}" style="--dly:${i*120}ms"><strong>${date} · ${title}</strong><small>${i===0?detail:'Click to see details'}</small></button>`).join('');all('[data-event]').forEach(el=>el.addEventListener('click',()=>{const i=+el.dataset.event;el.querySelector('small').textContent=timeline[i][2];$('#timelineHint').textContent=`${timeline[i][0]}: ${timeline[i][1]}. Fictional editorial workflow.`}));
const diverge=[['Seattle',22,65],['Denver',41,44],['Austin',35,55],['Boston',60,28]];
$('#divergingBars').innerHTML=diverge.map(([city,neg,pos],i)=>`<div class="diverge-row"><strong>${city}</strong><div class="diverge-track"><div class="diverge-neg" style="--width:${neg}%;--dly:${i*110}ms" title="Negative: ${neg}%"></div><div class="diverge-pos" style="--width:${pos}%;--dly:${i*110}ms" title="Positive: ${pos}%"></div></div></div>`).join('');
const lolli=[['Seattle',92],['Denver',84],['Austin',79],['Boston',64],['Miami',53]];
$('#lollipopChart').innerHTML=lolli.map(([city,value],i)=>`<button type="button" class="lolli-row" data-lolli="${city}" data-score="${value}" style="background:transparent;border:0;color:var(--ink);text-align:left"><b>${city}</b><span class="lolli-track" style="--width:${value}%;--dly:${i*110}ms"><i class="lolli-dot"></i></span><b>${value}</b></button>`).join('');all('[data-lolli]').forEach(el=>el.addEventListener('click',()=>$('#lolliHint').textContent=`${el.dataset.lolli}: ${el.dataset.score} out of 100 (fictional score).`));

let galleryObserver=null;
let parentScrollCleanup=null;
function animate(){
  if(galleryObserver){galleryObserver.disconnect();galleryObserver=null;}
  if(parentScrollCleanup){parentScrollCleanup();parentScrollCleanup=null;}
  ++numberRun;
  all('.widget').forEach(el=>{el.classList.remove('shown','animated');});
  all('.stat .number').forEach(el=>el.textContent='0');
  hideState();tapSelection=false;
  // A layout read separates resetting from entrance animations.
  void document.body.offsetHeight;
  const reveal=el=>{
    if(el.classList.contains('shown'))return;
    el.classList.add('shown','animated');
    if(el.dataset.widget==='metric_cards'&&!matchMedia('(prefers-reduced-motion: reduce)').matches)animateNumbers();
    else if(el.dataset.widget==='metric_cards')all('.stat .number').forEach(n=>n.textContent=n.dataset.count);
  };
  if(matchMedia('(prefers-reduced-motion: reduce)').matches){all('.widget').forEach(reveal);return;}

  // st.iframe(height="content") grows to the *entire* gallery height. That means
  // an observer inside the iframe would animate everything at once. Watch the
  // parent Streamlit viewport instead so each card animates when scrolled to.
  try {
    const host=window.parent;
    if(host!==window && host.document){
      const frame=window.frameElement || [...host.document.querySelectorAll('iframe')].find(f=>f.contentWindow===window);
      if(frame){
        const pending=new Set(all('.widget'));
        let frameRequested=false;
        let ro=null;
        let onScroll=null;
        const removeWatchers=()=>{
          host.removeEventListener('scroll',onScroll,true);
          host.removeEventListener('resize',onScroll);
          if(ro)ro.disconnect();
        };
        const checkVisibility=()=>{
          frameRequested=false;
          const iframeRect=frame.getBoundingClientRect();
          const viewportHeight=host.innerHeight||host.document.documentElement.clientHeight;
          for(const el of [...pending]){
            const r=el.getBoundingClientRect();
            const top=iframeRect.top+r.top;
            const bottom=iframeRect.top+r.bottom;
            if(bottom>0 && top<viewportHeight-40 && r.height>0){reveal(el);pending.delete(el);}
          }
          if(!pending.size)removeWatchers();
        };
        onScroll=()=>{
          if(!frameRequested){frameRequested=true;requestAnimationFrame(checkVisibility);}
        };
        host.addEventListener('scroll',onScroll,true);
        host.addEventListener('resize',onScroll);
        if('ResizeObserver' in window){
          ro=new ResizeObserver(onScroll);
          ro.observe(document.documentElement);
        }
        parentScrollCleanup=removeWatchers;
        onScroll();
        return;
      }
    }
  }catch(_err){/* Cross-origin embed: fall back to iframe observer below. */}
  if('IntersectionObserver' in window){
    galleryObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{
      if(entry.isIntersecting){reveal(entry.target);galleryObserver?.unobserve(entry.target);}
    }),{threshold:.09,rootMargin:'0px 0px -22px 0px'});
    all('.widget').forEach(el=>galleryObserver.observe(el));
  } else all('.widget').forEach(reveal);
}
animate();
})();
</script></body></html>
"""


GALLERY_THEME = {'Action Network': {'background': '#080f14', 'panel': '#102025', 'elevated': '#1b3234', 'ocean': '#071419', 'horizon': '#10302d', 'line': '#314b48', 'highlight': '#10372e'}, 'VegasInsider': {'background': '#0c0d0f', 'panel': '#211e18', 'elevated': '#332d20', 'ocean': '#11100e', 'horizon': '#312816', 'line': '#53482d', 'highlight': '#3d311b'}, 'RotoGrinders': {'background': '#08111d', 'panel': '#142538', 'elevated': '#213c54', 'ocean': '#071527', 'horizon': '#163b5a', 'line': '#355874', 'highlight': '#173f5e'}, 'Canada Sports Betting': {'background': '#100c11', 'panel': '#25171d', 'elevated': '#3a2028', 'ocean': '#130d15', 'horizon': '#391724', 'line': '#57323e', 'highlight': '#441928'}}


def interactive_gallery_html(brand: str) -> str:
    theme = BRANDS[brand]
    primary, secondary = theme["primary"], theme["navy"]
    html = (_GALLERY_HTML
            .replace("__BRAND__", escape(theme["wordmark"]))
            .replace("__PRIMARY__", primary)
            .replace("__SECONDARY__", secondary)
            .replace("__PALE__", theme["bright"]))
    for key, value in GALLERY_THEME[brand].items():
        html = html.replace("__BRAND_" + key.upper() + "__", value)
    return html


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
    st.caption("v7.17 · 25 interactive widgets (8 renderer-ready, 17 gallery concepts; 4 map views) · No AI API")

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
    st.subheader("Explore interactive widgets · 25")
    st.write(f"**25 interactive widget cards:** 8 supported by the current renderer and 17 concepts demonstrated in the gallery. All previews use **{brand}** colours and fictional data. Scroll the **page** to trigger animations. `Build (must - ...)` currently accepts only renderer-supported widgets.")
    # Content-height iframe: no cropped 1,440px panel and no nested scrollbar.
    # Streamlit 1.56+ measures the HTML height as widgets reflow on different screens.
    # The gallery JavaScript observes the *parent* page scroll to reveal each widget.
    st.iframe(interactive_gallery_html(brand), width="stretch", height="content")
    st.caption("All numbers in the gallery are fictional examples. The map demonstrates US state boundaries and loads Canadian province/territory boundaries from a public dataset when online and responsive metric panels. The current landing_engine.py supports the original 8 widgets. The 17 newer examples, including world choropleth, travel routes, sparkline KPI, benchmark range and infographic charts, remain gallery-only until the engine and AI blueprint instructions are upgraded. US choropleth is also a gallery-only enhancement.")

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
