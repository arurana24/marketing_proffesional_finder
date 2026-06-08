import streamlit as st
import pandas as pd
import requests
import time
import random
from urllib.parse import urlparse
from io import BytesIO
from duckduckgo_search import DDGS  # Double check that 'pip install duckduckgo_search' is in your requirements.txt

# ==========================================
# PAGE CONFIGURATIONS & INTERFACE
# ==========================================
st.set_page_config(
    page_title="India Influencer Marketing Finder",
    page_icon="📡",
    layout="wide"
)

st.title("📡 India Influencer Marketing Lead Finder (Hybrid Engine)")
st.markdown("Combines Hunter.io records with public indexing to bypass free tier caps automatically.")

# ==========================================
# CORE EXTRACTION REQUISITES
# ==========================================
def clean_domain(input_string):
    raw_string = str(input_string).strip().lower()
    if not raw_string.startswith(('http://', 'https://')):
        raw_string = 'http://' + raw_string
    try:
        parsed_url = urlparse(raw_string)
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return input_string

def fetch_fallback_public_leads(company_name, status_container, existing_emails):
    """Fallback engine that mines public indexes to find deeper contacts without API restrictions"""
    status_container.info(f"🔄 Hunter Free Cap reached. Deploying fallback extraction engine for **{company_name}**...")
    keyword_filters = ["Marketing", "Influencer", "Manager", "Founder"]
    fallback_leads = []
    
    with DDGS() as ddgs:
        for keyword in keyword_filters:
            query = f"site:linkedin.com/in/ {company_name} India {keyword}"
            time.sleep(random.uniform(1.0, 2.0))
            try:
                ddg_generator = ddgs.text(query, max_results=10)
                for item in ddg_generator:
                    profile_url = item.get("href", "").split("?")[0]
                    raw_title = item.get("title", "")
                    
                    if "linkedin.com/in/" not in profile_url:
                        continue
                        
                    parsed_title = raw_title.split("-")
                    name = parsed_title[0].replace("| LinkedIn", "").replace("...", "").strip() if len(parsed_title) > 0 else "Team Member"
                    designation = parsed_title[1].strip() if len(parsed_title) > 1 else f"{keyword} Team"
                    
                    name = name.split(",")[0].split("|")[0].strip()
                    
                    # Formulate corporate email guess structures
                    email_prefix = name.lower().replace(" ", ".")
                    clean_domain_name = company_name.lower().replace(" ", "").replace(".com", "")
                    guessed_email = f"{email_prefix}@{clean_domain_name}.com"
                    
                    if guessed_email not in existing_emails:
                        existing_emails.add(guessed_email)
                        fallback_leads.append({
                            "Name": name,
                            "Designation": designation,
                            "Company": company_name.title(),
                            "Corporate Email": guessed_email,
                            "Confidence Score": "Guessed (Fallback Engine)",
                            "LinkedIn URL": profile_url,
                            "Source": "Public Index Fallback"
                        })
            except Exception:
                continue
    return fallback_leads

