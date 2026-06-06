# AGENTS.md

Operating contract for autonomous agents working in `~/Dev/holidai/scrape`.

## 1. Project Context

This directory contains the Booking.com matrix verification flow:

- Script: [verify_matrix.py](/Users/krz/Dev/holidai/scrape/verify_matrix.py)
- Local plan/spec: [scrape-plan.md](/Users/krz/Dev/holidai/scrape/scrape-plan.md)
- CDP helper copy: [cdp_helper.js](/Users/krz/Dev/holidai/scrape/cdp_helper.js)
- Shared Chrome helper: [chrome_control.py](/Users/krz/Dev/holidai/chrome-scrape-control/chrome_control.py)
- Input CSV directory: `/Users/krz/Dev/holidai/research/`
- Outputs:
  - verified CSV: `/Users/krz/Dev/holidai/scrape/{csv_name}_VERIFIED.csv`
  - cache: `/Users/krz/Dev/holidai/scrape/{csv_name}_cache.json`
  - markdown directory: `/Users/krz/Dev/holidai/scrape/{csv_name}_MD/`
  - discrepancy report: `/Users/krz/Dev/holidai/scrape/{csv_name}_discrepancies.md`

## 2. Hard Execution Guardrails

Run this scraper in one foreground terminal session only.

- Do not use `/goal`, subagents, timers, monitors, background watchers, browser tools, or repeated automation loops around the scraper.
- Do not open separate automation browsers. The scraper talks directly to the Chrome DevTools Protocol on port `9222`.
- The user owns browser readiness. The script must pause before navigation until the user confirms the browser state.

## 3. Chrome Setup

Use stable Google Chrome only.

1. Quit Google Chrome completely if you want a fresh debug session.
2. Launch Chrome from Terminal with the dedicated scraper profile:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="/Users/krz/Dev/holidai/scrape/chrome-profile" "https://www.booking.com"
```

3. Log in to Booking.com in that Chrome profile if needed.
4. Leave exactly one Booking.com tab open in the debug session.
5. Return to the terminal and type `OK` when the script asks for confirmation.
6. Any response other than `OK` must end the run cleanly before navigation.

The CDP helper refuses to pick a target if there are zero or multiple `type === "page"` targets.

## 4. Data And Scraping Rules

- Treat the CSV as the source of truth for row count, grouping inputs, and country values.
- Read CSV files with BOM-safe handling. Albania currently means `90` rows and `23` unique properties unless the CSV changes.
- Group unique properties by `(base_url, hotel_name)`, where `base_url` is the Booking URL without query parameters.
- Country fallback order is `kraj`, then `\ufeffkraj`, then `Destynacja`.
- For prices, record the minimum numeric value found in visible Booking price nodes for the current page.
- For room details, preserve the currently visible Booking room table as rendered on the page. Do not claim complete room-option coverage beyond what is visible.
- If navigation, evaluation, CAPTCHA recovery, or CDP commands fail, let the existing retry or `TBD` flow handle it.

## 5. Run Command

```bash
python3 /Users/krz/Dev/holidai/scrape/verify_matrix.py [/Users/krz/Dev/holidai/research/booking_matrix_turcja_kreta.csv]
```

If no CSV argument is passed, the script defaults to `booking_matrix_turcja_kreta.csv`.

## 6. Verification Notes

- Python syntax check:

```bash
PYTHONPYCACHEPREFIX=/tmp/holidai-pycache python3 -m py_compile /Users/krz/Dev/holidai/scrape/verify_matrix.py /Users/krz/Dev/holidai/chrome-scrape-control/chrome_control.py
```

- JS syntax check:

```bash
node --check /Users/krz/Dev/holidai/chrome-scrape-control/cdp_helper.js
node --check /Users/krz/Dev/holidai/scrape/cdp_helper.js
```

- CSV sanity check:

```bash
python3 -c 'import csv, urllib.parse; rows=list(csv.DictReader(open("/Users/krz/Dev/holidai/research/booking_matrix_albania.csv", encoding="utf-8-sig"))); bases={(urllib.parse.urlparse(r["link"]).scheme, urllib.parse.urlparse(r["link"]).netloc, urllib.parse.urlparse(r["link"]).path, r["nazwa"]) for r in rows}; print(len(rows), len(bases), rows[0]["kraj"])'
```

Expected output: `90 23 Albania`.
