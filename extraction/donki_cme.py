import os
import json
from datetime import date, timedelta

import requests
import pandas as pd
import duckdb
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["NASA_API_KEY"]
DB_PATH = "warehouse/space_data.duckdb"


def fetch_cme(start_date: str, end_date: str) -> list[dict]:
    url = "https://api.nasa.gov/DONKI/CME"
    params = {"startDate": start_date, "endDate": end_date, "api_key": API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def flatten_cme(records: list[dict]):
    """
    Splits raw nested CME JSON into three flat lists of dicts:
      - cme rows       (one per CME event)
      - analysis rows  (one per cmeAnalyses entry, FK -> activityID)
      - enlil rows     (one per enlilList entry, FK -> analysis_link)
    Also explodes impactList inside each enlil entry into its own rows,
    joined back via a foreign key to the enlil row.
    """
    cme_rows = []
    analysis_rows = []
    enlil_rows = []
    impact_rows = []

    for cme in records:
        activity_id = cme["activityID"]

        cme_rows.append({
            "activityID": activity_id,
            "catalog": cme.get("catalog"),
            "startTime": cme.get("startTime"),
            "instruments": json.dumps(cme.get("instruments")),
            "sourceLocation": cme.get("sourceLocation"),
            "activeRegionNum": cme.get("activeRegionNum"),
            "note": cme.get("note"),
            "submissionTime": cme.get("submissionTime"),
            "versionId": cme.get("versionId"),
            "link": cme.get("link"),
            "linkedEvents": json.dumps(cme.get("linkedEvents")) if cme.get("linkedEvents") is not None else None,
            "sentNotifications": json.dumps(cme.get("sentNotifications")) if cme.get("sentNotifications") is not None else None,
        })

        for analysis in cme.get("cmeAnalyses") or []:
            analysis_link = analysis.get("link")

            analysis_rows.append({
                "analysis_link": analysis_link,
                "activityID": activity_id,
                "isMostAccurate": analysis.get("isMostAccurate"),
                "time21_5": analysis.get("time21_5"),
                "latitude": analysis.get("latitude"),
                "longitude": analysis.get("longitude"),
                "halfAngle": analysis.get("halfAngle"),
                "speed": analysis.get("speed"),
                "type": analysis.get("type"),
                "featureCode": analysis.get("featureCode"),
                "imageType": analysis.get("imageType"),
                "measurementTechnique": analysis.get("measurementTechnique"),
                "note": analysis.get("note"),
                "levelOfData": analysis.get("levelOfData"),
                "tilt": analysis.get("tilt"),
                "minorHalfWidth": analysis.get("minorHalfWidth"),
                "speedMeasuredAtHeight": analysis.get("speedMeasuredAtHeight"),
                "submissionTime": analysis.get("submissionTime"),
            })

            for enlil in analysis.get("enlilList") or []:
                enlil_link = enlil.get("link")

                enlil_rows.append({
                    "enlil_link": enlil_link,
                    "analysis_link": analysis_link,
                    "modelCompletionTime": enlil.get("modelCompletionTime"),
                    "au": enlil.get("au"),
                    "estimatedShockArrivalTime": enlil.get("estimatedShockArrivalTime"),
                    "estimatedDuration": enlil.get("estimatedDuration"),
                    "rmin_re": enlil.get("rmin_re"),
                    "kp_18": enlil.get("kp_18"),
                    "kp_90": enlil.get("kp_90"),
                    "kp_135": enlil.get("kp_135"),
                    "kp_180": enlil.get("kp_180"),
                    "isEarthGB": enlil.get("isEarthGB"),
                    "isEarthMinorImpact": enlil.get("isEarthMinorImpact"),
                })

                for impact in enlil.get("impactList") or []:
                    impact_rows.append({
                        "enlil_link": enlil_link,
                        "location": impact.get("location"),
                        "arrivalTime": impact.get("arrivalTime"),
                        "isGlancingBlow": impact.get("isGlancingBlow"),
                        "isMinorImpact": impact.get("isMinorImpact"),
                    })

    return (
        pd.DataFrame(cme_rows),
        pd.DataFrame(analysis_rows),
        pd.DataFrame(enlil_rows),
        pd.DataFrame(impact_rows),
    )


def upsert_table(con, df: pd.DataFrame, table: str, create_sql: str, pk: str, update_cols: list[str]):
    if df.empty:
        print(f"No rows for {table} — nothing to upsert.")
        return

    con.execute(create_sql)
    con.register("df_new", df)

    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    con.execute(f"""
        INSERT INTO {table}
        SELECT * FROM df_new
        ON CONFLICT ({pk}) DO UPDATE SET {set_clause}
    """)

    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"Upsert complete. {table} now has {count} rows.")