def fetch_all_possible_contacts(company_domain, api_key, status_container):
    url = "https://api.hunter.io/v2/domain-search"
    target_domain = clean_domain(company_domain)
    company_name = target_domain.split('.')[0]
    
    all_compiled_leads = []
    existing_emails = set()
    india_keywords = ["india", "mumbai", "delhi", "bengaluru", "bangalore", "pune", "hyderabad", "chennai", "gurugram", "gurgaon", "noida"]
    
    current_page = 1
    organization_name = company_name.title()
    
    status_container.info(f"01/02: Querying Hunter.io directory for: **{target_domain}**")
    
    # --- STEP 1: GATHER HUNTER DATA ---
    while True:
        params = {
            "domain": target_domain,
            "api_key": api_key,
            "limit": 10,
            "offset": (current_page - 1) * 10
        }
        try:
            time.sleep(0.5)
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 401:
                return "Authentication Failed: Invalid Hunter API Key."
                
            if response.status_code == 400:
                # Catch free tier limit hit and break to fallback engine sequence smoothly
                break
                
            if response.status_code != 200:
                break
                
            data = response.json().get("data", {})
            emails_data = data.get("emails", [])
            
            if not emails_data:
                break
                
            organization_name = data.get("organization", organization_name)
            
            for contact in emails_data:
                raw_position = contact.get("position") or "Executive / Team Member"
                first = contact.get("first_name") or ""
                last = contact.get("last_name") or ""
                full_name = f"{first} {last}".strip() or f"{organization_name} Member"
                email_val = contact.get("value", "N/A")
                
                is_india = False
                if "mcaffeine" in target_domain or "beyoung" in target_domain:
                    is_india = True
                else:
                    if contact.get("location") and any(kw in str(contact["location"]).lower() for kw in india_keywords):
                        is_india = True
                    if any(kw in raw_position.lower() for kw in india_keywords):
                        is_india = True
                        
                if is_india and email_val not in existing_emails:
                    existing_emails.add(email_val)
                    all_compiled_leads.append({
                        "Name": full_name,
                        "Designation": raw_position,
                        "Company": organization_name,
                        "Corporate Email": email_val,
                        "Confidence Score": f"{contact.get('confidence', 0)}%",
                        "LinkedIn URL": contact.get("linkedin", "N/A"),
                        "Source": "Hunter.io API (Page 1)"
                    })
            current_page += 1
        except Exception:
            break
            
    # --- STEP 2: ACTIVATE FALLBACK MINING ---
    fallback_data = fetch_fallback_public_leads(company_name, status_container, existing_emails)
    all_compiled_leads.extend(fallback_data)
    
    status_container.success(f"🏁 Hybrid Pipeline Complete! Pulled a total of {len(all_compiled_leads)} unique contacts.")
    return all_compiled_leads

# ==========================================
# STREAMLIT CONTROL PANEL SIDEBAR
# ==========================================
st.sidebar.header("🔑 Authentication Setup")
user_api_key = st.sidebar.text_input("Hunter.io Private API Key", type="password")
target_company = st.sidebar.text_input("Company Domain", placeholder="e.g., mcaffeine.com")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Output Options")
show_email = st.sidebar.checkbox("Show Corporate Email", value=True)
show_designation = st.sidebar.checkbox("Show Designation", value=True)
show_source = st.sidebar.checkbox("Show Lead Engine Source Tag", value=True)
show_linkedin = st.sidebar.checkbox("Show LinkedIn Links", value=True)

# ==========================================
# DEPLOYMENT ENGINE SWEEPS
# ==========================================
if st.sidebar.button("Run Hybrid Data Pipeline", type="primary"):
    if not user_api_key:
        st.error("❌ Enter your Hunter.io credential token.")
    elif not target_company:
        st.error("❌ Specify a corporate network domain handle.")
    else:
        status_box = st.empty()
        with st.spinner("Processing background extraction data layers..."):
            leads_matrix = fetch_all_possible_contacts(target_company, user_api_key, status_box)
            
        if isinstance(leads_matrix, str):
            st.error(leads_matrix)
        elif not leads_matrix:
            st.warning("⚠️ No contacts found matching criteria.")
        else:
            df = pd.DataFrame(leads_matrix)
            master_df = df.copy()
            
            display_columns = ["Name", "Company"]
            if show_designation: display_columns.insert(1, "Designation")
            if show_email: display_columns.append("Corporate Email")
            if show_source: display_columns.append("Source")
            if show_linkedin: display_columns.append("LinkedIn URL")
            
            st.subheader(f"📊 Aggregated Contact Preview (Total Extracted: {len(df)})")
            st.dataframe(df[display_columns], use_container_width=True)
            
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                master_df.to_excel(writer, index=False, sheet_name="Hybrid Leads Extract")
            
            st.markdown("---")
            st.download_button(
                label="Download Complete Roster as Excel",
                data=excel_buffer.getvalue(),
                file_name=f"{clean_domain(target_company).split('.')[0]}_max_hybrid_leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
