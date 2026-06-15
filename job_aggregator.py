import logging
import os
import re
import pandas as pd
from datetime import datetime
from linkedin_jobs_scraper import LinkedinScraper
from linkedin_jobs_scraper.events import Events, EventData
from linkedin_jobs_scraper.query import Query, QueryOptions, QueryFilters
from linkedin_jobs_scraper.filters import TimeFilters

# 1. Configuration & Requirements
LOCATIONS = ['Chittorgarh', 'Bhilwara', 'Udaipur', 'Mumbai', 'Navi Mumbai']
KEYWORDS = ['Credit Manager', 'Credit Risk']

# Sub-filters to match within descriptions
MUST_HAVE_KEYWORDS = ['sme', 'large ticket', 'turnover', 'medium corporate', 'large corporate', 'underwriting', 'caam']

extracted_jobs = []

# 2. Callback function when a job is successfully scraped
def on_data(data: EventData):
    desc_lower = data.description.lower()
    
    # Check if the job description contains our target banking keywords
    has_keyword = any(kw in desc_lower for kw in MUST_HAVE_KEYWORDS)
    
    if has_keyword:
        # Regex to scan for email IDs inside the post description
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', data.description)
        mail_id = ", ".join(set(emails)) if emails else "Apply via Link"
        
        # Format the data according to your required layout
        job_record = {
            "Job Profile": data.title,
            "Posted by": data.company,
            "Location": data.place,
            "Mail id": mail_id,
            "Posted Date": data.date if data.date else "Recently",
            "Apply Link": data.apply_link if data.apply_link else data.link
        }
        extracted_jobs.append(job_record)
        print(f"Captured: {data.title} at {data.company} ({data.place})")

def on_error(error):
    pass # Silently handle minor scraping structural errors

# 3. Setup Scraper Engine
scraper = LinkedinScraper(
    chrome_executable_path=None, # Automatically finds Chrome
    chrome_options=None,
    headless=True,               # Runs quietly in the background
    max_workers=2,
    slow_mo=1.5                  # Prevents hitting rate limits
)

# Bind events
scraper.on(Events.DATA, on_data)
scraper.on(Events.ERROR, on_error)

# 4. Construct Queries dynamically
queries = []
for kw in KEYWORDS:
    for loc in LOCATIONS:
        queries.append(
            Query(
                query=kw,
                options=QueryOptions(
                    locations=[f"{loc}, India"],
                    limit=15, # Limit per category to keep execution fast
                    filters=QueryFilters(
                        time=TimeFilters.DAY # Fetches fresh posts (last 24 hours)
                    )
                )
            )
        )

print("Starting one-click daily job aggregation...")
scraper.run(queries)

# 5. Build the Interactive HTML Single-Page View
if extracted_jobs:
    df = pd.DataFrame(extracted_jobs)
    
    # Generate an elegant, scannable HTML file
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Daily Credit Risk Job Feed</title>
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
        <h2>Daily Hiring Tracker: Credit Manager / Risk</h2>
        <div class="meta">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Locations: {', '.join(LOCATIONS)}</div>
        <table>
            <tr>
                <th>Posted By</th>
                <th>Job Profile</th>
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
                <td><a class="apply-btn" href="{row['Apply Link']}" target="_blank">Click to Apply</a></td>
            </tr>
        """
        
    html_content += """
        </table>
    </body>
    </html>
    """
    
    # Save the output file
    output_path = "job_dashboard.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nSuccess! Open '{os.path.abspath(output_path)}' in your browser to view and apply.")
else:
    print("\nNo matching jobs found in the last 24 hours with your specific keywords.")