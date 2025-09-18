# email_jobup_reader.py
# -*- coding: utf-8 -*-

from imapclient import IMAPClient
import pyzmail
import pandas as pd
from bs4 import BeautifulSoup
import os, sys, time, glob, random
from typing import Optional, List, Dict

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils import load_env_file

load_env_file()

# ----------------------
# Config
# ----------------------
EMAIL_ADDR = os.getenv("JOBUP_EMAIL", "test.antho.undersales@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("JOBUP_EMAIL_APP_PASSWORD")  # ex: "huek ipka vfbw btdl"
IMAP_SERVER = "imap.gmail.com"
IMAP_FOLDER = "INBOX"
SENDER_EMAIL = "noreply@jobup.ch"
SUBJECT_KEYWORDS = ["job alert", "job offers", "offres d'emploi", "jobs"]

OUTPUT_XLSX = "offres_jobup.xlsx"

# ----------------------
# Helpers
# ----------------------
def find_chromedriver_binary() -> Optional[str]:
    # 1) dossier local standard
    pats = [
        "chromedriver/**/chromedriver.exe",
        "chromedriver/**/chromedriver",
        "**/chromedriver.exe",
        "**/chromedriver",
    ]
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            if os.path.isfile(p):
                return os.path.abspath(p)
    # 2) PATH
    for p in os.getenv("PATH", "").split(os.pathsep):
        cand = os.path.join(p, "chromedriver")
        if os.name == "nt":
            cand += ".exe"
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    # 3) fallback “classique” si tu utilises update_chromedriver.py
    fallback = os.path.join("chromedriver", "chromedriver-win64", "chromedriver.exe")
    return os.path.abspath(fallback) if os.path.isfile(fallback) else None

def polite_delay(a=0.6, b=1.4):
    time.sleep(random.uniform(a, b))

def extract_offers_from_body(body_text: str) -> List[Dict[str, str]]:
    """
    Format attendu (3 lignes par offre) :
      [titre]
      [url_jobup]
      [Entreprise, Localisation]
    """
    clean = body_text.replace("=\n", "").replace("=3D", "=")
    lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
    offers: List[Dict[str, str]] = []

    for i in range(len(lines) - 2):
        title_line = lines[i]
        url_line = lines[i + 1]
        company_line = lines[i + 2]
        if url_line.startswith("https://www.jobup.ch") and "," in company_line:
            try:
                company, location = [x.strip() for x in company_line.split(",", 1)]
                offers.append({
                    "Titre Offre": title_line,
                    "Entreprise (mail)": company,
                    "Localisation": location,
                    "URL Offre": url_line,
                })
            except Exception:
                continue
    return offers

def build_chrome(chromedriver_path: str) -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=fr-FR")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")
    service = Service(chromedriver_path)
    return webdriver.Chrome(service=service, options=opts)

def open_job_page_and_extract(url: str, chromedriver_path: str) -> Dict[str, Optional[str]]:
    options = Options()
    options.add_argument("--headless=new")   # Mets en commentaire pour débug visuel
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=fr-FR")
    options.add_argument("--window-size=1280,1800")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)

    contact_name = phone_number = company_name = None

    try:
        driver.get(url)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        accept_cookies_if_present(driver)
        time.sleep(0.3)

        # Petit scroll pour déclencher les lazy-loads
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(0.4)

        # ---- 1) Titre/Entreprise (plusieurs sélecteurs possibles)
        candidates_company = [
            "[data-cy='company-name']",
            "a[data-cy='company-name']",
            "[data-cy='company-information'] h2",
            "a[href*='/fr/entreprise/']",
            "div[class*='company'] a[href*='/entreprise/']",
        ]
        for sel in candidates_company:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                txt = el.text.strip()
                if txt:
                    company_name = txt
                    break
            except Exception:
                pass

        # ---- 2) Contact responsable (souvent caché derrière un bouton)
        # Essaye d'abord un “toggle” de contact
        reveal_btn_selectors = [
            "[data-cy='vacancy-contact-toggle']",
            "button[data-cy='vacancy-contact-toggle']",
            "//button[contains(., 'Contact') or contains(., 'Kontakt') or contains(., 'Contactez')]",
        ]
        for sel in reveal_btn_selectors:
            try:
                if sel.startswith("//"):
                    btn = driver.find_element(By.XPATH, sel)
                else:
                    btn = driver.find_element(By.CSS_SELECTOR, sel)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                if btn.is_enabled():
                    btn.click()
                    time.sleep(0.4)
                    break
            except Exception:
                pass

        contact_selectors = [
            "[data-cy='vacancy-contact-name']",
            "[data-cy='vacancy-contact'] [data-cy='name']",
            "section[id*='contact'] [class*='name']",
            "//section//*[contains(@class,'name') and string-length(normalize-space())>0]",
        ]
        for sel in contact_selectors:
            try:
                if sel.startswith("//"):
                    el = driver.find_element(By.XPATH, sel)
                else:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                txt = el.text.strip()
                if txt:
                    contact_name = txt
                    break
            except Exception:
                pass

        # ---- 3) Téléphone (parfois “Afficher le numéro”)
        # Essaye de cliquer sur un bouton “voir/afficher le numéro”
        show_phone_candidates = [
            "//button[contains(., 'Voir le numéro')]",
            "//button[contains(., 'Afficher le numéro')]",
            "//button[contains(., 'Show phone')]",
            "//a[contains(@href,'tel:') and string-length(normalize-space())=0]",  # parfois lien vide → cliquer avant
        ]
        for xp in show_phone_candidates:
            try:
                btn = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                if btn.is_enabled():
                    btn.click()
                    time.sleep(0.5)
                    break
            except Exception:
                pass

        # Ensuite on lit un lien tel:
        try:
            tel_el = driver.find_element(By.CSS_SELECTOR, "a[href^='tel:']")
            txt = tel_el.text.strip()
            if not txt:
                # fallback: récupérer le href (tel:+41...)
                txt = tel_el.get_attribute("href") or ""
                txt = txt.replace("tel:", "").strip()
            phone_number = txt or None
        except Exception:
            pass

        # ---- 4) Ultime fallback pour l’entreprise: meta/breadcrumbs
        if not company_name:
            try:
                # meta og:site_name ou og:title contiennent parfois le nom
                metas = driver.find_elements(By.CSS_SELECTOR, "meta[property='og:site_name'], meta[property='og:title']")
                for m in metas:
                    val = (m.get_attribute("content") or "").strip()
                    if val and len(val) > 2:
                        company_name = val
                        break
            except Exception:
                pass

    finally:
        # Pour débug: sauvegarder une capture si rien trouvé
        if not (contact_name or phone_number or company_name):
            try:
                driver.save_screenshot("debug_jobup.png")
                print("🖼  Capture page dans debug_jobup.png (pour inspection).")
            except Exception:
                pass
        driver.quit()

    return {
        "Contact Offre": contact_name,
        "Téléphone Offre": phone_number,
        "Entreprise (scrapée)": company_name,
    }

