"""Landing Page Studio v7.8 - Build / Widgets / Outputs.

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

</style></head><body>
<header><div><div class="eyebrow">Interactive widget gallery</div><div class="headbrand"><span>●</span> __BRAND__ <span style="color:#738f9d">/ Live previews</span></div></div><button class="replay" type="button" id="replay" aria-label="Replay chart animations">↻ Replay animations</button></header>
<div class="gallery" id="gallery">
<section class="widget feature reveal" data-widget="map">
<div class="widget-head"><div><div class="eyebrow">Geographic storytelling / interactive</div><div class="widget-title" style="font-size:clamp(20px,2.8vw,32px);margin-top:7px">Animated US state explorer</div><div class="widget-description">Hover over a state to reveal its score and breakdown. Tap to inspect on touchscreens. Alaska and Hawaii appear as insets.</div></div><span class="tag">Build (must - map)</span></div>
<div class="widget-body"><div class="atlas-stage" id="atlasStage">
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
</div></div></section>
<section class="widget reveal" data-widget="table_ranking"><div class="widget-head"><div><div class="widget-title">Ranking table</div><div class="widget-description">Search the sample data or sort by rank, place or score.</div></div><span class="tag">Build (must - ranking table)</span></div><div class="widget-body"><div class="mini-tools"><input class="search" id="tableSearch" type="search" placeholder="Search locations…" aria-label="Search demo ranking table"></div><table><thead><tr><th data-sort="rank"># ↕</th><th data-sort="city">Location ↕</th><th data-sort="score">Score ↕</th></tr></thead><tbody id="tableRows"></tbody></table><div class="tab-foot" id="tableStatus">Showing 5 demo rows</div></div></section>
<section class="widget reveal" data-widget="ranking"><div class="widget-head"><div><div class="widget-title">Animated ranking bars</div><div class="widget-description">Rows and bars reveal smoothly; hover for individual scores.</div></div><span class="tag">Build (must - bar chart)</span></div><div class="widget-body" id="bars"><div class="bar-row" title="Seattle: 92.4"><span class="bar-name">Seattle</span><div class="bar-track"><div class="bar-fill" style="--value:92.4%;--delay:80ms"></div></div><strong class="bar-amt">92.4</strong></div><div class="bar-row" title="Denver: 88.7"><span class="bar-name">Denver</span><div class="bar-track"><div class="bar-fill" style="--value:88.7%;--delay:160ms"></div></div><strong class="bar-amt">88.7</strong></div><div class="bar-row" title="Austin: 85.3"><span class="bar-name">Austin</span><div class="bar-track"><div class="bar-fill" style="--value:85.3%;--delay:240ms"></div></div><strong class="bar-amt">85.3</strong></div><div class="bar-row" title="Atlanta: 81.5"><span class="bar-name">Atlanta</span><div class="bar-track"><div class="bar-fill" style="--value:81.5%;--delay:320ms"></div></div><strong class="bar-amt">81.5</strong></div><div class="bar-row" title="Boston: 78.9"><span class="bar-name">Boston</span><div class="bar-track"><div class="bar-fill" style="--value:78.9%;--delay:400ms"></div></div><strong class="bar-amt">78.9</strong></div><div class="chart-axis"><span>0</span><span>Illustrative index score / 100</span><span>100</span></div></div></section>
<section class="widget reveal" data-widget="comparison"><div class="widget-head"><div><div class="widget-title">Side-by-side comparison</div><div class="widget-description">Select either city to highlight its comparative result.</div></div><span class="tag">Build (must - comparison)</span></div><div class="widget-body"><div class="metric-split"><button class="measure selected" data-city="Seattle"><div class="m-label">Seattle</div><div class="m-number">92.4</div><div class="m-bar"><span style="--value:92.4%"></span></div><div class="m-note">Index score</div></button><button class="measure" data-city="Denver"><div class="m-label">Denver</div><div class="m-number">88.7</div><div class="m-bar"><span style="--value:88.7%"></span></div><div class="m-note">Index score</div></button></div><div class="compare-summary" id="compareSummary">Seattle is 3.7 points higher than Denver in this fictional example.</div></div></section>
<section class="widget reveal" data-widget="scatter"><div class="widget-head"><div><div class="widget-title">Scatterplot</div><div class="widget-description">Hover over points to explore the relationship between two measures.</div></div><span class="tag">Build (must - scatterplot)</span></div><div class="widget-body"><svg class="scatter-svg" viewBox="0 0 450 215" role="img" aria-label="Scatterplot comparing fictional access and index scores"><g class="scatter-grid"><path d="M45 20H432 M45 68H432 M45 116H432 M45 164H432 M45 20V183 M144 20V183 M243 20V183 M342 20V183 M432 20V183"/></g><path class="scatter-trend" d="M53 166L420 35"/><g id="plotPoints"></g><g class="scatter-label"><text x="45" y="208">Lower access</text><text x="353" y="208">Higher access</text><text x="8" y="18">Score</text></g></svg><div class="tooltip" id="scatterTooltip" aria-live="polite">Hover over a plotted location for details.</div></div></section>
<section class="widget reveal" data-widget="heatmap"><div class="widget-head"><div><div class="widget-title">Metric heatmap</div><div class="widget-description">Hover over any cell to reveal its illustrative value.</div></div><span class="tag">Build (must - heatmap)</span></div><div class="widget-body"><div class="heat-grid" id="heatGrid"></div><div class="tooltip" id="heatTooltip" aria-live="polite">Hover over a square to inspect a value.</div></div></section>
<section class="widget reveal" data-widget="metric_cards"><div class="widget-head"><div><div class="widget-title">Metric cards</div><div class="widget-description">Animated, clearly labelled headline figures.</div></div><span class="tag">Build (must - metric cards)</span></div><div class="widget-body"><div class="stat-grid"><div class="stat"><div class="number" data-count="5">5</div><div class="stat-name">Locations</div></div><div class="stat"><div class="number" data-count="92.4">92.4</div><div class="stat-name">Highest score</div></div><div class="stat"><div class="number" data-count="13.5">13.5</div><div class="stat-name">Score spread</div></div></div><div class="stat-note">Values are illustrative. The published landing page will use verified research figures.</div></div></section>
<section class="widget reveal" data-widget="callout"><div class="widget-head"><div><div class="widget-title">Editorial callout</div><div class="widget-description">A focused, branded explanation that connects the data to the story.</div></div><span class="tag">Build (must - callout)</span></div><div class="widget-body"><div class="callout"><div class="eyebrow" style="margin-bottom:11px">Research insight</div><h4>What makes the top-ranked location stand out?</h4><p>A short editorial interpretation that explains the underlying factors, rather than simply repeating a ranking number. This is placeholder copy and not a real study finding.</p></div></div></section>
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
let galleryObserver=null;
function animate(){
  if(galleryObserver){galleryObserver.disconnect();galleryObserver=null;}
  ++numberRun;
  all('.widget').forEach(el=>{el.classList.remove('shown','animated');});
  all('.stat .number').forEach(el=>el.textContent='0');
  hideState();tapSelection=false;
  // A layout read separates resetting from the replay, allowing CSS animations to restart.
  void document.body.offsetHeight;
  const reveal=el=>{
    el.classList.add('shown','animated');
    if(el.dataset.widget==='metric_cards'&&!matchMedia('(prefers-reduced-motion: reduce)').matches)animateNumbers();
    else if(el.dataset.widget==='metric_cards')all('.stat .number').forEach(n=>n.textContent=n.dataset.count);
  };
  if(matchMedia('(prefers-reduced-motion: reduce)').matches){all('.widget').forEach(reveal);return;}
  if('IntersectionObserver' in window){
    galleryObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{
      if(entry.isIntersecting){reveal(entry.target);galleryObserver?.unobserve(entry.target);}
    }),{threshold:.09,rootMargin:'0px 0px -22px 0px'});
    all('.widget').forEach(el=>galleryObserver.observe(el));
  } else all('.widget').forEach(reveal);
}
$('#replay').addEventListener('click',animate);
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
    st.caption("v7.8 · Fully branded animated gallery · No AI API · Existing landing_engine.py and requirements.txt unchanged")

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
    st.subheader("Explore interactive widgets")
    st.write(f"Live examples styled for **{brand}**. Hover, search, click, and inspect the animations. Use a widget name in `Build (must - ...)` to require it in every version.")
    components.html(interactive_gallery_html(brand), height=2400, scrolling=True)
    st.caption("All numbers in the gallery are fictional examples. The map demonstrates accurate US state boundaries with a fictional choropleth and responsive metric panels. The current landing_engine.py uses interactive Leaflet pin maps; bespoke geographic choropleths and advanced map storytelling need a separate engine update.")

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
