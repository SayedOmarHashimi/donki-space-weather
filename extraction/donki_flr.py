import os
import json
from datetime import date, timedelta

import pandas as pd
import duckdb
from dotenv import load_dotenv

from donki_http import get_json, TransientAPIError

load_dotenv()

API_KEY = os.environ["NASA_API_KEY"]
DB_PATH = "warehouse/space_data.duckdb"

def fetch_flr(start_date: str, end_date: str) -> list[dict]:
    url = "https://api.nasa.gov/DONKI/FLR"
    params = {"startDate": start_date, "endDate": end_date, "api_key": API_KEY}
    return get_json(url, params)

def to_dataframe(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["instruments"] = df["instruments"].apply(json.dumps)
    df["linkedEvents"] = df["linkedEvents"].apply(
        lambda x: json.dumps(x) if x is not None else None
    )
    return df

def upsert(df: pd.DataFrame):
    if df.empty:
        print("No FLR records in range — nothing to upsert.")
        return

    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_flr (
            flrID TEXT PRIMARY KEY,
            catalog TEXT,
            instruments TEXT,
            beginTime TEXT,
            peakTime TEXT,
            endTime TEXT,
            classType TEXT,
            sourceLocation TEXT,
            activeRegionNum BIGINT,
            note TEXT,
            submissionTime TEXT,
            versionId INTEGER,
            link TEXT,
            linkedEvents TEXT,
            sentNotifications TEXT
        )
    """)
    con.register("df_new", df)
    con.execute("""
        INSERT INTO raw_flr
        SELECT * FROM df_new
        ON CONFLICT (flrID) DO UPDATE SET
            catalog = EXCLUDED.catalog,
            instruments = EXCLUDED.instruments,
            beginTime = EXCLUDED.beginTime,
            peakTime = EXCLUDED.peakTime,
            endTime = EXCLUDED.endTime,
            classType = EXCLUDED.classType,
            sourceLocation = EXCLUDED.sourceLocation,
            activeRegionNum = EXCLUDED.activeRegionNum,
            note = EXCLUDED.note,
            submissionTime = EXCLUDED.submissionTime,
            versionId = EXCLUDED.versionId,
            link = EXCLUDED.link,
            linkedEvents = EXCLUDED.linkedEvents,
            sentNotifications = EXCLUDED.sentNotifications
    """)
    count = con.execute("SELECT COUNT(*) FROM raw_flr").fetchone()[0]
    print(f"Upsert complete. raw_flr now has {count} rows.")
    con.close()

def main():
    end = date.today()
    start = end - timedelta(days=7)
    try:
        records = fetch_flr(start.isoformat(), end.isoformat())
    except TransientAPIError as exc:
        # A transient NASA outage shouldn't abort the whole refresh — leave the
        # existing raw_flr data in place and let the rest of the pipeline run.
        print(f"WARNING: skipping FLR refresh — {exc}")
        return
    df = to_dataframe(records)
    upsert(df)

if __name__ == "__main__":
    main()