def accept_cookies_if_present(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # tente quelques variantes (FR/EN/DE)
    candidates_css = [
        "#onetrust-accept-btn-handler",
        "button[aria-label='Accepter tout']",
        "button[aria-label='Tout accepter']",
        "button[aria-label='Accept all']",
        "button[aria-label='Alle akzeptieren']",
    ]
    for sel in candidates_css:
        try:
            btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            btn.click()
            time.sleep(0.3)
            return
        except Exception:
            pass

    candidates_xpath = [
        "//button[contains(., 'Accepter')]",
        "//button[contains(., 'Tout accepter')]",
        "//button[contains(., 'Accept all')]",
        "//button[contains(., 'Alle akzeptieren')]",
    ]
    for xp in candidates_xpath:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            time.sleep(0.3)
            return
        except Exception:
            pass

# ----------------------
# Main
# ----------------------
def fetch_jobup_emails() -> None:
    if not EMAIL_APP_PASSWORD:
        print("❌ Mot de passe d'application Gmail manquant dans .env (JOBUP_EMAIL_APP_PASSWORD).")
        sys.exit(1)

    chromedriver_path = find_chromedriver_binary()
    if not chromedriver_path or not os.path.isfile(chromedriver_path):
        print("❌ ChromeDriver introuvable. Lance d'abord: python update_chromedriver.py")
        sys.exit(1)

    all_rows: List[Dict[str, Optional[str]]] = []

    with IMAPClient(IMAP_SERVER) as server:
        server.login(EMAIL_ADDR, EMAIL_APP_PASSWORD)
        server.select_folder(IMAP_FOLDER)

        messages = server.search(["UNSEEN"])
        print(f"🔍 {len(messages)} e-mails non lus.")

        for uid in messages:
            data = server.fetch([uid], ["BODY[]", "FLAGS"])
            raw = data[uid][b"BODY[]"]
            msg = pyzmail.PyzMessage.factory(raw)

            subject = (msg.get_subject() or "").strip()
            from_email = (msg.get_addresses("from")[0][1] if msg.get_addresses("from") else "").strip()

            if SENDER_EMAIL.lower() not in from_email.lower():
                continue
            if not any(k in subject.lower() for k in SUBJECT_KEYWORDS):
                continue

            # Corps du message
            body: Optional[str] = None
            if msg.text_part:
                body = msg.text_part.get_payload().decode(msg.text_part.charset or "utf-8", errors="ignore")
            elif msg.html_part:
                html = msg.html_part.get_payload().decode(msg.html_part.charset or "utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                body = soup.get_text("\n")

            if not body:
                continue

            offers = extract_offers_from_body(body)
            for off in offers:
                polite_delay()
                details = open_job_page_and_extract(off["URL Offre"], chromedriver_path)
                row: Dict[str, Optional[str]] = {**off, **details}
                all_rows.append(row)

    if not all_rows:
        print("📭 Aucun contenu exporté.")
        return

    df = pd.DataFrame(all_rows)
    # dédup stricte sur l’URL
    df.drop_duplicates(subset=["URL Offre"], inplace=True)
    df.to_excel(OUTPUT_XLSX, index=False)
    print(f"✅ Export: {OUTPUT_XLSX} ({len(df)} lignes)")

if __name__ == "__main__":
    fetch_jobup_emails()
