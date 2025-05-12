import requests
from bs4 import BeautifulSoup
import math
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/107.0.0.0 Safari/537.36"
    )
}

def extract_job_ids(search_url, total_jobs, per_page=25):
    """
    Given any LinkedIn search URL, parse out jobPosting IDs by paging through.
    - search_url: full URL including query string
    - total_jobs: how many results you expect (used to compute pages)
    """
    # Parse the URL
    parsed = urlparse(search_url)
    qs = parse_qs(parsed.query)

    job_ids = []
    pages = math.ceil(total_jobs / per_page)
    for page in range(pages):
        # update the 'start' parameter
        qs['start'] = [str(page * per_page)]
        # rebuild URL
        new_query = urlencode(qs, doseq=True)
        paged_url = urlunparse(parsed._replace(query=new_query))

        resp = requests.get(paged_url, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for li in soup.find_all("li"):
            urn = li.find("div", class_="base-card") \
                    .get("data-entity-urn", "")
            job_id = urn.split(":")[-1]
            if job_id:
                job_ids.append(job_id)
    return job_ids

def fetch_job_details(job_id):
    """Fetch and parse details for a given jobPosting ID."""
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    data = {'job_id': job_id}
    # Company
    comp = soup.select_one(".top-card-layout__card a img")
    data['company'] = comp['alt'].strip() if comp else None
    # Title
    title = soup.select_one(".top-card-layout__entity-info a")
    data['title'] = title.get_text(strip=True) if title else None
    # Seniority, Employment Type, Function, Industries
    for li in soup.select("ul.description__job-criteria-list li"):
        key = li.find("h3").get_text(strip=True) \
                .lower().replace(" ", "_")
        val = li.find("span").get_text(strip=True)
        data[key] = val
    # Full Description
    desc = soup.select_one(".description__text")
    if desc:
        data['description'] = "\n".join(
            p.get_text(strip=True) for p in desc.find_all(["p","li"])
        )
    else:
        data['description'] = None

    return data

def scrape_linkedin(search_url, total_jobs_estimate, per_page=25):
    """
    Master function: given any LinkedIn search-guest URL, scrape all jobs.
    - search_url: the “seeMoreJobPostings/search” URL you copy from LinkedIn
    - total_jobs_estimate: e.g. 117 (you can also parse this dynamically if you prefer)
    """
    ids = extract_job_ids(search_url, total_jobs_estimate, per_page)
    print(f"Found {len(ids)} job IDs; fetching details…")
    all_jobs = []
    for jid in ids:
        try:
            all_jobs.append(fetch_job_details(jid))
        except Exception as e:
            print(f"Error on {jid}: {e}")
    df = pd.DataFrame(all_jobs)
    df.to_csv("linkedin_jobs_generic.csv", index=False, encoding="utf-8")
    print("Done; saved to linkedin_jobs_generic.csv")
    return df

if __name__ == "__main__":
    # Example usage: any search you like
    url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
        "keywords=Data%20Science&location=New%20York%2C%20NY%2C%20USA&"
        "geoId=102356111&start=0"
    )
    # You can estimate total_jobs by first fetching the page and parsing the count,
    # or just pass a high enough number so math.ceil() pages covers all results.
    df = scrape_linkedin(url, total_jobs_estimate=200, per_page=25)
