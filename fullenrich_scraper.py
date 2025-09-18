import pandas as pd
import requests
import time
import os
import sys
from math import ceil

from utils import load_env_file, getenv_or_file

load_env_file()  # charge FULLENRICH_API_KEY si présent

INPUT_XLSX = "offres_jobup_profile_linkedin.xlsx"
OUTPUT_XLSX = "offres_jobup_enriched.xlsx"
BATCH_SIZE = 50
POLL_MAX_TRIES = 30
POLL_SLEEP = 5

API_KEY = os.getenv("FULLENRICH_API_KEY") or getenv_or_file("FULLENRICH_API_KEY", "fullenrich_api_key.txt")
if not API_KEY:
    print("❌ FULLENRICH_API_KEY manquant (dans .env ou fullenrich_api_key.txt).")
    sys.exit(1)

def send_bulk_enrichment(profiles):
    url = "https://app.fullenrich.com/api/v1/contact/enrich/bulk"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "name": "Jobup Contact Enrichment",
        "datas": [
            {
                "linkedin_url": profile,
                "enrich_fields": ["contact.profile", "contact.emails", "contact.phones"],
                "custom": {"row": str(i)}
            } for i, profile in enumerate(profiles)
        ]
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 429:
        raise RuntimeError("Rate limited by FullEnrich (429). Try later.")
    resp.raise_for_status()
    return resp.json().get("enrichment_id")

def retrieve_bulk_results(enrichment_id):
    url = f"https://app.fullenrich.com/api/v1/contact/enrich/bulk/{enrichment_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    for _ in range(POLL_MAX_TRIES):
        time.sleep(POLL_SLEEP)
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code == 429:
            time.sleep(POLL_SLEEP * 2)
            continue
        r.raise_for_status()
        data = r.json() if r.content else {}
        results = data.get("datas", [])
        if results:
            return results
    return []

def update_dataframe_with_results(df: pd.DataFrame, results: list) -> pd.DataFrame:
    cols = ["Prénom (FE)", "Nom (FE)", "Titre (FE)", "Poste (FE)", "Société (FE)", "Email (FE)", "Téléphone (FE)"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    for res in results:
        try:
            idx = int(res.get("custom", {}).get("row", -1))
            if idx < 0 or idx >= len(df):
                continue
            contact = res.get("contact", {}) or {}
            profile = contact.get("profile", {}) or {}
            position = profile.get("position", {}) or {}
            company = position.get("company", {}) or {}
            df.at[idx, "Email (FE)"] = contact.get("most_probable_email", "") or ""
            df.at[idx, "Téléphone (FE)"] = contact.get("most_probable_phone", "") or ""
            df.at[idx, "Prénom (FE)"] = profile.get("firstname", "") or ""
            df.at[idx, "Nom (FE)"] = profile.get("lastname", "") or ""
            df.at[idx, "Titre (FE)"] = profile.get("headline", "") or ""
            df.at[idx, "Poste (FE)"] = position.get("title", "") or ""
            df.at[idx, "Société (FE)"] = company.get("name", "") or ""
        except Exception:
            continue
    return df

def main():
    print("📥 Lecture:", INPUT_XLSX)
    df = pd.read_excel(INPUT_XLSX)
    profiles = df.get("LinkedIn Profile URL", pd.Series([])).dropna().astype(str)
    profiles = [p for p in profiles if p.startswith("https://www.linkedin.com/in/")]
    if not profiles:
        print("📭 Aucun profil LinkedIn /in/ valide.")
        return

    all_results = []
    total = len(profiles)
    batches = [profiles[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    for i, batch in enumerate(batches, start=1):
        print(f"🚀 Batch {i}/{len(batches)} ({len(batch)} profils)")
        try:
            enrichment_id = send_bulk_enrichment(batch)
        except Exception as e:
            print("❌ Envoi batch:", e)
            continue
        results = retrieve_bulk_results(enrichment_id)
        if results:
            all_results.extend(results)

    if not all_results:
        print("❌ Aucun résultat enrichi.")
        return

    df = update_dataframe_with_results(df, all_results)
    df.fillna("", inplace=True)
    df.to_excel(OUTPUT_XLSX, index=False)
    print(f"✅ Export: {OUTPUT_XLSX}")

if __name__ == "__main__":
    main()
