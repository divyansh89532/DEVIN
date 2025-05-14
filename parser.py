import html
from bs4 import BeautifulSoup, NavigableString
from utils import get_response

JOB_API = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

def parse_job_details(job_id: str) -> dict:
    url = JOB_API.format(job_id=job_id)
    resp = get_response(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    data = {'job_id': job_id}
    # Top bar
    comp = soup.select_one('.top-card-layout__card a img')
    data['company'] = comp['alt'].strip() if comp and comp.has_attr('alt') else None
    title = soup.select_one('.top-card-layout__entity-info a')
    data['title'] = title.get_text(strip=True) if title else None
    loc = soup.select_one('.topcard__flavor-row .topcard__flavor--bullet')
    data['location'] = loc.get_text(strip=True) if loc else None
    date = soup.select_one('.posted-time-ago__text')
    data['date_posted'] = date.get_text(strip=True) if date else None
    apps = soup.select_one('.num-applicants__caption')
    data['applicants'] = apps.get_text(strip=True) if apps else None
    # Criteria
    for li in soup.select('ul.description__job-criteria-list li'):
        h, sp = li.find('h3'), li.find('span')
        if h and sp:
            data[h.get_text(strip=True).lower().replace(' ', '_')] = sp.get_text(strip=True)
    # Website & type
    site = soup.select_one('.topcard__org-url a')
    data['company_website'] = site['href'] if site and site.has_attr('href') else None
    remote = soup.select_one('.jobs-unified-top-card__workplace-type')
    data['workplace_type'] = remote.get_text(strip=True) if remote else None
    # Full desc
    desc = soup.select_one('.description__text')
    data['description'] = desc.get_text(separator='\n', strip=True) if desc else None
    # Structured
    details = []
    sec = soup.select_one('section.show-more-less-html')
    if sec:
        for tag in sec.find_all(['h1','h2','h3','h4','h5','h6','p','li'], recursive=True):
            txt = tag.get_text(strip=True)
            if not txt: continue
            if tag.name.startswith('h'):
                details.append(f"\n**{txt}**")
            elif tag.name == 'li':
                details.append(f"- {txt}")
            else:
                details.append(txt)
    data['all_details'] = '\n'.join(details) or None
    return data
