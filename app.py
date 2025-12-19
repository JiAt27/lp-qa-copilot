import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import json

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="LP QA Co-Pilot", layout="wide")

# Custom CSS to match Luxury Presence Brand Identity
st.markdown("""
<style>
    /* IMPORT FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');

    /* BACKGROUND & MAIN THEME */
    .stApp {
        background-color: #0F0F0F;
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
    }
    
    /* HEADERS (Serif, High-End) */
    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #FFFFFF !important;
        font-weight: 600;
    }
    
    /* BUTTON STYLING (Gold) */
    div.stButton > button {
        background-color: #C5A065;
        color: #000000;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 2px;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #D4B075;
        color: #000000;
        box-shadow: 0 4px 15px rgba(197, 160, 101, 0.3);
    }

    /* CARD DESIGN FOR RESULTS */
    .audit-card {
        background-color: #1A1A1A;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 4px;
        margin-bottom: 15px;
        border-left: 4px solid #C5A065;
    }
    .audit-card h4 {
        font-family: 'Playfair Display', serif;
        margin-top: 0;
        color: #C5A065;
        font-size: 1.2rem;
    }
    .audit-meta {
        font-size: 0.85rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .audit-fix {
        background-color: #252525;
        padding: 10px;
        border-radius: 4px;
        margin-top: 10px;
        font-family: monospace;
        color: #8FBC8F; /* Soft green for fixes */
    }

    /* INPUT FIELDS */
    .stTextInput > div > div > input {
        background-color: #1A1A1A;
        color: white;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR CONFIG ---
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password", help="Enter your Google AI Studio Key")
    st.markdown("---")
    st.markdown("*Built for the Product Fulfillment Team*")

# --- 3. MAIN APP LAYOUT ---
st.title("Luxury Presence QA Co-Pilot")
st.markdown("Automated design & logic audit for pro websites.")

url_input = st.text_input("Enter Website URL to Audit", placeholder="https://...")

# --- 4. CORE LOGIC ---
if st.button("RUN AUDIT") and url_input and api_key:
    
    # 1. SETUP MODEL
    try:
        genai.configure(api_key=api_key)
        # Using the latest available flash model
        model = genai.GenerativeModel('gemini-2.5-flash') 
        # If 2.0 fails, fallback to 1.5 in your mind, but 2.0-flash-exp is current bleeding edge speed
    except Exception as e:
        st.error(f"API Key Error: {e}")
        st.stop()

    with st.spinner("🕷️ Crawling site and analyzing logic..."):
        try:
            # A. CRAWL SITE
            response = requests.get(url_input, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract Text
            visible_text = soup.get_text(separator=' ', strip=True)[:10000] # Limit char count for speed
            
            # Extract Links for Logic Check
            links = []
            for a in soup.find_all('a', href=True):
                links.append(f"Text: '{a.get_text(strip=True)}' -> Dest: '{a['href']}'")
            links_str = "\n".join(links[:50]) # Limit to top 50 links
            
            # B. AI PROMPT (Structured Output)
            prompt = f"""
            Act as a Senior QA Specialist for Luxury Presence. 
            Analyze the following website content and navigation links.
            
            CONTENT TO ANALYZE:
            {visible_text}
            
            LINKS TO ANALYZE:
            {links_str}
            
            TASK:
            Identify spelling errors, grammar issues, and LOGICAL link errors (e.g., a link says "Team" but goes to "/contact").
            Ignore generic real estate terms or proper nouns.
            
            OUTPUT FORMAT:
            Return a purely JSON array of objects. Do not use Markdown formatting.
            Each object must have:
            - "category": "Spelling", "Grammar", or "Logic"
            - "issue": The specific error found.
            - "fix": The corrected text or suggested link fix.
            - "context": Where this appears (e.g., "Footer", "About Section", or specific text snippet).
            
            Example:
            [
                {{"category": "Spelling", "issue": "Luxery", "fix": "Luxury", "context": "Hero Headline"}},
                {{"category": "Logic", "issue": "Link 'View Homes' goes to Contact page", "fix": "Change link to /properties", "context": "Navigation Bar"}}
            ]
            """
            
            # C. GET AI RESPONSE
            result = model.generate_content(prompt)
            
            # Clean up response to ensure pure JSON
            raw_text = result.text.replace("```json", "").replace("```", "").strip()
            
            try:
                audit_data = json.loads(raw_text)
                
                # --- 5. DISPLAY RESULTS (THE "CARD" UI) ---
                st.success(f"Audit Complete. Found {len(audit_data)} issues.")
                st.markdown("---")

                # Iterate through errors and create "Cards"
                for item in audit_data:
                    # Determine icon based on category
                    icon = "🔗" if item['category'] == "Logic" else "📝"
                    
                    st.markdown(f"""
                    <div class="audit-card">
                        <div class="audit-meta">{icon} {item['category']}  •  LOCATION: {item['context']}</div>
                        <h4>{item['issue']}</h4>
                        <div style="color: #ccc; margin-top:5px;">Suggested Fix:</div>
                        <div class="audit-fix">{item['fix']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Download Option
                df = pd.DataFrame(audit_data)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="DOWNLOAD FULL REPORT (CSV)",
                    data=csv,
                    file_name="lp_audit_report.csv",
                    mime="text/csv",
                )

            except json.JSONDecodeError:
                st.error("AI returned a format that couldn't be parsed. Please try again.")
                st.write(raw_text) # Debug view

        except Exception as e:
            st.error(f"Error crawling site: {e}")
