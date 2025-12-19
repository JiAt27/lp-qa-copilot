import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STATE ---
st.set_page_config(
    page_title="LP QA Co-Pilot", 
    page_icon="✨",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize Memory
if 'audit_results' not in st.session_state:
    st.session_state.audit_results = []

# --- 2. SIDEBAR CONFIGURATION ---
with st.sidebar:
    # LOGO HANDLING
    try:
        st.image("logo.png", width=170) 
    except:
        st.markdown("## Luxury Presence")

    st.markdown("### Configuration")
    
    # API Key
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown(
        """<div style="margin-top: -10px; margin-bottom: 20px; font-size: 0.85rem;">
        👉 <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #CCC; text-decoration: underline;">Get your API Key here</a>
        </div>""", 
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # THEME TOGGLE
    dark_mode = st.toggle("Dark Mode", value=False)
    
    st.markdown("---")
    st.markdown('<p style="color: #666; font-size: 0.8rem;">PFT | v3.3</p>', unsafe_allow_html=True)

# --- 3. DYNAMIC CSS STYLING ---
if dark_mode:
    # DARK MODE PALETTE
    main_bg = "#0F0F0F"
    text_color = "#FFFFFF"
    input_bg = "#1A1A1A"
    input_border = "#333333"
    card_issue_bg = "#2A1C1C"
    card_issue_text = "#FCA5A5"
    card_fix_bg = "#1C2A21"
    card_fix_text = "#86EFAC"
    button_bg = "#C5A065" 
    button_text = "#000000"
    subtitle_color = "#AAAAAA"
else:
    # LIGHT MODE PALETTE (Default)
    main_bg = "#FFFFFF"
    text_color = "#111111"
    input_bg = "#F9FAFB"
    input_border = "#E5E7EB"
    card_issue_bg = "#FEF2F2"
    card_issue_text = "#991B1B"
    card_fix_bg = "#F0FDF4"
    card_fix_text = "#166534"
    button_bg = "#000000"
    button_text = "#FFFFFF"
    subtitle_color = "#666666"

st.markdown(f"""
<style>
    /* IMPORT FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    /* --- MAIN CONTAINER THEME --- */
    [data-testid="stAppViewContainer"] {{
        background-color: {main_bg} !important;
    }}
    .main {{
        background-color: {main_bg} !important;
    }}

    /* --- TYPOGRAPHY --- */
    .stApp, p, div, input, label, span, h1, h2, h3, h4, strong {{
        font-family: 'ABC Normal', 'Neutral Regular', 'Inter', sans-serif !important;
        color: {text_color};
    }}
    
    p.subtitle-text {{
        color: {subtitle_color} !important;
        font-size: 1.1rem;
        font-weight: 300;
    }}

    /* --- SIDEBAR (Always Dark) --- */
    [data-testid="stSidebar"] {{
        background-color: #0F0F0F !important; 
        border-right: 1px solid #222;
    }}
    [data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
    [data-testid="stSidebar"] img {{ filter: invert(1) brightness(2); }}
    [data-testid="stSidebar"] .stTextInput > div > div > input {{
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: 1px solid #333 !important;
    }}

    /* --- INPUT FIELDS --- */
    .main .stTextInput > div > div > input {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid {input_border} !important;
    }}

    /* --- BUTTONS (Fix for BOTH Normal and Download Buttons) --- */
    div.stButton > button, div.stDownloadButton > button {{
        background-color: {button_bg} !important;
        border-radius: 8px;
        padding: 0.6rem 1.8rem;
        font-weight: 500;
        border: 1px solid {button_bg} !important;
        transition: transform 0.1s;
    }}
    /* Force ALL text inside buttons to match the button_text color */
    div.stButton > button *, div.stDownloadButton > button * {{
        color: {button_text} !important;
    }}
    div.stButton > button:hover, div.stDownloadButton > button:hover {{
        transform: translateY(-2px);
        opacity: 0.9;
    }}

    /* --- CARDS --- */
    .issue-card {{
        background-color: {card_issue_bg};
        border-left: 4px solid #EF4444;
        padding: 16px;
        border-radius: 6px 6px 0 0;
    }}
    .solution-card {{
        background-color: {card_fix_bg};
        border-left: 4px solid #22C55E;
        padding: 16px;
        border-radius: 0 0 6px 6px;
    }}
    
    /* --- PADDING & SPACING --- */
    .block-container {{ padding-top: 6rem; padding-bottom: 3rem; }}
    
    h3.results-header {{ color: {text_color} !important; margin-top: 2rem; }}
</style>
""", unsafe_allow_html=True)

# --- 4. MAIN INTERFACE ---
st.markdown('<h1 class="main-title">QA Co-Pilot</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Automated audit for PRO WD</p>', unsafe_allow_html=True)

st.write("") 
st.write("") 

url_input = st.text_input("Website URL", placeholder="https://presencepreview.site/...")

# ACTION BUTTON
if st.button("Start Audit"):
    if not api_key or not url_input:
        st.error("⚠️ Please provide both an API Key and a URL.")
    else:
        # PROGRESS BAR INITIALIZATION
        progress_bar = st.progress(0, text="Initializing...")
        
        try:
            # STEP 1: SETUP (10%)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            progress_bar.progress(10, text="⚙️ AI Brain Ready...")
            
            # STEP 2: CRAWL (40%)
            progress_bar.progress(20, text="🕷️ Crawling website content...")
            response = requests.get(url_input, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            visible_text = soup.get_text(separator=' ', strip=True)[:15000]
            progress_bar.progress(40, text="📖 Extracting text and links...")
            
            links = []
            for a in soup.find_all('a', href=True):
                links.append(f"'{a.get_text(strip=True)}' -> '{a['href']}'")
            links_str = "\n".join(links[:50])

            # STEP 3: ANALYZE (70%)
            progress_bar.progress(60, text="🧠 Analyzing logic with Gemini...")
            prompt = f"""
            You are a QA Specialist for Luxury Presence.
            Analyze this website text and links.
            
            TEXT: {visible_text}
            LINKS: {links_str}
            
            TASK: Find spelling errors, grammar issues, and BROKEN LOGIC (e.g. 'Contact' link goes to 'Home').
            Ignore generic real estate terms.
            
            RETURN JSON ONLY:
            [
                {{"type": "Spelling", "issue": "Word", "fix": "Correction", "loc": "Section Name"}},
                {{"type": "Logic", "issue": "Link mismatch", "fix": "Change href", "loc": "Footer"}}
            ]
            """
            
            result = model.generate_content(prompt)
            progress_bar.progress(85, text="✨ Formatting results...")
            
            # STEP 4: FINISH (100%)
            clean_json = result.text.replace("```json", "").replace("```", "").strip()
            st.session_state.audit_results = json.loads(clean_json)
            progress_bar.progress(100, text="✅ Audit Complete!")
            time.sleep(0.5) # Small pause to see 100%
            progress_bar.empty() # Remove bar to show results cleanly
            
        except Exception as e:
            st.error(f"Error: {e}")
            progress_bar.empty()

# --- 5. RESULTS ---
if st.session_state.audit_results:
    st.markdown('<h3 class="results-header">Results</h3>', unsafe_allow_html=True)
    results = st.session_state.audit_results
    
    if len(results) == 0:
        st.success("✅ No issues found!")
    
    for i, item in enumerate(results):
        col_check, col_content = st.columns([0.5, 9.5])
        with col_check:
            is_checked = st.checkbox("", key=f"check_{i}")
        with col_content:
            opacity = "0.4" if is_checked else "1.0"
            st.markdown(f"""
            <div style="opacity: {opacity}; margin-bottom: 20px;">
                <div class="issue-card">
                    <span class="card-label" style="color:{card_issue_text};">🔴 {item['type']} • {item['loc']}</span>
                    <div style="color:{card_issue_text}; font-weight:600;">{item['issue']}</div>
                </div>
                <div class="solution-card">
                    <span class="card-label" style="color:{card_fix_text};">🟢 SUGGESTED FIX</span>
                    <div style="color:{card_fix_text}; font-family:monospace;">{item['fix']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if results:
        # Added container to ensure button style applies
        st.markdown('<div class="download-container">', unsafe_allow_html=True)
        st.download_button(
            "Download CSV", 
            pd.DataFrame(results).to_csv(index=False).encode('utf-8'), 
            "audit.csv", 
            "text/csv"
        )
        st.markdown('</div>', unsafe_allow_html=True)
