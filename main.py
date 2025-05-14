import pandas as pd
from search import extract_job_ids
from parser import parse_job_details
from output import write_outputs


def scrape_linkedin(location: str, keywords: str = 'Python (Programming Language)',
                    geo_id: str = None, filters: dict = None, total_jobs: int = 100,
                    per_page: int = 25) -> pd.DataFrame:
    ids = extract_job_ids(keywords, location, geo_id, filters, total_jobs, per_page)
    jobs = [parse_job_details(jid) for jid in ids]
    df = pd.DataFrame(jobs)
    write_outputs(df, location)
    return df

if __name__ == '__main__':
    loc = input("Enter location (e.g. 'Las Vegas, Nevada, United States'): ")
    kw = input("Enter keywords [Python default]: ") or 'Python (Programming Language)'
    print("Optional filters (enter comma-separated values, or leave blank):")
    exp = input(" Experience levels (e.g. 2,3 for Associate, Mid-Senior): ")
    jt = input(" Job types (e.g. F for Full-time, P for Part-time): ")
    flt = {}
    if exp: flt['experience'] = [x.strip() for x in exp.split(',')]
    if jt:  flt['job_type'] = [x.strip() for x in jt.split(',')]
    scrape_linkedin(loc, kw, filters=flt)
