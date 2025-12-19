import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import json
import time
from urllib.parse import urljoin, urlparse

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

# --- 2. SIDEBAR ---
with st.sidebar:
    try:
        st.image("logo.png", width=170) 
    except:
        st.markdown("## Luxury Presence")

    st.markdown("### Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    
    # NEW: CRAWL LIMIT SETTING
    st.markdown("### Scan Settings")
    max_pages = st.slider("Max Pages to Scan", min_value=1, max_value=10, value=3, help="Higher = Slower but more complete.")
    
    st.markdown("---")
    dark_mode = st.toggle("Dark Mode", value=False)
    st.markdown("---")
    st.markdown('<p style="color: #666; font-size: 0.8rem;">PFT | v4.0 (Multi-Page)</p>', unsafe_allow_html=True)

# --- 3. DYNAMIC STYLING (SAME AS BEFORE) ---
if dark_mode:
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    [data-testid="stAppViewContainer"] {{ background-color: {main_bg} !important; }}
    .main {{ background-color: {main_bg} !important; }}
    .stApp, p, div, input, label, span, h1, h2, h3, h4, strong {{
        font-family: 'ABC Normal', 'Neutral Regular', 'Inter', sans-serif !important;
        color: {text_color};
    }}
    p.subtitle-text {{ color: {subtitle_color} !important; font-size: 1.1rem; font-weight: 300; }}
    [data-testid="stSidebar"] {{ background-color: #0F0F0F !important; border-right: 1px solid #222; }}
    [data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
    [data-testid="stSidebar"] img {{ filter: invert(1) brightness(2); }}
    [data-testid="stSidebar"] .stTextInput > div > div > input {{ background-color: #1A1A1A !important; color: #FFFFFF !important; border: 1px solid #333 !important; }}
    .main .stTextInput > div > div > input {{ background-color: {input_bg} !important; color: {text_color} !important; border: 1px solid {input_border} !important; }}
    
    div.stButton > button, div.stDownloadButton > button {{
        background-color: {button_bg} !important;
        border-radius: 8px;
        padding: 0.6rem 1.8rem;
        font-weight: 500;
        border: 1px solid {button_bg} !important;
        transition: transform 0.1s;
    }}
    div.stButton > button *, div.stDownloadButton > button * {{ color: {button_text} !important; }}
    div.stButton > button:hover, div.stDownloadButton > button:hover {{ transform: translateY(-2px); opacity: 0.9; }}

    .issue-card {{ background-color: {card_issue_bg}; border-left: 4px solid #EF4444; padding: 16px; border-radius: 6px 6px 0 0; }}
    .solution-card {{ background-color: {card_fix_bg}; border-left: 4px solid #22C55E; padding: 16px; border-radius: 0 0 6px 6px; }}
    .block-container {{ padding-top: 6rem; padding-bottom: 3rem; }}
    h3.results-header {{ color: {text_color} !important; margin-top: 2rem; }}
    .page-badge {{ background-color: #333; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-bottom: 8px; display: inline-block; }}
</style>
""", unsafe_allow_html=True)

# --- 4. APP LOGIC ---
st.markdown('<h1 class="main-title">QA Co-Pilot</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Full site audit for PRO WD</p>', unsafe_allow_html=True)
st.write("") 

url_input = st.text_input("Website URL", placeholder="https://presencepreview.site/...")

if st.button("Start Full Audit"):
    if not api_key or not url_input:
        st.error("⚠️ Please provide both an API Key and a URL.")
    else:
        # PROGRESS & SETUP
        progress_bar = st.progress(0, text="Initializing...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        all_issues = []
        visited_urls = set()
        urls_to_visit = [url_input]
        base_domain = urlparse(url_input).netloc
        
        try:
            # --- STEP A: FIND PAGES (Crawl Home) ---
            progress_bar.progress(10, text="🕷️ Mapping website structure...")
            response = requests.get(url_input, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find internal links to add to queue
            for a in soup.find_all('a', href=True):
                link = a['href']
                full_url = urljoin(url_input, link)
                parsed = urlparse(full_url)
                
                # Only internal links, no pdfs/images
                if parsed.netloc == base_domain and full_url not in visited_urls:
                    if not any(x in full_url for x in ['.jpg', '.png', '.pdf', 'mailto:', 'tel:']):
                        if full_url not in urls_to_visit:
                            urls_to_visit.append(full_url)

            # Limit pages
            urls_to_visit = urls_to_visit[:max_pages]
            
            # --- STEP B: LOOP THROUGH PAGES ---
            total_pages = len(urls_to_visit)
            
            for i, page_url in enumerate(urls_to_visit):
                current_step = i + 1
                progress_percent = int(20 + ((current_step / total_pages) * 70))
                progress_bar.progress(progress_percent, text=f"🔍 Analyzing Page {current_step}/{total_pages}: {page_url}...")
                
                try:
                    # Get Page Content
                    page_resp = requests.get(page_url, timeout=10)
                    page_soup = BeautifulSoup(page_resp.content, 'html.parser')
                    visible_text = page_soup.get_text(separator=' ', strip=True)[:10000] # Limit text per page
                    
                    # Extract Page Links for Logic Check
                    page_links = []
                    for a in page_soup.find_all('a', href=True):
                        page_links.append(f"'{a.get_text(strip=True)}' -> '{a['href']}'")
                    links_str = "\n".join(page_links[:30])
                    
                    # AI Audit
                    prompt = f"""
                    Role: QA Specialist for Luxury Presence.
                    Context: Auditing a specific page: {page_url}
                    
                    TEXT CONTENT: {visible_text}
                    LINKS ON PAGE: {links_str}
                    
                    TASK: Find spelling, grammar, and LOGIC errors (e.g. 'Contact' link goes to 'Home').
                    Ignore generic real estate terms.
                    
                    RETURN JSON ONLY:
                    [
                        {{"type": "Spelling", "issue": "Word", "fix": "Correction", "loc": "Section Name"}}
                    ]
                    """
                    
                    ai_resp = model.generate_content(prompt)
                    clean_json = ai_resp.text.replace("```json", "").replace("```", "").strip()
                    page_issues = json.loads(clean_json)
                    
                    # Tag issues with the Page URL
                    for issue in page_issues:
                        issue['page_url'] = page_url
                        all_issues.append(issue)
                        
                except Exception as e:
                    print(f"Skipped page {page_url}: {e}")
                    
                visited_urls.add(page_url)
                time.sleep(0.5) # Polite delay

            # --- STEP C: FINISH ---
            progress_bar.progress(100, text="✅ Full Site Audit Complete!")
            st.session_state.audit_results = all_issues
            time.sleep(1)
            progress_bar.empty()

        except Exception as e:
            st.error(f"Critical Error: {e}")
            progress_bar.empty()

# --- 5. RESULTS ---
if st.session_state.audit_results:
    st.markdown('<h3 class="results-header">Results</h3>', unsafe_allow_html=True)
    results = st.session_state.audit_results
    
    if len(results) == 0:
        st.success("✅ No issues found across scanned pages!")
    
    for i, item in enumerate(results):
        col_check, col_content = st.columns([0.5, 9.5])
        with col_check:
            is_checked = st.checkbox("", key=f"check_{i}")
        with col_content:
            opacity = "0.4" if is_checked else "1.0"
            
            # Show Page URL badge if it exists
            page_badge = f'<div class="page-badge">📄 {item.get("page_url", "Unknown Page")}</div>'
            
            st.markdown(f"""
            <div style="opacity: {opacity}; margin-bottom: 20px;">
                {page_badge}
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
        st.markdown('<div class="download-container">', unsafe_allow_html=True)
        st.download_button(
            "Download Master Report (CSV)", 
            pd.DataFrame(results).to_csv(index=False).encode('utf-8'), 
            "full_audit.csv", 
            "text/csv"
        )
        st.markdown('</div>', unsafe_allow_html=True)
