# backfill_pf_starter.py — Punting Form Starter backfill by month (meetings + form)
import os, re, io, json, datetime as dt, pandas as pd
from dotenv import load_dotenv
from puntingform_api import PuntingFormClient, month_key, ensure_dir

load_dotenv(".env")
PROC_ROOT = "./data/processed/puntingform"
RAW_ROOT  = "./data/raw/puntingform"
os.makedirs(PROC_ROOT, exist_ok=True)

def to_months(start="2023-01", end=None):
    if end is None:
        today = dt.date.today()
        end = f"{today.year}-{today.month:02d}"
    y0,m0 = map(int, start.split("-")); y1,m1 = map(int, end.split("-"))
    cur = dt.date(y0,m0,1)
    endd= dt.date(y1,m1,1)
    out=[]
    while cur <= endd:
        out.append((cur.year, cur.month))
        # advance month
        y = cur.year + (cur.month//12)
        m = 1 if cur.month==12 else cur.month+1
        cur = dt.date(y,m,1)
    return out

def flatten(payload):
    if not payload: return pd.DataFrame()
    if isinstance(payload, dict) and "_raw" in payload:
        return pd.read_csv(io.StringIO(payload["_raw"]))
    if isinstance(payload, dict):
        for k in ("rows","data","items","form","meetings","payLoad","payload","results"):
            if k in payload and isinstance(payload[k], list):
                return pd.DataFrame(payload[k])
        return pd.json_normalize(payload)
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    return pd.DataFrame()

def run_backfill(start="2023-01", end=None, fetch_form=True, fetch_meetings=True):
    client = PuntingFormClient()
    months = to_months(start, end)
    written= []
    for y,m in months:
        mk = month_key(y,m)
        out_dir = os.path.join(PROC_ROOT, mk)
        ensure_dir(out_dir)
        if fetch_meetings:
            try:
                # meetings list (Starter-safe); if your client exposes a meetings endpoint, prefer it
                meetings = client.get_southcoast_data(y, m)   # Starter form often includes meeting rows; reuse endpoint
                df_meet = flatten(meetings)
                if not df_meet.empty:
                    df_meet.to_csv(os.path.join(out_dir, f"{mk}__meetings.csv"), index=False)
            except Exception as e:
                print("meetings fail", mk, e)
        if fetch_form:
            try:
                form = client.get_southcoast_data(y, m)
                df_form = flatten(form)
                if not df_form.empty:
                    df_form.to_csv(os.path.join(out_dir, f"{mk}__form.csv"), index=False)
                    written.append((mk, len(df_form)))
                    print("wrote form", mk, len(df_form))
            except Exception as e:
                print("form fail", mk, e)
    return written

if __name__ == "__main__":
    w = run_backfill(start="2023-01")
    print("DONE months:", w)
