import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import json

# --- 1. CONFIGURATION & STATE MANAGEMENT ---
st.set_page_config(page_title="LP QA Co-Pilot", layout="wide", initial_sidebar_state="expanded")

# Initialize Session State to keep results in memory when checking boxes
if 'audit_results' not in st.session_state:
    st.session_state.audit_results = None

# --- 2. LUXURY PRESENCE "ONBOARDING HUB" STYLING ---
st.markdown("""
<style>
    /* IMPORT FONTS (Inter for UI, Playfair for Logo) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:wght@700&display=swap');

    /* MAIN THEME - LIGHT MODE */
    .stApp {
        background-color: #FFFFFF;
        color: #111111;
        font-family: 'Inter', sans-serif;
    }

    /* LOGO STYLING */
    .lp-logo {
        font-family: 'Playfair Display', serif;
        font-size: 24px;
        font-weight: 700;
        color: #000000;
        margin-bottom: 20px;
    }

    /* HEADERS */
    h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        color: #000000;
        letter-spacing: -1px;
    }
    .subtitle {
        color: #666666;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    /* BUTTONS (Black like 'Mark as complete') */
    div.stButton > button {
        background-color: #000000;
        color: #FFFFFF;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        border: 1px solid #000000;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #333333;
        border-color: #333333;
        color: #FFFFFF;
    }

    /* INPUT FIELDS (Light Gray Background) */
    .stTextInput > div > div > input {
        background-color: #F7F7F7;
        color: #000000;
        border: 1px solid #E5E5E5;
        border-radius: 6px;
    }

    /* RESULT CARDS */
    .issue-box {
        background-color: #FFF5F5; /* Light Red */
        border-left: 4px solid #E53E3E;
        padding: 15px;
        border-radius: 4px 4px 0 0;
        color: #9B2C2C;
    }
    .fix-box {
        background-color: #F0FFF4; /* Light Green */
        border-left: 4px solid #38A169;
        padding: 15px;
        border-radius: 0 0 4px 4px;
        color: #22543D;
        font-family: monospace;
        font-size: 0.9rem;
    }
    .card-label {
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-bottom: 5px;
        display: block;
    }
    
    /* CHECKBOX STYLING */
    .stCheckbox {
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    # Simulated Logo
    st.markdown('<div class="lp-logo">Luxury Presence</div>', unsafe_allow_html=True)
    
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.markdown("---")
    st.markdown("**Build for PFT**")
    st.caption("v1.2 | Internal Tool")

# --- 4. MAIN INTERFACE ---
st.title("Luxury Presence QA Co-Pilot")
st.markdown('<div class="subtitle">Automated spelling, grammar and broken links audit for PRO WD</div>', unsafe_allow_html=True)

url_input = st.text_input("Website URL", placeholder="https://...")

# Action Button
if st.button("Start Audit"):
    if not api_key or not url_input:
        st.error("Please provide both an API Key and a URL.")
    else:
        # --- THE CRAWLER & AI LOGIC ---
        with st.spinner("Analyzing site structure and content..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash') # Stable Model
                
                # Crawl
                response = requests.get(url_input, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                visible_text = soup.get_text(separator=' ', strip=True)[:15000]
                
                links = []
                for a in soup.find_all('a', href=True):
                    links.append(f"Text: '{a.get_text(strip=True)}' -> Dest: '{a['href']}'")
                links_str = "\n".join(links[:60])

                # Prompt
                prompt = f"""
                Act as a QA Specialist. Analyze this website content:
                {visible_text}
                
                And these links:
                {links_str}
                
                Identify:
                1. Spelling/Grammar errors (Ignore real estate terms like 'Realtor', 'MLS').
                2. BROKEN LOGIC in links (e.g. 'Contact' link going to 'Home' page).
                
                Return JSON ONLY:
                [
                    {{"type": "Spelling", "issue": "Wrng word", "fix": "Wrong word", "loc": "Hero Section"}},
                    {{"type": "Link Logic", "issue": "Link 'About' goes to /contact", "fix": "Update href to /about", "loc": "Nav"}}
                ]
                """
                
                result = model.generate_content(prompt)
                clean_json = result.text.replace("```json", "").replace("```", "").strip()
                
                # Save to Session State (Memory)
                st.session_state.audit_results = json.loads(clean_json)
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. DISPLAY RESULTS FROM MEMORY ---
if st.session_state.audit_results:
    st.markdown("### 📝 Audit Results")
    st.markdown("---")
    
    # Create a counter for fixed items
    results = st.session_state.audit_results
    
    for i, item in enumerate(results):
        col1, col2 = st.columns([0.5, 9.5])
        
        with col1:
            # Checkbox with unique key
            fixed = st.checkbox("", key=f"check_{i}")
        
        with col2:
            # Opacity change if checked
            opacity = "0.5" if fixed else "1.0"
            
            st.markdown(f"""
            <div style="opacity: {opacity}; margin-bottom: 20px;">
                <div class="issue-box">
                    <span class="card-label">🔴 {item['type']} • {item['loc']}</span>
                    <strong>ISSUE:</strong> {item['issue']}
                </div>
                <div class="fix-box">
                    <span class="card-label">🟢 SUGGESTED FIX</span>
                    {item['fix']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Download Button
    if results:
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Report (CSV)", csv, "audit_report.csv", "text/csv")
