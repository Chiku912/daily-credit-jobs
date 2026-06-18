import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime
import re
import json

# 1. Secure Keys
API_KEY = os.environ.get("GCP_API_KEY", "").strip()
CX_ID = os.environ.get("GCP_CX_ID", "").strip()

if not CX_ID or not API_KEY:
    print("CRITICAL ERROR: GitHub is NOT passing the secrets to Python!")
    sys.exit(1)

print(f"DIAGNOSTIC -> Using API Key ending in: ...{API_KEY[-4:]}")
print(f"DIAGNOSTIC -> Using CX ID ending in: ...{CX_ID[-4:]}")

# 2. Load the User's Custom JSON Configuration
try:
    with open("linkedin_scraper_config.json", "r") as config_file:
        config = json.load(config_file)
        print("Successfully loaded linkedin_scraper_config.json!")
except Exception as e:
    print(f"Failed to load config JSON: {e}")
    sys.exit(1)

LOCATIONS = config.get("target_locations", [])
PROFILES = config.get("target_profiles", [])
DASHBOARD_TITLE = config.get("dashboard_title", "Daily Credit Job Feed")

extracted_posts = []
print("Initializing Google Search API...")
url = "https://customsearch.googleapis.com/customsearch/v1"

# 3. Run the Scraper (STRICT MATCHING VERSION)
for loc in LOCATIONS:
    for prof in PROFILES:
        # Enforcing STRICT matching by targeting LinkedIn job view pages directly
        query = f'intitle:"{prof}" "{loc}" site:in.linkedin.com/jobs/view'
        print(f"Asking Google: {query}")
        
        params = {
            "key": API_KEY,
            "cx": CX_ID,
            "q": query,
            "dateRestrict": "d3" # Setting to 3 days to only get fresh, active jobs
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if "error" in data:
                print(f"API ERROR: {data['error']['message']}")
                continue
            
            total_results = data.get("searchInformation", {}).get("totalResults", "0")
            print(f"--> Google found {total_results} results.")
            
            if "items" in data:
                for item in data["items"]:
                    snippet = item.get("snippet", "") 
                    link = item.get("link", "")
                    title = item.get("title", "")
                    
                    # STRICT FILTER: Ensure your exact target profile is in the job title
                    if prof.lower() not in title.lower():
                        continue
                    
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                    mail_id = ", ".join(set(emails)) if emails else "Apply via Link"
                    
                    # Clean up the dashboard title
                    poster = title.split(" hiring ")[0] if " hiring " in title else title.split(" | ")[0]
                    clean_title = title.split(" hiring ")[1].split(" in ")[0] if " hiring " in title else title
                    
                    job_record = {
                        "Job Profile": clean_title[:70],
                        "Posted by": poster[:30],
                        "Location": loc,
                        "Mail id": mail_id,
                        "Posted Date": datetime.now().strftime('%Y-%m-%d'), 
                        "Apply Link": link
                    }
                    
                    if not any(post['Apply Link'] == job_record['Apply Link'] for post in extracted_posts):
                        extracted_posts.append(job_record)
            
            time.sleep(1.5) 
            
        except Exception as e:
            print(f"Error connecting to Google: {e}")

# 4. Build the HTML Dashboard
if extracted_posts:
    df = pd.DataFrame(extracted_posts)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{DASHBOARD_TITLE}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #f4f6f9; }}
            h2 {{ color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
            .meta {{ color: #64748b; margin-bottom: 20px; font-size: 14px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
            th {{ background-color: #1e293b; color: white; text-align: left; padding: 12px 16px; font-weight: 600; }}
            td {{ padding: 14px 16px; border-bottom: 1px solid #e2e8f0; color: #334155; font-size: 15px; }}
            tr:hover {{ background-color: #f8fafc; }}
            .apply-btn {{ display: inline-block; padding: 8px 14px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: bold; }}
            .apply-btn:hover {{ background-color: #1d4ed8; }}
            .email-text {{ font-family: monospace; color: #059669; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>{DASHBOARD_TITLE}</h2>
        <div class="meta">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Auto-pulled from Config</div>
        <table>
            <tr>
                <th>Company / Posted By</th>
                <th>Exact Job Title</th>
                <th>Location</th>
                <th>Mail ID / Action</th>
                <th>Scraped Date</th>
                <th>Action</th>
            </tr>
    """
    
    for _, row in df.iterrows():
        mail_display = f'<span class="email-text">{row["Mail id"]}</span>' if "@" in row["Mail id"] else f'<span>{row["Mail id"]}</span>'
        html_content += f"""
            <tr>
                <td><b>{row['Posted by']}</b></td>
                <td>{row['Job Profile']}</td>
                <td>{row['Location']}</td>
                <td>{mail_display}</td>
                <td>{row['Posted Date']}</td>
                <td><a class="apply-btn" href="{row['Apply Link']}" target="_blank">View on LinkedIn</a></td>
            </tr>
        """
        
    html_content += """
        </table>
    </body>
    </html>
    """
    
    with open("job_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nSuccess! Captured {len(extracted_posts)} strict credit jobs.")
else:
    print("\nNo matching credit jobs found in the last 3 days. Try checking again tomorrow!")
