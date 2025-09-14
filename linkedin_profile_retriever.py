
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import sys

from utils import find_chromedriver_binary, normalize_linkedin_url, polite_delay

INPUT_XLSX = "offres_jobup_company_linkedin.xlsx"
OUTPUT_XLSX = "offres_jobup_profile_linkedin.xlsx"

CHROMEDRIVER_PATH = find_chromedriver_binary()
if not CHROMEDRIVER_PATH:
    print("❌ ChromeDriver introuvable. Exécute d'abord update_chromedriver.py")
    sys.exit(1)

def find_ceo_profile(company_name: str) -> str | None:
    # Broaden query to include CEO/founder/director
    query = f'site:linkedin.com/in ("CEO" OR "Chief Executive" OR "Founder" OR "Managing Director") "{company_name}"'
    search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(search_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a")))
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='linkedin.com/in']")
        for a in links:
            href = a.get_attribute("href") or ""
            if "linkedin.com/in" in href:
                return normalize_linkedin_url(href)
        return None
    finally:
        driver.quit()

def main():
    df = pd.read_excel(INPUT_XLSX)
    if "Entreprise (scrapée)" not in df.columns:
        raise RuntimeError("Colonne 'Entreprise (scrapée)' absente de l'entrée.")
    out = df.copy()
    results = []
    for name in df["Entreprise (scrapée)"].fillna("").astype(str).tolist():
        if not name.strip():
            results.append(None)
            continue
        polite_delay(0.6, 1.6)
        url = find_ceo_profile(name)
        results.append(url)
    out["LinkedIn Profile URL"] = results
    # Normalize + dedupe
    out["LinkedIn Profile URL"] = out["LinkedIn Profile URL"].apply(lambda u: normalize_linkedin_url(u) if isinstance(u, str) else u)
    out.to_excel(OUTPUT_XLSX, index=False)
    print(f"✅ Export: {OUTPUT_XLSX}")

if __name__ == "__main__":
    main()
