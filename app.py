import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
from urllib.parse import urljoin, urlparse
import time

# --- Configuration & Styling ---
st.set_page_config(
    page_title="Luxury Presence QA Co-Pilot",
    page_icon="💎",
    layout="wide"
)

# STRICT Luxury Presence Design System
STYLING_CSS = """
<style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@300;400;700&display=swap');

    /* Global Reset & Background */
    .stApp {
        background-color: #0F0F0F !important;
        color: #FFFFFF !important;
        font-family: 'Lato', sans-serif;
    }

    /* Headers - Serif */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Playfair Display', serif !important;
        color: #FFFFFF !important;
        letter-spacing: 0.5px;
    }
    
    /* Text Input Fields */
    .stTextInput input {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 4px;
    }
    .stTextInput input:focus {
        border-color: #C5A065 !important;
        box-shadow: 0 0 0 1px #C5A065 !important;
    }
    
    /* Primary Buttons */
    div.stButton > button {
        background-color: #C5A065 !important;
        color: #000000 !important;
        font-family: 'Lato', sans-serif !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 0px !important; /* Sharp luxe edges */
        padding: 0.6rem 2rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background-color: #D6B176 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(197, 160, 101, 0.3);
    }
    div.stButton > button:active {
        background-color: #B08D55 !important;
        transform: translateY(0px);
    }

    /* DataFrame Styling */
    [data-testid="stDataFrame"] {
        background-color: #1A1A1A;
        border: 1px solid #333;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #141414 !important;
        border-right: 1px solid #2A2A2A;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #C5A065 !important;
    }
    
    /* Success/Error Alerts */
    .stAlert {
        background-color: #1A1A1A;
        color: #FFF;
        border: 1px solid #333;
    }
</style>
"""
st.markdown(STYLING_CSS, unsafe_allow_html=True)

# --- Helper Functions ---

def init_gemini(api_key):
    """Initializes the Gemini client."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-pro')

def crawl_website(url):
    """Fetches HTML and extracts text and links."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract Visible Text
        for script in soup(["script", "style", "nav", "footer", "header", "noscript"]): # Remove non-content
            script.extract()
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Extract Links
        links = []
        base_domain = urlparse(url).netloc
        for a in soup.find_all('a', href=True):
            href = a['href']
            link_text = a.get_text(strip=True)
            full_url = urljoin(url, href)
            
            # Filter for internal-ish links or relevant ones
            # We want to check logic of navigation, so we skip standard anchors like '#' or javascript:
            if not href.startswith(('javascript:', 'mailto:', 'tel:', '#')) and link_text:
                links.append({
                    'text': link_text,
                    'href': full_url,
                    'raw_href': href
                })
                
        return text_content, links
    except Exception as e:
        return None, str(e)

def chunk_text(text, chunk_size=8000):
    """Chunks text to respect token limits."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def analyze_grammar(model, text_chunk):
    """Checks for spelling/grammar errors."""
    prompt = f"""
    Act as a professional QA Editor for a luxury real estate website.
    Audit the following text for SPELLING and GRAMMAR errors.
    
    RULES:
    1. IGNORE proper nouns, real estate industry terms (e.g., "Realtor", "DRE#", street names).
    2. Focus on embarrassing typos, subject-verb agreement, and punctuation errors.
    3. Output MUST be a list of errors found.
    4. Format format per line: [Type] Original -> Correction
    5. If no errors, return "NO_ERRORS"
    
    TEXT TO AUDIT:
    {text_chunk}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_links_batch(model, links_batch):
    """Checks link logic in batches."""
    link_list_str = "\n".join([f"{i}. Text: '{l['text']}' | Dest: '{l['raw_href']}'" for i, l in enumerate(links_batch)])
    
    prompt = f"""
    Act as a Website Logic Auditor. 
    I will provide a list of links (Link Text and Destination URL).
    For each link, determine if the Link Text logically matches the Destination URL.
    
    Examples:
    - Text: "Contact Us" | Dest: "/contact-us" -> YES
    - Text: "View Properties" | Dest: "/about-me" -> NO (Mismatch)
    - Text: "Home" | Dest: "/" -> YES
    
    Analyze the following list. 
    OUTPUT ONLY the mismatches in this format:
    ID: [ID] | Issue: [Explanation]
    
    If all are correct, return "ALL_CORRECT".
    
    LINKS TO ANALYZE:
    {link_list_str}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- Main Application ---
def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input("Gemini API Key", type="password", help="Get key from Google AI Studio")
        st.markdown("---")
        st.markdown("**/Instructions/**")
        st.markdown("1. Enter API Key.")
        st.markdown("2. Input URL.")
        st.markdown("3. Run Audit.")
        st.markdown("---")
        st.caption("Luxury Presence QA Co-Pilot v1.0")

    # Main Content
    st.title("QA Co-Pilot")
    st.markdown("#### Intelligent Website Audit Tool")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        url_input = st.text_input("Target Website URL", placeholder="https://www.luxurypresence.com")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True) # Spacer
        start_btn = st.button("Start QA Audit", use_container_width=True)

    if start_btn:
        if not api_key:
            st.error("⚠️ API Key is required.")
            return
        if not url_input:
            st.warning("⚠️ Please enter a valid URL.")
            return

        # Initialize
        model = init_gemini(api_key)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results_data = []

        # Step 1: Crawl
        status_text.text("Wait... Crawling website content...")
        progress_bar.progress(10)
        
        text_content, links = crawl_website(url_input)
        
        if links is None: # Error case
            st.error(f"Failed to crawl: {text_content}")
            return
            
        progress_bar.progress(30)
        
        # Step 2: Grammar Check
        status_text.text("Wait... Analyzing Spelling & Grammar...")
        # Check first 5k characters to save time/tokens for demo, or chunk if needed
        grammar_issues = analyze_grammar(model, text_content[:5000])
        
        if "NO_ERRORS" not in grammar_issues:
            for line in grammar_issues.split('\n'):
                if line.strip():
                    results_data.append({
                        "Category": "Spelling/Grammar",
                        "Issue": line,
                        "Context": "Page Content"
                    })
        
        progress_bar.progress(60)
        
        # Step 3: Link Logic Check
        status_text.text(f"Wait... Analyzing {len(links)} Links for Logic...")
        
        # Batch links (take first 30 for demo speed/rate limits)
        target_links = links[:30] 
        link_issues_raw = analyze_links_batch(model, target_links)
        
        if "ALL_CORRECT" not in link_issues_raw:
             for line in link_issues_raw.split('\n'):
                if line.strip() and "ID:" in line:
                    results_data.append({
                        "Category": "Link Logic",
                        "Issue": line.split("| Issue:")[-1].strip(),
                        "Context": "Navigation"
                    })

        progress_bar.progress(100)
        status_text.text("Audit Complete.")
        time.sleep(1)
        status_text.empty()
        
        # Display Results
        st.divider()
        st.header("Audit Results")
        
        if results_data:
            df = pd.DataFrame(results_data)
            st.dataframe(df, use_container_width=True)
            
            # Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Report (CSV)",
                data=csv,
                file_name="qa_audit_report.csv",
                mime="text/csv"
            )
        else:
            st.success("✨ No issues found! The site looks clean.")

if __name__ == "__main__":
    main()
