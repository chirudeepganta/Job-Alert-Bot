import requests
import feedparser
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

KEYWORDS = [
    "python developer", "python engineer",
    "backend engineer", "backend developer",
    "data engineer", "platform engineer",
    "ai engineer", "ml engineer",
    "machine learning engineer",
    "software engineer", "software developer",
    "associate engineer", "junior engineer",
    "entry level engineer", "new grad"
]

EXCLUDE_KEYWORDS = [
    "senior", "staff", "principal", "manager",
    "director", "lead", "head of", "vp", "vice president",
    "5+ years", "6+ years", "7+ years", "8+ years",
    "10+ years", "ruby only", ".net only",
    "salesforce apex", "embedded firmware"
]

EXPERIENCE_KEYWORDS = [
    "0-1", "0-2", "0-3", "1-2", "1-3", "2-3",
    "entry level", "junior", "associate", "new grad",
    "recent graduate", "early career", "less than 3"
]

VISA_KEYWORDS = [
    "visa sponsorship", "sponsor", "h1b", "h-1b",
    "work authorization", "sponsorship available",
    "will sponsor", "visa support"
]

NO_VISA_KEYWORDS = [
    "no sponsorship", "no visa", "must be authorized",
    "us citizen only", "security clearance required",
    "active clearance"
]

JOB_SOURCES = [
    "https://boards.greenhouse.io/mistralai/jobs.json",
    "https://boards.greenhouse.io/labelbox/jobs.json",
    "https://boards.greenhouse.io/remitly/jobs.json",
    "https://boards.greenhouse.io/sofi/jobs.json",
    "https://boards.greenhouse.io/cerebras/jobs.json",
    "https://boards.greenhouse.io/replit/jobs.json",
    "https://boards.greenhouse.io/harmonic/jobs.json",
    "https://boards.greenhouse.io/scale/jobs.json",
    "https://boards.greenhouse.io/anthropic/jobs.json",
    "https://boards.greenhouse.io/notion/jobs.json",
    "https://boards.greenhouse.io/figma/jobs.json",
    "https://boards.greenhouse.io/airtable/jobs.json",
    "https://boards.greenhouse.io/stripe/jobs.json",
    "https://boards.greenhouse.io/plaid/jobs.json",
    "https://boards.greenhouse.io/brex/jobs.json",
    "https://boards.greenhouse.io/gusto/jobs.json",
    "https://boards.greenhouse.io/mongodb/jobs.json",
    "https://boards.greenhouse.io/hubspot/jobs.json",
    "https://boards.greenhouse.io/datadog/jobs.json",
    "https://boards.greenhouse.io/snyk/jobs.json",
]

LEVER_SOURCES = [
    "https://api.lever.co/v0/postings/openai?mode=json",
    "https://api.lever.co/v0/postings/anduril?mode=json",
    "https://api.lever.co/v0/postings/benchling?mode=json",
    "https://api.lever.co/v0/postings/verkada?mode=json",
    "https://api.lever.co/v0/postings/rippling?mode=json",
]

RSS_FEEDS = [
    "https://remoteok.com/remote-python-jobs.rss",
    "https://remotive.com/api/remote-jobs/rss?category=software-dev",
]

seen_jobs = set()

def check_visa_status(text):
    text_lower = text.lower()
    for word in NO_VISA_KEYWORDS:
        if word in text_lower:
            return "❌ No Sponsorship"
    for word in VISA_KEYWORDS:
        if word in text_lower:
            return "✅ Visa Sponsorship Available"
    return "❓ Not Mentioned"

def check_experience(text):
    text_lower = text.lower()
    for word in EXCLUDE_KEYWORDS[6:]:
        if word in text_lower:
            return False
    return True

