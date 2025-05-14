import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
import math
import pandas as pd
from urllib.parse import quote_plus, urlencode, urlparse, parse_qs, urlunparse
import time
import html
import csv 

#  Resolved error 429 Too Many Requests by implementing a retry mechanism this is done because linkedIn has a rate limit to avoid scrapping
#  Resolved error 403 Forbidden by adding a user agent to the headers


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/107.0.0.0 Safari/537.36"
    )
}

# Mapping for common LinkedIn guest API filter parameters
FILTER_PARAMS = {
    'experience': 'f_E',        # e.g. ['2','3'] for "Associate" and "Mid-Senior"
    'job_type': 'f_JT',         # e.g. ['F','P','C','I']
    'job_function': 'f_JC',     # e.g. ['1','2','3'] categories
    'company_size': 'f_SB',     # e.g. ['1','2','3']
    'remote': 'f_WT',           # e.g. ['1'] for On-site, ['2'] Remote, etc.
    'posted': 'f_TPR'           # e.g. ['r2592000'] posted within 30 days
}

def build_search_url(
    keywords: str = None,
    location: str = None,
    geo_id: str = None,
    filters: dict = None,
    start: int = 0
) -> str:
    """
    Construct a LinkedIn guest search URL including any provided filters.
    filters: dict where keys are one of FILTER_PARAMS keys and
             values are lists of strings for that parameter.
    """
    base = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    qs = {}
    if keywords:
        qs['keywords'] = keywords
    if location:
        qs['location'] = location
    if geo_id:
        qs['geoId'] = geo_id
    # apply optional filters
    if filters:
        for key, vals in filters.items():
            if key in FILTER_PARAMS and vals:
                qs[FILTER_PARAMS[key]] = vals
    qs['start'] = start
    # encode with doseq for lists
    query = urlencode(qs, doseq=True, quote_via=quote_plus)
    return f"{base}?{query}"