def upsert_all(cme_df, analysis_df, enlil_df, impact_df):
    con = duckdb.connect(DB_PATH)

    upsert_table(
        con, cme_df, "raw_cme",
        """
        CREATE TABLE IF NOT EXISTS raw_cme (
            activityID TEXT PRIMARY KEY,
            catalog TEXT,
            startTime TEXT,
            instruments TEXT,
            sourceLocation TEXT,
            activeRegionNum BIGINT,
            note TEXT,
            submissionTime TEXT,
            versionId INTEGER,
            link TEXT,
            linkedEvents TEXT,
            sentNotifications TEXT
        )
        """,
        pk="activityID",
        update_cols=["catalog", "startTime", "instruments", "sourceLocation",
                     "activeRegionNum", "note", "submissionTime", "versionId",
                     "link", "linkedEvents", "sentNotifications"],
    )

    upsert_table(
        con, analysis_df, "raw_cme_analyses",
        """
        CREATE TABLE IF NOT EXISTS raw_cme_analyses (
            analysis_link TEXT PRIMARY KEY,
            activityID TEXT,
            isMostAccurate BOOLEAN,
            time21_5 TEXT,
            latitude DOUBLE,
            longitude DOUBLE,
            halfAngle DOUBLE,
            speed DOUBLE,
            type TEXT,
            featureCode TEXT,
            imageType TEXT,
            measurementTechnique TEXT,
            note TEXT,
            levelOfData DOUBLE,
            tilt DOUBLE,
            minorHalfWidth DOUBLE,
            speedMeasuredAtHeight DOUBLE,
            submissionTime TEXT
        )
        """,
        pk="analysis_link",
        update_cols=["activityID", "isMostAccurate", "time21_5", "latitude",
                     "longitude", "halfAngle", "speed", "type", "featureCode",
                     "imageType", "measurementTechnique", "note", "levelOfData",
                     "tilt", "minorHalfWidth", "speedMeasuredAtHeight", "submissionTime"],
    )

    upsert_table(
        con, enlil_df, "raw_cme_enlil",
        """
        CREATE TABLE IF NOT EXISTS raw_cme_enlil (
            enlil_link TEXT PRIMARY KEY,
            analysis_link TEXT,
            modelCompletionTime TEXT,
            au DOUBLE,
            estimatedShockArrivalTime TEXT,
            estimatedDuration DOUBLE,
            rmin_re DOUBLE,
            kp_18 DOUBLE,
            kp_90 DOUBLE,
            kp_135 DOUBLE,
            kp_180 DOUBLE,
            isEarthGB BOOLEAN,
            isEarthMinorImpact BOOLEAN
        )
        """,
        pk="enlil_link",
        update_cols=["analysis_link", "modelCompletionTime", "au",
                     "estimatedShockArrivalTime", "estimatedDuration", "rmin_re",
                     "kp_18", "kp_90", "kp_135", "kp_180", "isEarthGB", "isEarthMinorImpact"],
    )

    # impact rows have no natural unique key (location + enlil_link isn't
    # guaranteed unique across re-runs), so we do a delete+reinsert per
    # enlil_link batch instead of an upsert
    if not impact_df.empty:
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw_cme_impacts (
                enlil_link TEXT,
                location TEXT,
                arrivalTime TEXT,
                isGlancingBlow BOOLEAN,
                isMinorImpact BOOLEAN
            )
        """)
        enlil_links = tuple(impact_df["enlil_link"].unique())
        con.execute(
            "DELETE FROM raw_cme_impacts WHERE enlil_link IN ?",
            [enlil_links],
        )
        con.register("df_impacts", impact_df)
        con.execute("INSERT INTO raw_cme_impacts SELECT * FROM df_impacts")
        count = con.execute("SELECT COUNT(*) FROM raw_cme_impacts").fetchone()[0]
        print(f"Upsert complete. raw_cme_impacts now has {count} rows.")
    else:
        print("No rows for raw_cme_impacts — nothing to upsert.")

    con.close()


def main():
    end = date.today()
    start = end - timedelta(days=7)
    records = fetch_cme(start.isoformat(), end.isoformat())
    cme_df, analysis_df, enlil_df, impact_df = flatten_cme(records)
    upsert_all(cme_df, analysis_df, enlil_df, impact_df)


if __name__ == "__main__":
    main()