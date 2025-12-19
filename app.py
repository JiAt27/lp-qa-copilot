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

# --- 2. LUXURY PRESENCE BRAND STYLING (Onboarding Hub Theme) ---
st.markdown("""
<style>
    /* IMPORT FONTS: Inter (UI) and Playfair Display (Headers) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@600;700&display=swap');

    /* BASE THEME - LIGHT MODE */
    .stApp {
        background-color: #FFFFFF;
        color: #111111;
        font-family: 'Inter', sans-serif;
    }

    /* TYPOGRAPHY */
    h1 {
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 2.2rem;
        color: #000000;
        margin-bottom: 0rem;
    }
    
    /* REMOVE DEFAULT STREAMLIT PADDING */
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
    }

    /* BUTTONS - BLACK PILL SHAPE */
    div.stButton > button {
        background-color: #000000;
        color: #FFFFFF;
        border-radius: 8px;
        padding: 0.6rem 1.8rem;
        font-weight: 500;
        font-size: 0.95rem;
        border: 1px solid #000000;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #333333;
        border-color: #333333;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* INPUT FIELDS */
    .stTextInput > div > div > input {
        background-color: #F9FAFB;
        color: #111111;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 0.5rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: #000000;
        box-shadow: none;
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
        font-family: 'Inter', monospace;
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

    /* CHECKBOX ALIGNMENT */
    .stCheckbox {
        padding-top: 30px; 
    }
    
    /* LINK STYLING */
    a { color: #666; text-decoration: none; }
    a:hover { text-decoration: underline; color: #000; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    # LOGO HANDLING
    try:
        st.image("logo.png", width=160) 
    except:
        # Fallback if you forget to upload the file
        st.markdown("## Luxury Presence")

    st.markdown("### Configuration")
    
    # API Key with Helper Link
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown(
        """<div style="margin-top: -10px; margin-bottom: 20px; font-size: 0.85rem;">
        👉 <a href="https://aistudio.google.com/app/apikey" target="_blank">Get your API Key here</a>
        </div>""", 
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    st.caption("PFT | v2.0")

# --- 4. MAIN INTERFACE ---
st.title("QA Co-Pilot")

# Spacer
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
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # CRAWL
                response = requests.get(url_input, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                visible_text = soup.get_text(separator=' ', strip=True)[:15000]
                
                links = []
                for a in soup.find_all('a', href=True):
                    links.append(f"'{a.get_text(strip=True)}' -> '{a['href']}'")
                links_str = "\n".join(links[:50])

                # ANALYZE (JSON OUTPUT)
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

# --- 5. DISPLAY RESULTS (Interactive Cards) ---
if st.session_state.audit_results:
    st.markdown("### Results")
    results = st.session_state.audit_results
    
    if len(results) == 0:
        st.success("✅ No issues found!")
    
    for i, item in enumerate(results):
        col_check, col_content = st.columns([0.5, 9.5])
        
        with col_check:
            # Unique key ensures state is remembered
            is_checked = st.checkbox("", key=f"fix_{i}")
        
        with col_content:
            # Dim the card if checked
            opacity = "0.4" if is_checked else "1.0"
            
            st.markdown(f"""
            <div style="opacity: {opacity}; margin-bottom: 20px;">
                <div class="issue-card">
                    <span class="card-label">🔴 {item['type']} • {item['loc']}</span>
                    <strong>{item['issue']}</strong>
                </div>
                <div class="solution-card">
                    <span class="card-label">🟢 SUGGESTED FIX</span>
                    {item['fix']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # DOWNLOAD
    if results:
        st.download_button(
            "Download CSV", 
            pd.DataFrame(results).to_csv(index=False).encode('utf-8'), 
            "audit.csv", 
            "text/csv"
        )
