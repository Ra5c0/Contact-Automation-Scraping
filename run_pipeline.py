#!/usr/bin/env python3
"""
Run the full Auto Scrap pipeline in order with simple logging & resume flags.

Steps:
 1) update_chromedriver.py
 2) email_jobup_reader.py
 3) linkedin_company_retriever.py
 4) linkedin_profile_retriever.py
 5) fullenrich_scraper.py

Usage examples:
  python run_pipeline.py
  python run_pipeline.py --from-step 3
  python run_pipeline.py --to-step 4
  python run_pipeline.py --skip 1 --skip 2
  python run_pipeline.py --dry-run
"""

import argparse
import subprocess
import sys
from datetime import datetime

STEPS = [
    ("update_chromedriver.py", "Met à jour ChromeDriver"),
    ("email_jobup_reader.py", "Lit IMAP & extrait offres + contacts"),
    ("linkedin_company_retriever.py", "Trouve l'URL LinkedIn de l'entreprise"),
    ("linkedin_profile_retriever.py", "Trouve le profil LinkedIn du dirigeant"),
    ("fullenrich_scraper.py", "Enrichit via FullEnrich et exporte le final"),
]

PY = sys.executable or "python"

def run_step(script: str) -> int:
    print(f"\n=== ▶ {script} ===")
    start = datetime.now()
    try:
        proc = subprocess.run([PY, script], check=False)
        code = proc.returncode
    except FileNotFoundError:
        print(f"❌ Script introuvable: {script}")
        return 127
    except Exception as e:
        print(f"❌ Erreur d'exécution: {e}")
        return 1
    dur = (datetime.now() - start).total_seconds()
    status = "✅ OK" if code == 0 else f"❌ Exit {code}"
    print(f"--- {status} ({dur:.1f}s) ---\n")
    return code

def main():
    parser = argparse.ArgumentParser(description="Orchestrateur Auto Scrap")
    parser.add_argument("--from-step", type=int, default=1, help="Commencer à l'étape N (1..5)")
    parser.add_argument("--to-step", type=int, default=len(STEPS), help="Terminer à l'étape N (1..5)")
    parser.add_argument("--skip", type=int, action="append", default=[], help="Étape(s) à ignorer (peut être répétée)")
    parser.add_argument("--dry-run", action="store_true", help="N'exécute rien, affiche seulement le plan")
    args = parser.parse_args()

    if args.from_step < 1 or args.to_step > len(STEPS) or args.from_step > args.to_step:
        print("❌ Plage d'étapes invalide.")
        sys.exit(2)

    plan = []
    for idx in range(args.from_step, args.to_step + 1):
        if idx in args.skip:
            continue
        plan.append((idx, *STEPS[idx - 1]))

    if not plan:
        print("Rien à exécuter.")
        return 0

    print("Plan d'exécution:")
    for idx, script, desc in plan:
        print(f"  {idx}) {script} — {desc}")

    if args.dry_run:
        return 0

    for idx, script, desc in plan:
        code = run_step(script)
        if code != 0:
            print(f"Arrêt sur échec à l'étape {idx}.")
            return code

    print("🎉 Pipeline terminé avec succès.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
