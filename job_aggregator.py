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

# 2. Load Config
try:
    with open("linkedin_scraper_config.json", "r") as config_file:
        config = json.load(config_file)
        print("Successfully loaded linkedin_scraper_config.json!")
except Exception as e:
    print(f"Failed to load config JSON: {e}")
    sys.exit(1)

LOCATIONS          = config.get("target_locations", [])
PROFILES           = config.get("target_profiles", [])
MANDATORY_KEYWORDS = [kw.lower() for kw in config.get("mandatory_keywords", [])]
DASHBOARD_TITLE    = config.get("dashboard_title", "Daily Credit Job Feed")

print(f"Loaded {len(LOCATIONS)} locations, {len(PROFILES)} profiles, {len(MANDATORY_KEYWORDS)} mandatory keywords.")

# ── Extract LinkedIn numeric Job ID to fix duplicate detection ──
def extract_job_id(url):
    match = re.search(r'-(\d+)\?', url)
    return match.group(1) if match else url

# ── Check if snippet contains at least one mandatory keyword ──
def passes_keyword_filter(text):
    text_lower = text.lower()
    for kw in MANDATORY_KEYWORDS:
        if kw in text_lower:
            return True, kw
    return False, None

extracted_posts = []
seen_job_ids    = set()

print("Initializing Google Search API...")
api_url = "https://customsearch.googleapis.com/customsearch/v1"

# 3. Run the Scraper
for loc in LOCATIONS:
    for prof in PROFILES:
        query = f'intitle:"{prof}" "{loc}" site:in.linkedin.com/jobs/view'
        print(f"\nAsking Google: {query}")

        params = {
            "key": API_KEY,
            "cx": CX_ID,
            "q": query,
            "dateRestrict": "d3"
        }

        try:
            response = requests.get(api_url, params=params)
            data = response.json()

            if "error" in data:
                print(f"  API ERROR: {data['error']['message']}")
                continue

            total_results = data.get("searchInformation", {}).get("totalResults", "0")
            print(f"  --> Google found {total_results} results.")

            if "items" in data:
                for item in data["items"]:
                    snippet = item.get("snippet", "")
                    link    = item.get("link", "")
                    title   = item.get("title", "")

                    # FILTER 1: Profile keyword must appear in job title
                    if prof.lower() not in title.lower():
                        print(f"  SKIP (title mismatch): {title[:70]}")
                        continue

                    # FILTER 2: Deduplicate by LinkedIn Job ID
                    job_id = extract_job_id(link)
                    if job_id in seen_job_ids:
                        print(f"  SKIP (duplicate ID {job_id}): {title[:70]}")
                        continue

                    # FILTER 3: At least one mandatory keyword in snippet or title
                    combined_text = title + " " + snippet
                    passed, matched_kw = passes_keyword_filter(combined_text)
                    if not passed:
                        print(f"  SKIP (no keyword match): {title[:70]}")
                        continue

                    # All filters passed — add the job
                    seen_job_ids.add(job_id)

                    emails   = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                    mail_id  = ", ".join(set(emails)) if emails else "Apply via Link"

                    poster      = title.split(" hiring ")[0] if " hiring " in title else title.split(" | ")[0]
                    clean_title = title.split(" hiring ")[1].split(" in ")[0] if " hiring " in title else title

                    job_record = {
                        "Job Profile":  clean_title[:70],
                        "Posted by":    poster[:35],
                        "Location":     loc,
                        "Mail id":      mail_id,
                        "Posted Date":  datetime.now().strftime('%Y-%m-%d'),
                        "Apply Link":   link,
                        "Matched KW":  matched_kw
                    }

                    extracted_posts.append(job_record)
                    print(f"  ADDED (keyword: '{matched_kw}'): {clean_title[:60]}")

            time.sleep(1.5)

        except Exception as e:
            print(f"  Error connecting to Google: {e}")

# 4. Build the HTML Dashboard
print(f"\n{'='*50}")
print(f"Total unique jobs found: {len(extracted_posts)}")
print(f"{'='*50}")

if extracted_posts:
    df = pd.DataFrame(extracted_posts)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{DASHBOARD_TITLE}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #f4f6f9; }}
        h2 {{ color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
        .meta {{ color: #64748b; margin-bottom: 20px; font-size: 14px; }}
        .stats {{ background: #dbeafe; border-left: 4px solid #2563eb; padding: 10px 16px; margin-bottom: 20px; border-radius: 4px; font-size: 14px; color: #1e3a8a; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        th {{ background-color: #1e293b; color: white; text-align: left; padding: 12px 16px; font-weight: 600; }}
        td {{ padding: 14px 16px; border-bottom: 1px solid #e2e8f0; color: #334155; font-size: 14px; }}
        tr:hover {{ background-color: #f8fafc; }}
        .apply-btn {{ display: inline-block; padding: 8px 14px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: bold; }}
        .apply-btn:hover {{ background-color: #1d4ed8; }}
        .email-text {{ font-family: monospace; color: #059669; font-weight: bold; }}
        .kw-badge {{ background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
    </style>
</head>
<body>
    <h2>{DASHBOARD_TITLE}</h2>
    <div class="meta">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    <div class="stats">
        ✅ <b>{len(extracted_posts)} unique credit roles</b> found across {len(LOCATIONS)} locations &nbsp;|&nbsp;
        Filters applied: Title Match + Job ID Dedup + Keyword Match
    </div>
    <table>
        <tr>
            <th>Company / Posted By</th>
            <th>Job Title</th>
            <th>Location</th>
            <th>Mail ID / Action</th>
            <th>Date</th>
            <th>Matched Keyword</th>
            <th>Apply</th>
        </tr>
"""

    for _, row in df.iterrows():
        mail_display = (
            f'<span class="email-text">{row["Mail id"]}</span>'
            if "@" in row["Mail id"]
            else f'<span>{row["Mail id"]}</span>'
        )
        html_content += f"""
        <tr>
            <td><b>{row['Posted by']}</b></td>
            <td>{row['Job Profile']}</td>
            <td>{row['Location']}</td>
            <td>{mail_display}</td>
            <td>{row['Posted Date']}</td>
            <td><span class="kw-badge">{row['Matched KW']}</span></td>
            <td><a class="apply-btn" href="{row['Apply Link']}" target="_blank">Click to Apply</a></td>
        </tr>"""

    html_content += """
    </table>
</body>
</html>"""

    with open("job_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard saved: job_dashboard.html")

else:
    # Write a blank dashboard so GitHub Pages doesn't show old stale data
    with open("job_dashboard.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html><body>
        <h2>No matching credit jobs found today.</h2>
        <p>Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}. Try again tomorrow.</p>
        </body></html>""")
    print("No jobs found. Blank dashboard written.")
