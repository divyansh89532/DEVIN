import math
import pandas as pd
from utils import get_response, build_search_url
from bs4 import BeautifulSoup

FILTER_PARAMS = {
    'experience': 'f_E', 'job_type': 'f_JT', 'job_function': 'f_JC',
    'company_size': 'f_SB', 'remote': 'f_WT', 'posted': 'f_TPR'
}

BASE_SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

def extract_job_ids(keywords: str, location: str, geo_id: str = None,
                    filters: dict = None, total: int = 100, per_page: int = 25) -> list:
    params = {'keywords': keywords, 'location': location}
    if geo_id: params['geoId'] = geo_id
    if filters:
        for k,v in filters.items():
            if k in FILTER_PARAMS and v:
                params[FILTER_PARAMS[k]] = v
    job_ids = []
    pages = math.ceil(total / per_page)
    for page in range(pages):
        params['start'] = page * per_page
        url = build_search_url(BASE_SEARCH, params)
        resp = get_response(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for li in soup.find_all('li'):
            div = li.find('div', class_='base-card')
            if div and div.get('data-entity-urn'):
                job_ids.append(div['data-entity-urn'].split(':')[-1])
    return job_ids