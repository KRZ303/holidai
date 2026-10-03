# Holidai

This workspace collects vacation-planning artifacts for a September 2026 Mediterranean trip comparison and a Booking.com scraping workflow used to produce accommodation source data.

## Stack

- Static HTML reports in `gpt/` and `gemini/`.
- React/Rsbuild dashboard in `ultimate-dashboard/`, published to GitHub Pages at `ultimate/`.
- The React dashboard loads `public/data/bookings/bookings.json.gz`, renders Booking.com hotel cards by destination, stay length, and variant, and supports per-destination hotel/flight favorites, selected trip totals, stay-length/category price ranges, and flight-option tables.
- The first favorited hotel or flight is auto-selected for trip totals, and the dashboard shows both the selected pair total and the min-max total range across favorited hotel/flight combinations.
- Dashboard Booking.com choices persist on GitHub Pages through browser `localStorage`, not cookies.
- Markdown and CSV source material in `gpt/sources/`.
- TypeScript roundtrip tooling in `booking-model/` and `skyscanner/`.
- Python 3 scripts in the private `booking-scraper-flow` Git submodule.
- `agent-browser` CLI for live Booking.com scraping.

No root package manifest, dependency lockfile, build system, test runner, or linter configuration was found.
The `ultimate-dashboard/` package has its own npm lockfile and build/test commands.

## Setup

Clone the public root repository:

```bash
git clone https://github.com/KRZ303/holidai.git
```

If you also need the private `booking-scraper-flow` submodule and have access to it, initialize it afterward:

```bash
git submodule update --init --recursive
```

For static report review, no setup is required. Open the HTML files directly in a browser.
For the React canvas dashboard:

```bash
cd ultimate-dashboard
npm ci
npm run dev
```

Published Pages entry point:

```text
https://krzkraw.github.io/holidai/
```

For the Booking.com scraper flow, install `agent-browser` and use Python 3:

```bash
npm install -g agent-browser
python3 --version
```

## Important Commands

Syntax-check the Python scripts without writing cache files into the workspace:

```bash
PYTHONPYCACHEPREFIX=/tmp/holidai-pycache python3 -m py_compile booking-scraper-flow/scripts/scrape_booking.py booking-scraper-flow/scripts/consolidate.py
cd ultimate-dashboard && npm test
cd ultimate-dashboard && npm run typecheck
cd ultimate-dashboard && npm run build
bun test booking-model/test/roundtrip.test.ts
bun test skyscanner/test/roundtrip.test.ts
bun run skyscanner/src/cli.ts roundtrip <path-to-skyscanner-csv>
```

Run the scraper against a file containing Booking.com links:

```bash
python3 booking-scraper-flow/scripts/scrape_booking.py <path-to-file-containing-booking-links>
```

Consolidate a generated Booking.com output directory:

```bash
python3 booking-scraper-flow/scripts/consolidate.py <path-to-booking-directory>
```

Review final report artifacts:

```text
index.html
ultimate/
gpt/ultimate-desktop.html
gpt/ultimate-mobile.html
gemini/2026-holidai-v1.html
gemini/2026-holidai-v2.html
```

## Project Structure

```text
.
|-- AGENTS.md
|-- README.md
|-- .gitignore
|-- .gitmodules
|-- .github/workflows/deploy-pages.yml
|-- index.html
|-- booking-scraper-flow/
|   |-- AGENTS.md
|   |-- README.md
|   |-- SKILL.md
|   |-- scripts/
|   `-- examples/booking/
|-- booking-model/
|   |-- src/
|   |   `-- infrastructure/property-page-repository.ts
|   `-- test/
|-- chrome-scrape-control/
|   |-- SKILL.md
|   `-- cdp_helper.js
|-- ultimate-dashboard/
|   |-- package.json
|   |-- package-lock.json
|   |-- rsbuild.config.ts
|   |-- tsconfig.json
|   `-- src/
|-- skyscanner/
|   |-- AGENTS.md
|   |-- README.md
|   |-- src/
|   `-- test/
|-- gemini/
|   |-- 2026-holidai-v1.html
|   `-- 2026-holidai-v2.html
`-- gpt/
    |-- AGENTS.md
    |-- README.md
    |-- MANIFEST.txt
    |-- ultimate-desktop.html
    |-- ultimate-mobile.html
    `-- sources/
```

## Repository Notes

The root workspace is a public GitHub repository:

- `origin`: `https://github.com/KRZ303/holidai.git`
- default branch: `main`
- GitHub Pages will publish from a GitHub Actions workflow
- expected site URL: `https://krzkraw.github.io/holidai/`

The nested `booking-scraper-flow/` directory is included as a private Git submodule:

- submodule remote: `https://github.com/KRZ303/booking-scraper-flow.git`
- submodule branch: `main`
- configured in `.gitmodules`

Git internals are not versioned as ordinary files. Local generated files such as `.DS_Store` and Python `__pycache__/` output are ignored and should stay out of Git history.