def fetch_greenhouse_jobs(url):
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        jobs = []
        company = url.split("/")[4]
        for job in data.get("jobs", []):
            title = job.get("title", "")
            location = job.get("location", {}).get("name", "")
            job_url = job.get("absolute_url", "")
            
            # Get full job description for visa check
            description = ""
            try:
                detail = requests.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job.get('id')}",
                    timeout=5
                )
                description = detail.json().get("content", "")
            except:
                pass

            jobs.append({
                "title": title,
                "location": location,
                "url": job_url,
                "company": company,
                "id": str(job.get("id", "")),
                "description": description
            })
        return jobs
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def fetch_lever_jobs(url):
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        jobs = []
        company = url.split("/")[5]
        for job in data:
            categories = job.get("categories", {})
            location = categories.get("location", "")
            description = job.get("descriptionPlain", "") + job.get("additionalPlain", "")
            jobs.append({
                "title": job.get("text", ""),
                "location": location,
                "url": job.get("hostedUrl", ""),
                "company": company,
                "id": job.get("id", ""),
                "description": description
            })
        return jobs
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def is_good_match(job):
    title_lower = job["title"].lower()
    location_lower = job.get("location", "").lower()

    # Exclude senior/management roles
    for word in EXCLUDE_KEYWORDS[:6]:
        if word in title_lower:
            return False

    # Must match at least one job keyword
    keyword_match = any(kw in title_lower for kw in KEYWORDS)
    if not keyword_match:
        return False

    # USA location filter
    non_usa = [
        "uk", "united kingdom", "london", "europe", "germany",
        "france", "canada", "australia", "india", "singapore",
        "netherlands", "spain", "italy", "brazil", "mexico",
        "japan", "china", "korea", "berlin", "amsterdam",
        "toronto", "sydney", "dublin", "paris", "remote - eu",
        "remote - europe", "remote - uk", "remote - canada"
    ]
    
    # If location is specified and clearly non-USA, skip it
    if location_lower and any(loc in location_lower for loc in non_usa):
        return False

    # Check experience level in description
    desc_lower = job.get("description", "").lower()
    has_high_exp = any(f"{i}+ years" in desc_lower for i in range(4, 15))
    if has_high_exp:
        has_entry = any(kw in desc_lower for kw in EXPERIENCE_KEYWORDS)
        if not has_entry:
            return False

    return True

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Telegram error: {response.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

def check_jobs():
    print(f"Checking jobs at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    new_jobs = []

    # Greenhouse
    for source in JOB_SOURCES:
        jobs = fetch_greenhouse_jobs(source)
        for job in jobs:
            if job["id"] not in seen_jobs and is_good_match(job):
                seen_jobs.add(job["id"])
                new_jobs.append(job)

    # Lever
    for source in LEVER_SOURCES:
        jobs = fetch_lever_jobs(source)
        for job in jobs:
            if job["id"] not in seen_jobs and is_good_match(job):
                seen_jobs.add(job["id"])
                new_jobs.append(job)

        # Himalayas - free remote jobs
    him_jobs = fetch_himalayas_jobs()
    for job in him_jobs:
        if job["id"] not in seen_jobs and is_good_match(job):
            seen_jobs.add(job["id"])
            new_jobs.append(job)

    # Arbeitnow - visa sponsorship jobs
    arb_jobs = fetch_arbeitnow_jobs()
    for job in arb_jobs:
        if job["id"] not in seen_jobs and is_good_match(job):
            seen_jobs.add(job["id"])
            job["visa_confirmed"] = True
            new_jobs.append(job)

    # Ashby companies
    for company in ASHBY_COMPANIES:
        ash_jobs = fetch_ashby_jobs(company)
        for job in ash_jobs:
            if job["id"] not in seen_jobs and is_good_match(job):
                seen_jobs.add(job["id"])
                new_jobs.append(job)
        time.sleep(0.5)

    if new_jobs:
        # Send in batches of 5
        for i in range(0, len(new_jobs), 5):
            batch = new_jobs[i:i+5]
            message = f"🚀 <b>{len(new_jobs)} New Job Match(es) Found!</b>\n"
            message += f"🕐 {datetime.now().strftime('%b %d, %I:%M %p')}\n\n"

            for job in batch:
                visa = check_visa_status(job.get("description", "") + job["title"])
                message += f"🏢 <b>{job['company'].upper()}</b>\n"
                message += f"💼 {job['title']}\n"
                message += f"📍 {job['location'] or 'USA'}\n"
                message += f"🛂 {visa}\n"
                message += f"🔗 <a href='{job['url']}'>Apply Now</a>\n\n"

            send_telegram(message)
            time.sleep(1)

        print(f"Sent {len(new_jobs)} new jobs to Telegram")
    else:
        print("No new matching jobs found")

def fetch_himalayas_jobs():
    """Fetch remote jobs from Himalayas - completely free"""
    try:
        keywords = ["python", "backend", "data engineer", 
                    "platform engineer", "software engineer", "ai engineer"]
        jobs = []
        for kw in keywords:
            url = f"https://himalayas.app/jobs/api?q={kw}&limit=20"
            response = requests.get(url, timeout=10)
            data = response.json()
            for job in data.get("jobs", []):
                jobs.append({
                    "title": job.get("title", ""),
                    "location": "Remote - " + job.get("countries", ["USA"])[0] if job.get("countries") else "Remote",
                    "url": job.get("applicationLink", ""),
                    "company": job.get("company", {}).get("name", ""),
                    "id": "him_" + str(job.get("slug", "")),
                    "description": job.get("description", "")
                })
            time.sleep(1)
        return jobs
    except Exception as e:
        print(f"Himalayas error: {e}")
        return []

def fetch_arbeitnow_jobs():
    """Fetch jobs from Arbeitnow - free, has visa sponsorship filter"""
    try:
        url = "https://www.arbeitnow.com/api/job-board-api?visa_sponsorship=true"
        response = requests.get(url, timeout=10)
        data = response.json()
        jobs = []
        for job in data.get("data", []):
            jobs.append({
                "title": job.get("title", ""),
                "location": job.get("location", "USA"),
                "url": job.get("url", ""),
                "company": job.get("company_name", ""),
                "id": "arb_" + str(job.get("slug", "")),
                "description": job.get("description", ""),
                "visa": True
            })
        return jobs
    except Exception as e:
        print(f"Arbeitnow error: {e}")
        return []

def fetch_ashby_jobs(company):
    """Fetch jobs from Ashby ATS"""
    try:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        response = requests.get(url, timeout=10)
        data = response.json()
        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "title": job.get("title", ""),
                "location": job.get("location", "USA"),
                "url": job.get("jobUrl", ""),
                "company": company,
                "id": "ash_" + str(job.get("id", "")),
                "description": job.get("descriptionHtml", "")
            })
        return jobs
    except Exception as e:
        print(f"Ashby {company} error: {e}")
        return []

# Ashby companies list
ASHBY_COMPANIES = [
    "linear", "vercel", "supabase", "retool",
    "dbt-labs", "temporal", "posthog", "fly",
    "loom", "mercury", "ramp", "deel"
]

# Run once - GitHub Actions handles scheduling
print(f"Starting job check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
check_jobs()
print(f"Job check complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