def extract_job_ids(search_url: str, total_jobs: int, per_page: int = 25) -> list:
    """
    Page through the LinkedIn search URL and collect all job IDs.
    """
    job_ids = []
    pages = math.ceil(total_jobs / per_page)

    for page in range(pages):
        # update start offset
        parsed = urlparse(search_url)
        qs = parse_qs(parsed.query)
        qs['start'] = [str(page * per_page)]
        new_query = urlencode(qs, doseq=True, quote_via=quote_plus)
        paged_url = urlunparse(parsed._replace(query=new_query))

        resp = requests.get(paged_url, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for li in soup.find_all('li'):
            div = li.find('div', class_='base-card')
            if not div:
                continue
            urn = div.get('data-entity-urn', '')
            job_id = urn.split(':')[-1]
            if job_id:
                job_ids.append(job_id)
    return job_ids


def parse_job_details(job_id: str) -> dict:
    """
    Fetch and parse comprehensive details of a LinkedIn job posting.
    """
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    retries = 3

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS)
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 429:
                wait_time = 5 * (attempt+1)
                print(f"Rate limit exceeded, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise e 
    else:
        print(f"Failed to fetch job details after {retries} attempts for JOB ID: {job_id}")


    soup = BeautifulSoup(resp.text, 'html.parser')

    data = {'job_id': job_id}
    # --- Top Bar Info ---
    data['company'] = None
    comp = soup.select_one('.top-card-layout__card a img')
    if comp and comp.has_attr('alt'):
        data['company'] = comp['alt'].strip()

    data['title'] = None
    title = soup.select_one('.top-card-layout__entity-info a')
    if title:
        data['title'] = title.get_text(strip=True)

    data['location'] = None
    loc = soup.select_one('.topcard__flavor-row .topcard__flavor--bullet')
    if loc:
        data['location'] = loc.get_text(strip=True)
    else:
        data['location'] = None    

    data['date_posted'] = None
    date = soup.select_one('.posted-time-ago__text')
    if date:
        data['date_posted'] = date.get_text(strip=True)

    data['applicants'] = None
    apps = soup.select_one('.num-applicants__caption')
    if apps:
        data['applicants'] = apps.get_text(strip=True)

    # --- Criteria Filters ---
    for li in soup.select('ul.description__job-criteria-list li'):
        header = li.find('h3')
        span = li.find('span')
        if header and span:
            key = header.get_text(strip=True).lower().replace(' ', '_')
            data[key] = span.get_text(strip=True)

    # --- Additional Fields ---
    # Company website, if available
    site = soup.select_one('.topcard__org-url a')
    data['company_website'] = site['href'] if site and site.has_attr('href') else None

    # Employment type / remote flag
    remote = soup.select_one('.job-view-layout__job-insight .jobs-unified-top-card__workplace-type')
    data['workplace_type'] = remote.get_text(strip=True) if remote else None

    # Full description
    desc = soup.select_one('.description__text')
    if desc:
        lines = [tag.get_text(strip=True) for tag in desc.find_all(['p', 'li']) if tag.get_text(strip=True)]
        data['description'] = '\n'.join(lines)
    else:
        data['description'] = None

    # --- Structured Full Text from show-more-less-html__markup ---
    structured_details = []
    # 1. Locate the clamp‐after‐5 div
    div_markup = soup.select_one(
        "section.show-more-less-html > div.show-more-less-html__markup"
    )
    if div_markup:
        # # 2. Grab its raw (entity-encoded) inner HTML
        # raw = div_markup.decode_contents()
        # # 3. Unescape HTML entities into real tags
        # unescaped = html.unescape(raw)
        # # 4. Re‐parse into a fresh BeautifulSoup tree
        # inner = BeautifulSoup(unescaped, "html.parser")

        # # 5. Iterate only the top-level children in order
        # for block in inner.find_all(recursive=False):
        #     # plain text at top level
        #     if isinstance(block, NavigableString):
        #         txt = block.strip()
        #         if txt:
        #             structured_details.append(txt)
            
        #     elif block.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
        #         heading = block.get_text(strip=True)
        #         if heading:
        #             structured_details.append(f"\n**{heading}**")
        #     elif block.name == "strong":
        #         heading = block.get_text(strip=True)
        #         if heading:
        #             structured_details.append(f"\n**{heading}**")

        #     # paragraphs
        #     elif block.name == "p":
        #         para = block.get_text(strip=True)
        #         if para:
        #             structured_details.append(para)

        #     # bullet lists
        #     elif block.name == "ul":
        #         for li in block.find_all("li"):
        #             bullet = li.get_text(strip=True)
        #             if bullet:
        #                 structured_details.append(f"- {bullet}")

        #     # explicit line breaks
        #     elif block.name == "br":
        #         structured_details.append(" ")

        #     # any other wrapper tags
        #     else:
        #         text = block.get_text(strip=True)
        #         if text:
        #             structured_details.append(text)
        for tag in div_markup.find_all(['p', 'li', 'h2', 'h3', 'h4', 'h5', 'h6'],recursive=True):
            txt = tag.get_text(strip=True)
            if not txt: continue
            if tag.name in ['h1','h2','h3','h4','h5','h6']:
                structured_details.append(f"\n**{txt}**")
            elif tag.name == 'li':
                structured_details.append(f"- {txt}")
            else:
                structured_details.append(txt)

    data["all_details"] = "\n".join(structured_details).strip() or None


    return data


def scrape_linkedin(
    location: str,
    keywords: str = 'Python (Programming Language)',
    geo_id: str = None,
    filters: dict = None,
    total_jobs_estimate: int = 100,
    per_page: int = 25
) -> pd.DataFrame:
    """
    Scrape LinkedIn jobs by location, with optional keywords, geo_id, and filters.
    Returns a DataFrame with all extracted fields.
    """
    # Build initial search URL
    search_url = build_search_url(keywords, location, geo_id, filters, start=0)
    # Collect job IDs
    job_ids = extract_job_ids(search_url, total_jobs_estimate, per_page)
    print(f"Found {len(job_ids)} jobs for location '{location}' with filters={filters}")  

    # Fetch details
    all_jobs = []
    for jid in job_ids:
        try:
            all_jobs.append(parse_job_details(jid))
        except Exception as e:
            print(f"Error parsing job {jid}: {e}")

    # Create DataFrame & save
    df = pd.DataFrame(all_jobs)
    safe_loc = location.replace(' ', '_').replace(',', '')

        # 1) Replace real newlines with literal “\n”
    for col in ['description', 'all_details']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('\n', '\\n')


    filename = f"linkedin_jobs_{safe_loc}.csv"
    df.to_csv(filename, index=False, encoding='utf-8',quoting=csv.QUOTE_ALL) # wrap every field in quotes because of the description field 
    print(f"Saved details to {filename}")


    # 3) Write JSON‑lines
    json_filename = f"linkedin_jobs_{safe_loc}.jsonl"
    # each line is one JSON object, full text (with real \n) still intact
    df.to_json(
        json_filename,
        orient='records',
        lines=True,
        force_ascii=False
    )
    print(f"Saved JSON-Lines → {json_filename}")

    # 4) Write XLSX
    xlsx_filename = f"linkedin_jobs_{safe_loc}.xlsx"
    with pd.ExcelWriter(xlsx_filename, engine='openpyxl') as writer:
        # rewind description/all_details to real newlines for Excel
        df_excel = df.copy()
        for col in ['description', 'all_details']:
            if col in df_excel.columns:
                df_excel[col] = df_excel[col].astype(str).str.replace('\\\\n', '\n')
        df_excel.to_excel(writer, index=False, sheet_name='Jobs')
        # optionally you could auto‐adjust column widths or set wrap‐text via openpyxl here
    print(f"Saved Excel → {xlsx_filename}")

    return df

if __name__ == '__main__':
    # Example interactive usage
    loc = input("Enter location (e.g. 'Las Vegas, Nevada, United States'): ")
    kw = input("Enter keywords (or press Enter for default 'Python'): ") or 'Python (Programming Language)'
    # Prompt for any filters
    print("Optional filters (enter comma-separated values, or leave blank):")
    exp = input("  Experience levels (e.g. 2,3 for Associate, Mid-Senior): ")
    jt = input("  Job types (e.g. F for Full-time, P for Part-time): ")
    filters_input = {}
    if exp:
        filters_input['experience'] = [x.strip() for x in exp.split(',')]
    if jt:
        filters_input['job_type'] = [x.strip() for x in jt.split(',')]

    df = scrape_linkedin(location=loc, keywords=kw, filters=filters_input)
    print(df.head())
