import os
import time
import requests
import pandas as pd
from datetime import datetime
import re

# 1. Securely grab your keys
API_KEY = os.environ.get("GCP_API_KEY")
CX_ID = os.environ.get("GCP_CX_ID")

LOCATIONS = ['Chittorgarh', 'Bhilwara', 'Udaipur', 'Mumbai', 'Navi Mumbai']
KEYWORDS = ['Credit Manager', 'Credit Risk', 'SME', 'Underwriting', 'Corporate']

extracted_posts = []

print("Initializing Enterprise Google Search API...")

# 2. Run the queries with loosened, natural search terms
url = "https://customsearch.googleapis.com/customsearch/v1"

for loc in LOCATIONS:
    for kw in KEYWORDS:
        # We removed the strict quotation marks so Google can find natural variations
        query = f'site:linkedin.com/posts hiring {kw} {loc}'
        print(f"Asking Google: {query}")
        
        params = {
            "key": API_KEY,
            "cx": CX_ID,
            "q": query
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            # X-RAY VISION: Print exactly how many results Google's API claims to see
            total_results = data.get("searchInformation", {}).get("totalResults", "0")
            print(f"--> Google found {total_results} results.")
            
            # If Google found results, extract the text
            if "items" in data:
                for item in data["items"]:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "") 
                    link = item.get("link", "")
                    
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                    mail_id = ", ".join(set(emails)) if emails else "Apply via Link"
                    
                    poster = title.split(" on LinkedIn")[0] if " on LinkedIn" in title else "Recruiter/Individual"
                    
                    job_record = {
                        "Job Profile": "Feed Post: " + snippet[:45] + "...",
                        "Posted by": poster[:30],
                        "Location": loc,
                        "Mail id": mail_id,
                        "Posted Date": "Recent", 
                        "Apply Link": link
                    }
                    
                    if not any(post['Apply Link'] == job_record['Apply Link'] for post in extracted_posts):
                        extracted_posts.append(job_record)
            
            time.sleep(1) 
            
        except Exception as e:
            print(f"Error connecting to Google: {e}")

# 3. Build the Dashboard
if extracted_posts:
    df = pd.DataFrame(extracted_posts)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Daily Credit Job Feed (Individual Posts)</title>
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
        <h2>Individual Recruiter Posts: Credit & SME Teams</h2>
        <div class="meta">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Powered by Google API</div>
        <table>
            <tr>
                <th>Posted By</th>
                <th>Post Preview</th>
                <th>Location</th>
                <th>Mail ID / Action</th>
                <th>Posted Date</th>
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
                <td><a class="apply-btn" href="{row['Apply Link']}" target="_blank">View Post</a></td>
            </tr>
        """
        
    html_content += """
        </table>
    </body>
    </html>
    """
    
    with open("job_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nSuccess! Captured {len(extracted_posts)} feed posts using Google.")
else:
    print("\nNo matching feed posts found today.")
