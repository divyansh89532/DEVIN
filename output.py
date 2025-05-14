import csv
import pandas as pd

def write_outputs(df: pd.DataFrame, location: str):
    safe_loc = location.replace(' ', '_').replace(',', '')
    # CSV
    # csv_fn = f"linkedin_jobs_{safe_loc}.csv"
    # df_csv = df.copy()
    # for c in ['description', 'all_details']:
    #     if c in df_csv:
    #         df_csv[c] = df_csv[c].astype(str).str.replace('\n', '\\n')
    # df_csv.to_csv(csv_fn, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
    # print(f"Saved CSV → {csv_fn}")
    # JSONL
    json_fn = f"linkedin_jobs_{safe_loc}.jsonl"
    df.to_json(json_fn, orient='records', lines=True, force_ascii=False)
    print(f"Saved JSONL → {json_fn}")
    # XLSX
    # xls_fn = f"linkedin_jobs_{safe_loc}.xlsx"
    # with pd.ExcelWriter(xls_fn, engine='openpyxl') as writer:
    #     df_xls = df.copy()
    #     for c in ['description', 'all_details']:
    #         if c in df_xls:
    #             df_xls[c] = df_xls[c].astype(str).str.replace('\\\\n', '\n')
    #     df_xls.to_excel(writer, index=False, sheet_name='Jobs')
    # print(f"Saved XLSX → {xls_fn}")
