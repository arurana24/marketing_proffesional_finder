import streamlit as st
import pandas as pd
import requests
import time
from urllib.parse import urlparse
from io import BytesIO

# ==========================================
# PAGE CONFIGURATIONS & INTERFACE
# ==========================================
st.set_page_config(
    page_title="India Influencer Marketing Finder",
    page_icon="📡",
    layout="wide"
)

st.title("📡 India Influencer Marketing Lead Finder")
st.markdown("Extract real-time corporate marketing contacts directly via Hunter.io pagination loops.")

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

def fetch_all_possible_contacts(company_domain, api_key, status_container):
    url = "https://api.hunter.io/v2/domain-search"
    target_domain = clean_domain(company_domain)
    
    all_compiled_leads = []
    india_keywords = ["india", "mumbai", "delhi", "bengaluru", "bangalore", "pune", "hyderabad", "chennai", "gurugram", "gurgaon", "noida"]
    
    current_page = 1
    organization_name = target_domain.split('.')[0].title()
    
    status_container.info(f"🛰️ Opening pagination data pipeline for: **{target_domain}**")
    
    while True:
        status_container.text(f"⏳ Extracting Page {current_page} records stream...")
        
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
            if response.status_code != 200:
                status_container.warning(f"⚠️ Terminated layout paging loop at page {current_page}. HTTP {response.status_code}")
                break
                
            data = response.json().get("data", {})
            emails_data = data.get("emails", [])
            
            if not emails_data:
                status_container.success(f"🏁 Finished crawling. Total data pages extracted: {current_page - 1}")
                break
                
            organization_name = data.get("organization", organization_name)
            
            for contact in emails_data:
                raw_position = contact.get("position") or "Executive / Team Member"
                first = contact.get("first_name") or ""
                last = contact.get("last_name") or ""
                full_name = f"{first} {last}".strip()
                if not full_name:
                    full_name = f"{organization_name} Member"
                    
                is_india = False
                if "mcaffeine" in target_domain or "beyoung" in target_domain:
                    is_india = True
                else:
                    if contact.get("location"):
                        if any(kw in str(contact["location"]).lower() for kw in india_keywords):
                            is_india = True
                    if any(kw in raw_position.lower() for kw in india_keywords):
                        is_india = True
                        
                if is_india:
                    all_compiled_leads.append({
                        "Name": full_name,
                        "Designation": raw_position,
                        "Company": organization_name,
                        "Corporate Email": contact.get("value", "N/A"),
                        "Confidence Score": f"{contact.get('confidence', 0)}%",
                        "LinkedIn URL": contact.get("linkedin", "N/A"),
                        "Source Page": current_page
                    })
            
            current_page += 1
            
        except Exception as e:
            status_container.error(f"❌ Core runtime exception encountered on page {current_page}: {str(e)}")
            break
            
    return all_compiled_leads

# ==========================================
# STREAMLIT CONTROL PANEL SIDEBAR
# ==========================================
st.sidebar.header("🔑 Authentication Setup")
user_api_key = st.sidebar.text_input("Hunter.io Private API Key", type="password", help="Input your workspace token.")
target_company = st.sidebar.text_input("Company Domain", placeholder="e.g., mcaffeine.com")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Output Visual Options")

show_email = st.sidebar.checkbox("Show Corporate Email", value=True)
show_designation = st.sidebar.checkbox("Show Designation", value=True)
show_confidence = st.sidebar.checkbox("Show Confidence Score", value=False)
show_linkedin = st.sidebar.checkbox("Show LinkedIn Profile Link", value=True)
show_page = st.sidebar.checkbox("Show Extracted Page Source Index", value=False)

# ==========================================
# DEPLOYMENT ENGINE SWEEPS
# ==========================================
if st.sidebar.button("Run Data Pipeline", type="primary"):
    if not user_api_key:
        st.error("❌ Enter your active Hunter.io credential token to authorize searches.")
    elif not target_company:
        st.error("❌ Specify a corporate network domain handle to harvest.")
    else:
        status_box = st.empty()
        
        with st.spinner("Extracting multi-page directory assets..."):
            leads_matrix = fetch_all_possible_contacts(target_company, user_api_key, status_box)
            
        if isinstance(leads_matrix, str):
            st.error(leads_matrix)
        elif not leads_matrix:
            st.warning("⚠️ No matching profiles explicitly corresponding to domestic regional tags were found.")
        else:
            df = pd.DataFrame(leads_matrix)
            master_df = df.copy()
            
            # Map checkboxes dynamically to active rendering arrays
            display_columns = ["Name", "Company"]
            if show_designation: display_columns.insert(1, "Designation")
            if show_email: display_columns.append("Corporate Email")
            if show_confidence: display_columns.append("Confidence Score")
            if show_linkedin: display_columns.append("LinkedIn URL")
            if show_page: display_columns.append("Source Page")
            
            filtered_df = df[display_columns]
            
            st.subheader(f"📊 Live Data Review (Matches: {len(df)})")
            st.dataframe(filtered_df, use_container_width=True)
            
            # Pack memory streams cleanly to handle seamless inline excel generation downloads
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                master_df.to_excel(writer, index=False, sheet_name="India Lead Extract")
            excel_binaries = excel_buffer.getvalue()
            
            st.markdown("---")
            st.subheader("📥 Export Final Clean Asset")
            
            st.download_button(
                label="Download Complete Roster as Excel",
                data=excel_binaries,
                file_name=f"{clean_domain(target_company).split('.')[0]}_leads_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
