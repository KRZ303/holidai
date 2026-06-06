# Booking Matrix CSV Verification Plan

This document describes the current, bounded behavior of the Booking.com verification flow for a single CSV file.

## 1. Browser Environment

The scraper is designed for a single foreground terminal session that talks to one Google Chrome debug session on port `9222`.

> [!WARNING]
> Do not wrap this workflow with `/goal`, subagents, timers, monitors, watcher loops, `browser_subagent`, `agent-browser`, or any other browser tool. Those patterns create extra browsers or orchestration noise that interferes with the logged-in Booking.com tab.

Runtime guardrails:

1. The script uses stable Google Chrome only:

   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="/Users/krz/Dev/holidai/scrape/chrome-profile" "https://www.booking.com"
   ```

2. The user is responsible for logging in and leaving exactly one Booking.com tab open in that debug session.
3. Before any navigation, the script pauses and requires the terminal response `OK`.
4. The CDP helper also checks the debug target list and refuses to continue unless there is exactly one `type === "page"` target.

## 2. Paths And Outputs

- Script: [verify_matrix.py](/Users/krz/Dev/holidai/scrape/verify_matrix.py)
- Input CSV directory: `/Users/krz/Dev/holidai/research/`
- Verified CSV: `/Users/krz/Dev/holidai/scrape/{csv_name}_VERIFIED.csv`
- Progress cache: `/Users/krz/Dev/holidai/scrape/{csv_name}_cache.json`
- Markdown outputs: `/Users/krz/Dev/holidai/scrape/{csv_name}_MD/`
- Discrepancy report: `/Users/krz/Dev/holidai/scrape/{csv_name}_discrepancies.md`

## 3. CSV Source Of Truth

- Read the CSV with `encoding="utf-8-sig"` so BOM-prefixed headers normalize correctly.
- Country lookup order is `kraj`, then `\ufeffkraj`, then `Destynacja`.
- Unique property grouping is `(base_url, hotel_name)`, where `base_url` strips query parameters from the Booking URL.
- Counts come from the CSV, not from hardcoded expectations. For the current Albania file that means `90` rows and `23` unique properties unless the CSV changes.

## 4. Scraping Rules

For each grouped property:

1. Visit the row URLs for the stay lengths present in the CSV, currently expected to cover `8`, `11`, and `14` days for the standard matrices.
2. Extract the minimum numeric price found in visible Booking price nodes on the current page. This is not a promise to capture an exact canonical page price across every widget.
3. Scroll and expand the facilities section to capture the currently rendered content.
4. Preserve the currently visible Booking room table as markdown. This is not a guarantee of complete room-option analysis beyond what the page renders at scrape time.
5. Collect the visible property details already implemented in the script: title, address, coordinates, visible image links, description, review summary, up to 10 visible comments, surroundings, facilities, house rules, and important information.
6. Mark washing-machine and other boolean feature fields using the implemented text heuristics.

If navigation or evaluation fails, the script uses the existing retry prompt and eventually falls back to `TBD`.

## 5. Explicit Non-Claims

This workflow does not claim any of the following:

- A guaranteed “single, correct active tab” without both user confirmation and the helper’s exact-one-page-target check.
- Exact displayed price parity across every Booking.com widget or experiment.
- Complete room-option analysis beyond the visible room table that Booking renders.
- Pattern learning. No selector-learning subsystem is implemented.

## 6. Verification

Run syntax and sanity checks without launching a live scrape:

```bash
PYTHONPYCACHEPREFIX=/tmp/holidai-pycache python3 -m py_compile /Users/krz/Dev/holidai/scrape/verify_matrix.py /Users/krz/Dev/holidai/chrome-scrape-control/chrome_control.py
node --check /Users/krz/Dev/holidai/chrome-scrape-control/cdp_helper.js
node --check /Users/krz/Dev/holidai/scrape/cdp_helper.js
python3 -c 'import csv, urllib.parse; rows=list(csv.DictReader(open("/Users/krz/Dev/holidai/research/booking_matrix_albania.csv", encoding="utf-8-sig"))); bases={(urllib.parse.urlparse(r["link"]).scheme, urllib.parse.urlparse(r["link"]).netloc, urllib.parse.urlparse(r["link"]).path, r["nazwa"]) for r in rows}; print(len(rows), len(bases), rows[0]["kraj"])'
```

Expected CSV sanity output: `90 23 Albania`.

Do not run the full interactive scraper as part of this fix verification.
