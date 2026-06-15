import re
import time
import pandas as pd
from datetime import datetime
from duckduckgo_search import DDGS

# 1. Configuration
LOCATIONS = ['Chittorgarh', 'Bhilwara', 'Udaipur', 'Mumbai', 'Navi Mumbai']

# We group keywords so the search engine understands we want ANY of these roles
ROLE_KEYWORDS = '"Credit Manager" OR "Credit Risk" OR "SME" OR "Underwriting" OR "Corporate"'

extracted_posts = []

print("Initializing Search Engine Backdoor...")

# 2. Run the Search Engine Queries
with DDGS() as ddgs:
    for loc in LOCATIONS:
        # 'site:linkedin.com/posts' forces the engine to ONLY look at individual user feeds
        # '"hiring"' ensures we are looking at job announcements
        query = f'site:linkedin.com/posts "hiring" ({ROLE_KEYWORDS}) "{loc}"'
        print(f"Scanning feed posts for: {loc}...")
        
        try:
            # Fetch the top 15 most relevant posts per location
            results = ddgs.text(query, max_results=15)
            
            if results:
                for r in results:
                    title = r.get('title', '')
                    snippet = r.get('body', '') # This is the actual text of the LinkedIn post!
                    link = r.get('href', '')
                    
                    # Search for emails hidden inside the post text
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                    mail_id = ", ".join(set(emails)) if emails else "Apply via Link"
                    
                    # Clean up the poster's name (Search engines usually format titles as "Name on LinkedIn: Post...")
                    poster = title.split(" on LinkedIn")[0] if " on LinkedIn" in title else "Recruiter/Individual"
                    
                    job_record = {
                        "Job Profile": "Feed Post: " + snippet[:45] + "...",
                        "Posted by": poster[:30],
                        "Location": loc,
                        "Mail id": mail_id,
                        "Posted Date": "Recent", # Search engines surface relevant, but not exact timestamped results
                        "Apply Link": link
                    }
                    
                    if job_record not in extracted_posts:
                        extracted_posts.append(job_record)
            
            # Pause for 3 seconds between city searches so the search engine doesn't block us
            time.sleep(3) 
            
        except Exception as e:
            print(f"Error scanning {loc}: {e}")

# 3. Build the Single-Page View Dashboard
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
        <div class="meta">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Tracking Hidden Feed Posts</div>
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
    
    output_path = "job_dashboard.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nSuccess! Captured {len(extracted_posts)} individual feed posts.")
else:
    print("\nNo matching feed posts found today.")
