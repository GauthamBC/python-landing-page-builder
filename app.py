"""Landing Page Studio v6: Two independent browser tabs, zero AI/API calls.

Streamlit browser tab: select a template/brand, preview with *fictional* demo
numbers, copy the Build instruction, then render the final JSON to one HTML file.
AI browser tab: ChatGPT or Claude Project has the research file and executes
feasibility review -> explicit human approval -> self-contained JSON.
"""
from __future__ import annotations

import base64
import json
import re
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components

from landing_engine import (
    BRANDS, TEMPLATES, WIDGET_TYPES, check_selected_page,
    demo_blueprint, jid, normalize, render, template_selection, validate,
)

st.set_page_config(page_title="Landing Page Studio · v6", page_icon="📐", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.65rem;max-width:1480px}
.stDownloadButton button,.stButton button{font-weight:700}
.stTabs [data-baseweb="tab"]{font-weight:750;font-size:16px}
</style>""", unsafe_allow_html=True)
st.title("Landing Page Studio")
st.caption("Design in Streamlit  →  Research & feasibility in ChatGPT/Claude  →  One final JSON  →  One HTML landing page. No AI APIs.")


def parse_json(text):
    text=text.strip().lstrip("\ufeff")
    match=re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```",text,flags=re.I|re.S)
    if match:
        text=match.group(1)
    try:
        obj=json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(obj,dict):
        raise ValueError("The final blueprint must be a single JSON object.")
    return obj


def require_complete_datasets(raw):
    raw_datasets=raw.get("datasets")
    if raw_datasets is not None:
        if not isinstance(raw_datasets,list) or not raw_datasets:
            raise ValueError("'datasets' must contain at least one ranked worksheet.")
        for i,ds in enumerate(raw_datasets,1):
            if not isinstance(ds,dict) or not isinstance(ds.get("rows"),list) or not ds["rows"]:
                raise ValueError(f"Research dataset {i} has no rows. Return to the AI conversation and regenerate the complete JSON with every ranking record.")
    elif not isinstance(raw.get("rows"),list) or not raw["rows"]:
        raise ValueError("The JSON has no research data. Include actual spreadsheet records inside 'datasets[].rows' or legacy 'rows'.")
    if len(json.dumps(raw,ensure_ascii=False))>22_000_000:
        raise ValueError("JSON exceeds the 22 MB application limit. Reduce the publication dataset in your AI project.")


def brand_lockup():
    theme=BRANDS[st.session_state["studio_brand"]]
    st.markdown(
        '<div style="display:flex;gap:5px;margin:5px 0 10px">' +
        ''.join(f'<span style="display:block;flex:1;height:13px;border-radius:3px;background:{theme[k]}"></span>' for k in ("primary","bright","navy")) +
        '</div>',unsafe_allow_html=True)
    st.caption(theme["note"])

if "studio_brand" not in st.session_state:
    st.session_state["studio_brand"]="Action Network"
if "active_template" not in st.session_state:
    st.session_state["active_template"]="visual_rankings"

with st.sidebar:
    st.header("Brand Settings")
    brand=st.selectbox("Publication Brand",list(BRANDS),key="studio_brand",
        help="This overrides all colors, source brands and logo fields inside the JSON.")
    brand_lockup()
    logo_upload=st.file_uploader("Optional approved brand logo",type=["png","webp","svg"],
        help="This logo will be embedded into the HTML instead of the provisional text lockup.",key="approved_logo")
    logo_uri=None
    if logo_upload:
        ext=logo_upload.name.rsplit('.',1)[-1].lower()
        mime={"svg":"image/svg+xml","png":"image/png","webp":"image/webp"}[ext]
        logo_uri=f"data:{mime};base64,"+base64.b64encode(logo_upload.getvalue()).decode("ascii")
    st.divider()
    st.markdown("**Workflow:**")
    st.caption("1. Choose template here → 2. Copy Build instruction → 3. In a separate ChatGPT or Claude tab upload spreadsheet + paste command → 4. Approve feasibility → 5. Return final JSON here.")
    st.info("The sample previews use invented values. Exact non-AN palettes and official logos need approved assets.")

studio_tab, renderer_tab=st.tabs(["① Template Studio & AI Instruction", "② Final JSON → HTML Generator"])

with studio_tab:
    st.subheader("Choose your page design")
    st.write("Preview the actual animated HTML in the selected brand before you send the build instructions to ChatGPT or Claude.")
    source=st.radio("Design mode",["Default templates","Custom widget builder"],horizontal=True,key="design_source")
    if source=="Default templates":
        st.caption("Each preset has a fixed family of widgets and a distinct editorial arrangement.")
        cards=list(TEMPLATES.items())
        for start in range(0,len(cards),3):
            cols=st.columns(3)
            for col,(ident,item) in zip(cols,cards[start:start+3]):
                with col:
                    with st.container(border=True):
                        st.markdown(f"**{item['name']}**")
                        st.caption(item["description"])
                        st.caption(" · ".join(WIDGET_TYPES[w].split(" ")[0] if False else w.replace("_"," ").title() for w in item["widgets"]))
                        if st.button("Select template" if st.session_state["active_template"]!=ident else "✓ Selected",key=f"pick_{ident}",use_container_width=True):
                            st.session_state["active_template"]=ident
                            st.session_state.pop("approved_build",None)
        template_id=st.session_state["active_template"]
        custom=[]
    else:
        template_id="custom"
        st.markdown("**Build your own widget composition**")
        custom=st.multiselect("Widgets to include",options=list(WIDGET_TYPES),
            default=["ranking","comparison"],format_func=lambda w: w.replace('_',' ').title(),
            help="A full table is automatically included if the chosen widgets do not expose all ranking records.",key="custom_widgets")
        for widget in custom:
            st.caption(f"**{widget.replace('_',' ').title()}:** {WIDGET_TYPES[widget]}")
        st.caption("Note: the pin map requires actual latitude/longitude. AI may recommend removing it after reviewing your dataset.")
    style=st.selectbox("Presentation style",["Default for template","editorial","minimal","bold"],
        help="This changes design density, typography and layout accents, not publication colors.")
    resolved_style=None if style=="Default for template" else style
    try:
        selection=template_selection(template_id,custom_widgets=custom,visual_style=resolved_style)
    except ValueError as exc:
        st.warning(str(exc))
        selection=None

    if selection:
        st.markdown("#### Animated template preview")
        if source=="Custom widget builder":
            st.caption("Change widgets and click Generate Preview to assemble your custom design. This uses sample data only.")
            clicked=st.button("Generate Custom Template Preview",type="primary",key="generate_custom",use_container_width=True)
            if clicked:
                st.session_state["preview_selection"]=selection
            preview_selection=st.session_state.get("preview_selection")
            preview_ready=(preview_selection is not None and preview_selection==selection)
            if not preview_ready:
                st.info("Choose your widgets, then click **Generate Custom Template Preview**.")
        else:
            preview_selection=selection
            preview_ready=True
        if preview_ready:
            demo=demo_blueprint(preview_selection)
            html=render(demo,brand,"selected",logo_uri=logo_uri)
            st.caption("Scroll **inside the preview** to activate reveals and animated charts. 'Replay motion' is included in the preview.")
            components.html(html,height=840,scrolling=True)
            a,b=st.columns([1,2])
            with a:
                st.download_button("Download sample preview HTML",html,
                    file_name=f"DEMO_{template_id}_{jid(brand)}.html",mime="text/html",use_container_width=True)
            with b:
                st.info("Illustrative data only. The finished page's content and widget feasibility are decided in the AI project.")
            st.divider()
            if st.button("Use This Template — Prepare AI Build Instruction",type="primary",use_container_width=True,key="use_design"):
                st.session_state["approved_build"]=selection
            if st.session_state.get("approved_build")==selection:
                command="Build | LP_TEMPLATE_V6="+json.dumps(selection,ensure_ascii=False,separators=(",",":"))
                st.success("Template selected. Copy the complete Build command and paste it into your ChatGPT or Claude Project alongside the research file.")
                st.code(command,language="text",wrap_lines=True)
                st.caption("Use the copy icon in the top-right corner of the code block. No AI API is involved.")
                st.download_button("Download Build Instruction (.txt)",command,file_name="LP_TEMPLATE_V6_Build_Instruction.txt",mime="text/plain",use_container_width=True)
                st.markdown("**AI sequence:** Spreadsheet + Build command → concise widget feasibility report → type `Agreed & Proceed` → one complete downloadable JSON.")

with renderer_tab:
    st.subheader("Generate one final landing page")
    st.write("Upload the **self-contained JSON** returned after 'Agreed & Proceed' in your AI Project. No spreadsheet upload is required here.")
    upload_tab,paste_tab=st.tabs(["Upload final JSON","Paste final JSON"])
    with upload_tab:
        final_upload=st.file_uploader("Complete approved research blueprint",type=["json","txt"],key="final_upload")
    with paste_tab:
        pasted=st.text_area("Paste complete JSON",height=200,key="final_paste",placeholder='{ "template": {"template_id":"visual_rankings", "widgets":["ranking","comparison"]}, "datasets": [...] }')
    incoming=final_upload.getvalue() if final_upload else pasted.encode("utf-8")
    if final_upload is not None and pasted.strip():
        st.caption("Using the uploaded JSON file; pasted text is ignored until the file is removed.")
    if not incoming.strip():
        st.info("Upload or paste your final JSON. The page will render automatically, using the selected brand.")
    else:
        try:
            raw=parse_json(incoming.decode("utf-8-sig"))
            require_complete_datasets(raw)
            spec=normalize(raw)
            check_selected_page(spec)
            warnings=validate(spec)
            html=render(spec,brand,"selected",logo_uri=logo_uri)
            raw_template=(spec.get("template") or {}).get("template_id", "")
            st.success(f"Generated one {brand} landing page using **{raw_template.replace('_',' ').title()}** from {len(spec['datasets'])} dataset(s) and {sum(len(d['rows']) for d in spec['datasets']):,} research rows.")
            for warning in warnings:
                st.warning(warning)
            if raw_template!=st.session_state.get("active_template"):
                st.caption("Layout comes from the approved JSON template, while the selected brand controls the visual identity. You can return to Template Studio to choose another template for a future campaign.")
            base=f"{jid(spec.get('slug') or spec['title'])}-{jid(brand)}-{jid(raw_template)}"
            left,right=st.columns(2)
            with left:
                st.download_button("Download Final Landing Page HTML",html,file_name=f"{base}.html",mime="text/html",use_container_width=True,type="primary")
            with right:
                st.download_button("Download Normalized JSON",json.dumps(spec,ensure_ascii=False,indent=2),file_name=f"{base}.json",mime="application/json",use_container_width=True)
            st.markdown("#### Final animated page preview")
            st.caption("Scroll within the panel to trigger animations; click Replay motion in the page navigation to restart.")
            components.html(html,height=960,scrolling=True)
            st.caption("Publication reminder: verify figures, sources, author attribution, accessibility and mobile view before publishing. Maps and external fonts require internet access.")
        except (ValueError,KeyError,TypeError,UnicodeDecodeError) as exc:
            st.error(f"The JSON cannot be rendered: {exc}")
            st.caption("Return to the same AI conversation and ask it to fix the named field/widget, preserving the original spreadsheet data and approved template.")
        except Exception as exc:
            st.error(f"Unexpected rendering error: {type(exc).__name__}: {exc}")
