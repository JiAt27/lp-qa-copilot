import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import json

# --- 1. CONFIGURATION & STATE ---
st.set_page_config(
    page_title="LP QA Co-Pilot", 
    page_icon="✨",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize Memory
if 'audit_results' not in st.session_state:
    st.session_state.audit_results = None

# --- 2. LUXURY PRESENCE BRAND STYLING (Modern Sans Theme) ---
st.markdown("""
<style>
    /* IMPORT FONTS: Inter (as the reliable web-safe fallback) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    /* --- TYPOGRAPHY STACK --- */
    /* Prioritizing the ABC fonts you requested, falling back to Inter */
    
    /* BODY / NORMAL TEXT */
    .stApp, p, div, input, label {
        font-family: 'ABC Normal', 'Neutral Regular', 'Inter', sans-serif !important;
        color: #111111;
    }

    /* HEADERS */
    h1, h2, h3, h4, strong {
        font-family: 'ABC Medium', 'Inter', sans-serif !important;
        font-weight: 600;
        color: #000000;
        letter-spacing: -0.02em; /* Tighter tracking for that modern look */
    }

    /* --- SIDEBAR (Dark/Premium) --- */
    [data-testid="stSidebar"] {
        background-color: #0F0F0F; 
        border-right: 1px solid #222;
    }
    
    /* SIDEBAR TEXT OVERRIDE */
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    
    /* LOGO INVERSION (Black PNG -> White) */
    [data-testid="stSidebar"] img {
        filter: invert(1) brightness(2);
    }

    /* SIDEBAR INPUTS */
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #1A1A1A;
        color: #FFFFFF;
        border: 1px solid #333;
    }

    /* --- UI ELEMENTS --- */
    
    h1 {
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    
    /* REMOVE PADDING */
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }

    /* BUTTONS - BLACK PILL SHAPE */
    div.stButton > button {
        background-color: #000000;
        color: #FFFFFF;
        border-radius: 8px;
        padding: 0.6rem 1.8rem;
        font-family: 'ABC Medium', 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.95rem;
        border: 1px solid #000000;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #333333;
        border-color: #333333;
        transform: translateY(-1px);
    }

    /* MAIN INPUT FIELDS */
    .main .stTextInput > div > div > input {
        background-color: #F9FAFB;
        color: #111111;
        border: 1px solid #E5E7EB;
        padding: 0.5rem;
    }

    /* ISSUE CARDS (RED) */
    .issue-card {
        background-color: #FEF2F2;
        border: 1px solid #FEE2E2;
        border-left: 4px solid #EF4444;
        padding: 16px;
        border-radius: 6px 6px 0 0;
        color: #991B1B;
    }
    
    /* SOLUTION CARDS (GREEN) */
    .solution-card {
        background-color: #F0FDF4;
        border: 1px solid #DCFCE7;
        border-left: 4px solid #22C55E;
        border-top: none;
        padding: 16px;
        border-radius: 0 0 6px 6px;
        color: #166534;
        font-family: 'ABC Normal', 'Inter', monospace;
        font-size: 0.9rem;
    }

    /* LABELS */
    .card-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 700;
        margin-bottom: 4px;
        display: block;
        opacity: 0.8;
    }

    .stCheckbox { padding-top: 30px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    # LOGO: Max width set to 170px as requested
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
    st.markdown('<p style="color: #666; font-size: 0.8rem;">PFT | v2.2</p>', unsafe_allow_html=True)

# --- 4. MAIN INTERFACE ---
st.title("QA Co-Pilot")
st.markdown('<p style="color: #666; font-size: 1.1rem; font-weight: 300;">Automated audit for PRO WD</p>', unsafe_allow_html=True)

st.markdown("##") 

url_input = st.text_input("Website URL", placeholder="https://presencepreview.site/...")

# ACTION BUTTON
if st.button("Start Audit"):
    if not api_key or not url_input:
        st.error("⚠️ Please provide both an API Key and a URL.")
    else:
        with st.spinner("Analyzing content & logic..."):
            try:
                genai.configure(api_key=api_key)
                # Using the stable 1.5-flash model
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # CRAWL
                response = requests.get(url_input, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                visible_text = soup.get_text(separator=' ', strip=True)[:15000]
                
                links = []
                for a in soup.find_all('a', href=True):
                    links.append(f"'{a.get_text(strip=True)}' -> '{a['href']}'")
                links_str = "\n".join(links[:50])

                # ANALYZE
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
                clean_json = result.text.replace("```json", "").replace("```", "").strip()
                st.session_state.audit_results = json.loads(clean_json)
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. RESULTS ---
if st.session_state.audit_results:
    st.markdown("### Results")
    results = st.session_state.audit_results
    
    if len(results) == 0:
        st.success("✅ No issues found!")
    
    for i, item in enumerate(results):
