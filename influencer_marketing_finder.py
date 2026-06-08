import os
import time
import requests
import pandas as pd
from urllib.parse import urlparse

# ==========================================
# CONFIGURATION MATRIX
# ==========================================
# 🔑 Paste your free Hunter.io API Key here
HUNTER_API_KEY = "4cb3c54d95b5ddac4514e02e69210bb323b680f8"
OUTPUT_EXCEL = "india_max_extracted_leads.xlsx"

def clean_domain(input_string):
    """Strips away protocols, www, sub-directories, and spacing to avoid errors"""
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

def fetch_all_possible_contacts(company_domain, api_key):
    """Loops through Hunter pagination to drain all available contacts"""
    url = "https://api.hunter.io/v2/domain-search"
    target_domain = clean_domain(company_domain)
    
    all_compiled_leads = []
    india_keywords = ["india", "mumbai", "delhi", "bengaluru", "bangalore", "pune", "hyderabad", "chennai", "gurugram", "gurgaon", "noida"]
    
    current_page = 1
    organization_name = target_domain.split('.')[0].title()
    
    print(f"\n📡 Initiating multi-page data drain for: '{target_domain}'")
    
    while True:
        print(f"⏳ Fetching Page {current_page} from Hunter...")
        
        # We pass the current_page variable to step through Hunter's database pages
        params = {
            "domain": target_domain,
            "api_key": api_key,
            "limit": 10, # Keeping it at the safe free-tier limit per request
            "offset": (current_page - 1) * 10 # Tells Hunter where the next page starts
        }
        
        try:
            # Respectful rate limiting pause (Hunter allows 15 requests per second, so 0.5s is perfectly safe)
            time.sleep(0.5)
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 401:
                return "Authentication Failed: Invalid Hunter API Key."
            if response.status_code != 200:
                print(f"⚠️ Stopped paging at page {current_page}. Server response: HTTP {response.status_code}")
                break
                
            data = response.json().get("data", {})
            emails_data = data.get("emails", [])
            
            # 🛑 CRITICAL BREAK CONDITION: If a page comes back empty, we've hit the end of the line!
            if not emails_data:
                print(f"🏁 Reached the end of available data records (Total pages parsed: {current_page - 1}).")
                break
                
            organization_name = data.get("organization", organization_name)
            
            # Process the batch of contacts from this specific page
            for contact in emails_data:
                raw_position = contact.get("position") or "Executive / Team Member"
                first = contact.get("first_name") or ""
                last = contact.get("last_name") or ""
                full_name = f"{first} {last}".strip()
                if not full_name:
                    full_name = f"{organization_name} Associate"
                    
                # Geographic location evaluation logic
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
            
            # Increment to crawl the next batch of 10 on the next loop cycle
            current_page += 1
            
        except Exception as e:
            print(f"❌ Exception error occurred on page {current_page}: {str(e)}")
            break
            
    return all_compiled_leads

def main():
    print("\n🚀 Starting Hunter.io Max-Yield Contact Harvester...")
    
    if HUNTER_API_KEY == "YOUR_HUNTER_API_KEY_HERE" or not HUNTER_API_KEY:
        print("❌ Error: You must replace 'YOUR_HUNTER_API_KEY_HERE' on line 10.")
        return
        
    target_company = input("\n🏢 Enter target domain (e.g., loreal.com, mcaffeine.com, unilever.com): ").strip()
    if not target_company:
        print("❌ Error: Target domain cannot be blank.")
        return
        
    leads = fetch_all_possible_contacts(target_company, HUNTER_API_KEY)
    
    if isinstance(leads, str):
        print(f"\n❌ Execution Stopped: {leads}")
        return
        
    if not leads:
        print("⚠️ No matching profiles extracted for this brand domain.")
        return
        
    df = pd.DataFrame(leads)
    
    try:
        df.to_excel(OUTPUT_EXCEL, index=False)
        print(f"\n🎉 Maximum Extraction Run Complete!")
        print(f"✅ Successfully extracted a total of {len(df)} contacts across all available data pages.")
        print(f"👉 Master Excel data file saved inside directory as: '{OUTPUT_EXCEL}'\n")
        
        print(df[["Name", "Designation", "Corporate Email", "Source Page"]].head(15).to_string())
        print("\n")
        
    except Exception as e:
        print(f"❌ Error compiling output spreadsheet: {str(e)}")

if __name__ == "__main__":
    main()