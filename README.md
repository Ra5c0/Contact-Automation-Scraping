# Automation Scraping Pipeline

## Purpose
This project automates the collection and enrichment of leads from [Jobup](https://www.jobup.ch/) e-mail alerts. Each step produces an Excel file that becomes the input of the following step.

## Pipeline steps
1. **`update_chromedriver.py`** – download the latest ChromeDriver so Selenium can drive Google Chrome.
2. **`email_jobup_reader.py`** – connect to Gmail via IMAP, parse Jobup alerts, visit each job offer and extract the company, contact name and phone number. Output: `offres_jobup.xlsx`.
3. **`linkedin_company_retriever.py`** – search DuckDuckGo for the LinkedIn page of each company. Output: `offres_jobup_company_linkedin.xlsx`.
4. **`linkedin_profile_retriever.py`** – search for a CEO/founder profile on LinkedIn for every company. Output: `offres_jobup_profile_linkedin.xlsx`.
5. **`fullenrich_scraper.py`** – send the LinkedIn profiles to the FullEnrich API to retrieve e‑mail and phone information. Output: `offres_jobup_enriched.xlsx`.

## Installation
* Python 3.10+
* Google Chrome

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Environment variables
Create a `.env` file or export the following variables before running the scripts:

| Variable | Description |
| --- | --- |
| `JOBUP_EMAIL` | Gmail address receiving Jobup alerts. |
| `JOBUP_EMAIL_APP_PASSWORD` | Gmail App password used for IMAP access. |
| `FULLENRICH_API_KEY` | API key for [FullEnrich](https://app.fullenrich.com/). |

`FULLENRICH_API_KEY` may also be placed in a `fullenrich_api_key.txt` file.

## Running individual scripts
Each script can be executed on its own:

```bash
python update_chromedriver.py
python email_jobup_reader.py
python linkedin_company_retriever.py
python linkedin_profile_retriever.py
python fullenrich_scraper.py
```

## Running the whole pipeline
`run_pipeline.py` orchestrates all steps. By default it executes every script in order:

```bash
python run_pipeline.py
```

Options:

* `--from-step N` / `--to-step N` – run only a subset of steps (1‑5).
* `--skip N` – skip specific step numbers.
* `--dry-run` – show the planned steps without executing.

