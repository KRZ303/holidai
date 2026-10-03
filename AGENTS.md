# AGENTS.md

This file is the operating contract for autonomous agents working in this workspace. Read it before any other project work. Follow the nearest nested `AGENTS.md` when working inside a subdirectory that has one.

## Bootstrap: First Run In This Workspace

When an agent starts in a workspace with this file, it must do the following before implementation work:

1. Read this `AGENTS.md`.
2. Inspect the project enough to understand what it is:
   - list top-level files and folders
   - read existing `README.md`, package manifests, build config, test config, and obvious docs
   - identify dependency, generated, build, cache, and reference folders
3. Check whether the workspace is inside a git repository:
   - Run `git rev-parse --is-inside-work-tree`.
   - If it is a repository, inspect `git status --short`.
   - If dirty files exist, identify whether they are pre-existing user changes or changes from the current task. Assess whether they could interfere with build, test, lint, or runtime verification.
   - Do not stash, commit, discard, overwrite, or reset pre-existing user changes unless the user explicitly asks. If dirty state blocks reliable verification or implementation, ask how to proceed.
   - If it is not a repository, ask the user whether to initialize git and create/push a private remote repository. Do not run `git init`, create a remote, or push until the user explicitly confirms.
4. If `README.md` is missing, create one with:
   - project name and purpose
   - detected stack and important commands
   - setup instructions
   - build, test, lint, and verification instructions
   - project structure
5. Update this `AGENTS.md` with discovered project-specific facts when useful:
   - verification commands
   - important files and folders
   - known generated/dependency/build folders
   - pending plans
6. Ensure `.gitignore` covers dependency, build, cache, runtime, and OS artifact folders, including `.DS_Store`.
7. If inside a git repository, or if the user confirmed repository creation, commit the bootstrap changes.
8. If the user declines repository creation, continue without commits and state that changes are uncommitted because no git repository is active.

## Core Workflow

Every user request follows this loop:

1. User prompt arrives.
2. Analyze the request and ask necessary clarifying questions as soon as possible. Do not delay essential questions until after implementation.
3. Decide the current mode:
   - analyzing existing files
   - researching new ideas
   - planning for implementation
   - implementing
4. Based on that decision, dispatch a subagent with the best persona, skills, and task framing for the work.
   - Execute tasks and subagents sequentially by default.
   - Do not run parallel subagents, parallel phases, or parallel implementation tasks unless the user explicitly asks for parallel execution.
   - Use the current checked-out branch.
   - Do not use git worktrees unless the user explicitly asks.
   - Keep the main agent as supervisor, reviewer, and coordinator.
5. When the subagent finishes:
   - If files were created, modified, or deleted:
     1. Review the changes.
     2. Ask for or perform iteration if the changes are incomplete, risky, or do not match the prompt.
     3. Run the appropriate verification for the completed phase.
     4. Commit accepted phase changes with the required subagent commit format.
        - Bundle minor docs, analysis, plan-status, or `AGENTS.md` updates with the phase when they directly belong to that phase.
        - Do not stage or commit unrelated user changes.
   - If no files changed, do not commit.
6. Execute additional tasks through subagents sequentially. Finish, review, verify, and commit or reject one subagent's work before dispatching the next. The main agent preserves context by coordinating, reviewing, accepting or rejecting, committing, and tracking the overall request.
7. When the original user request is done, check for remaining modified files.
   - If files are modified, create a final commit with the required final commit format.
   - If no files are modified, report completion without a commit.

## Required Commit Formats

### Subagent Change Commit

Use this format when a subagent created, modified, or deleted files:

```text
<short descriptive title>

User prompt:
<exact user prompt that triggered this work>

Supervisor summary:
<short precise summary of the action taken by the main agent>

Subagent prompt:
<exact prompt sent to the subagent>

Subagent summary:
<short precise summary of the action taken by the subagent>
```

### Final Request Commit

Use this format when the original user request is complete and there are still uncommitted changes:

```text
<short descriptive title>

User prompt:
<exact user prompt that triggered this work>

Supervisor summary:
<short precise summary of the final action taken>

Related phase commits:
- <commit-hash> <commit subject>
- <commit-hash> <commit subject>
```

If no phase commits were made, write:

```text
Related phase commits:
None.
```

## Core Rules

- Read relevant files before modifying them.
- Preserve user changes and dirty repository state. Never reset, discard, overwrite, or revert unrelated work unless the user explicitly asks.
- Do not modify dependencies, build outputs, generated files, reference repositories, caches, or vendored code unless explicitly asked.
- Add dependency, build, cache, runtime, and OS artifacts to `.gitignore`, including `.DS_Store`.
- Do not produce happy-path-only implementations unless the user explicitly asks for a sketch or draft.
- Do not leave placeholder implementations, fake data, `TODO` code, stubs, or unimplemented branches unless explicitly asked.
- Implement real error handling. External calls, filesystem access, network calls, parsing, database access, browser automation, and process management need clear failure paths.
- Use the project's real build, lint, test, and verification commands. Do not rely on generic checks when project-specific commands exist.
- If verification cannot be run, state exactly why and what remains unverified.
- If an active plan exists for the request, follow it exactly. Do not add unrelated improvements, opportunistic refactors, or extra scope without asking.
- Do not print, commit, copy, or expose secrets, tokens, private keys, credentials, or `.env` contents.
- Do not add new dependencies until existing project options have been checked and the new dependency is justified.
- Do not run destructive filesystem or git commands such as `rm -rf`, `git reset --hard`, `git checkout --`, `git clean`, forced pushes, or mass rewrites unless the user explicitly asks for that exact operation.
- Clean temporary debug artifacts, screenshots, logs, traces, and scratch outputs before committing unless they are deliberate user-facing deliverables or required test fixtures.

## Skill And Tool Workflow Precedence

When installed skills, tools, or external workflow instructions conflict with this file, use this priority order:

1. The user's explicit prompt.
2. The nearest applicable `AGENTS.md`.
3. Project `README.md`, plans, and source-of-truth docs.
4. Installed skills, tools, and tool-specific workflows.
5. Generic model defaults.

Use installed skills and tools only when they materially help the current task or are explicitly required by the environment. Do not let broad process skills expand a small-scoped task into unrelated design docs, worktrees, parallel execution, or extra commits when this `AGENTS.md` defines a narrower workflow.

Subagents are responsible only for executing their bounded assignment using the Core Rules, File Safety Rules, and relevant Implementation Cycle. They must not run workspace bootstrap, initialize repositories, manage plans, dispatch other subagents, create commits, or run generic conversation-start workflows unless the subagent prompt explicitly asks.

Subagent prompts must begin with this marker:

```text
You are a dispatched subagent for a bounded task. Follow the task prompt and the nearest AGENTS.md, specifically Core Rules, File Safety Rules, and relevant Implementation Cycle sections. Do not run workspace bootstrap, manage plans, dispatch subagents, make commits, or run generic conversation-start workflows. If the environment provides an explicit subagent-only skip rule, apply it.
```

Known workflow overrides:

- Sequential execution in this `AGENTS.md` overrides skills that recommend parallel agents unless the user explicitly asks for parallel execution.
- Current-branch work in this `AGENTS.md` overrides skills that recommend git worktrees unless the user explicitly asks for worktrees.
- The `plans/` and `analysis/` paths in this `AGENTS.md` override skills that default to other plan or spec directories.
- The supervisor owns review and commits. Subagents should not create extra reviewer subagents or commit independently unless the prompt explicitly asks.

## Subagent Dispatch Rules

The main agent should create a subagent prompt that includes:

- task mode: analysis, research, planning, or implementation
- persona and skills needed
- exact scope
- files and folders to read first
- files and folders that must not be touched
- expected output
- verification requirements
- commit expectations, normally: subagent does not commit and supervisor commits accepted work
- dirty-worktree assumptions and whether pre-existing changes must be avoided
- summary format

Subagents must be scoped tightly enough to fit their context. Prefer one subagent per complete phase, not one subagent per tiny subtask.

Subagents and phases are sequential by default. Dispatch the next subagent only after the previous subagent's work has been reviewed, verified where applicable, accepted or rejected, and committed when it changed files. Parallel subagents are allowed only when the user explicitly requests parallel execution.

The main agent remains responsible for:

- choosing the next task
- dispatching subagents
- reviewing results
- requesting iteration
- running or confirming verification
- committing accepted changes
- keeping the overall request coherent

## Analysis Workflow

Use this workflow when analyzing existing files or researching ideas.

1. Create or update an analysis file at:

```text
analysis/<subject-name>.md
```

2. The analysis file must start with:
   - title
   - what the file is
   - scope
   - date
   - full handoff regeneration prompt containing the instructions and context needed for another agent to continue or recreate the analysis

3. Include:
   - sources inspected
   - findings
   - decisions or recommendations
   - risks and unknowns
   - next actions

4. Update `README.md` and this `AGENTS.md` if the analysis changes project understanding, commands, architecture, or workflow.
5. Commit the analysis changes when inside a repository.

## Planning Workflow

Use plans for non-trivial implementation or re-indexing work.

Plans live under:

```text
plans/<plan-goal>/
```

Each plan folder should contain:

```text
plans/<plan-goal>/masterplan-<subject>.md
plans/<plan-goal>/phase-1-<subject>.md
plans/<plan-goal>/phase-2-<subject>.md
```

The master plan must include:

- scope
- target files
- issue or goal
- proposed fix
- verification strategy
- risks and assumptions
- phase list
- pending status for each phase

If an active plan already exists for the requested work, treat the plan as the specification. Read it before implementation, follow its scope, and update it as work progresses.

Each phase file must include:

- phase goal
- files to inspect
- files likely to modify
- exact implementation tasks
- acceptance criteria
- verification commands
- risks
- status

Valid phase statuses:

- `planned`
- `in progress`
- `done`
- `blocked`
- `won't do`

After creating or updating a plan:

1. Add it to the `Pending Plans` section of this `AGENTS.md`.
2. Commit the plan if inside a repository.

After finishing a phase:

1. Mark the phase as `done` in its phase file.
2. Run verification for the completed phase.
3. Review the changes.
4. Commit the phase.

After finishing the whole plan:

1. Remove the plan folder under `plans/<plan-goal>/`.
2. Remove the entry from `Pending Plans`.
3. Commit the cleanup.

If the user or project explicitly wants durable plan history, move completed plans to `plans/archive/<plan-goal>/` instead of deleting them. Otherwise keep `plans/` transient and delete completed plan folders.

## Implementation Cycle: Webpages And Web Apps

When implementing or debugging a webpage or web app:

1. Open the app in a visible browser controller.
2. If hot reload is supported, keep the app open while editing.
3. If hot reload is not supported, or a rebuild is required:
   - stop or replace stale server/browser sessions as needed
   - rebuild
   - reopen or refresh the app
4. Track all required processes:
   - frontend dev server
   - backend server
   - workers
   - database or emulator
   - test runner
5. Avoid unnecessary rebuilds.
   - When editing frontend-only code, keep the server running if hot reload works.
   - When editing server code, restart only the process that needs restarting.
6. Verify in the browser, not only through static checks.
7. Check console errors, visible layout, interaction behavior, and responsive states when relevant.

## Implementation Cycle: No Browser Involved

When no browser is involved:

1. Find the cheapest reliable way to build, run, and verify the change end to end.
2. Prefer focused tests for narrow changes.
3. Add a test helper, fixture, script, or harness when it materially improves verification speed or coverage.
4. Avoid broad slow test suites unless the touched behavior requires them.
5. Verify behavior through the closest realistic execution path available.

## Documentation Rules

Update `README.md` when:

- setup changes
- commands change
- architecture changes
- major files or directories change
- user-facing behavior changes
- generated analysis changes the project map

Update this `AGENTS.md` when:

- workflow changes
- verification commands are discovered or changed
- important project boundaries are discovered
- generated/dependency/build folders are discovered
- pending plans are added or completed

## Source Of Truth

During bootstrap, this workspace was identified as a root bundle for vacation-planning artifacts plus a nested Booking.com scraping flow. Agents must read the relevant source-of-truth files before changing behavior they govern.

- `README.md` - root workspace overview, setup, project map, and important commands.
- `AGENTS.md` - root operating contract.
- `.gitmodules` - submodule configuration for `booking-scraper-flow/`.
- `.github/workflows/deploy-pages.yml` - GitHub Pages deployment workflow for the root landing page, Ultimate Canvas dashboard, and published reports.
- `index.html` - GitHub Pages landing page linking to the published OpenAI, Gemini, and Ultimate Canvas reports.
- `booking-scraper-flow/AGENTS.md` - nested contract for the Booking.com scraping flow.
- `booking-scraper-flow/README.md` - scraper workflow setup and usage.
- `booking-scraper-flow/SKILL.md` - skill package metadata and execution workflow.
- `booking-scraper-flow/scripts/scrape_booking.py` - Booking.com extraction script.
- `booking-scraper-flow/scripts/consolidate.py` - generated hotel-card consolidation script.
- `booking-model/` - DDD-style Booking matrix model and CSV roundtrip tooling.
  - `booking-model/src/infrastructure/property-page-repository.ts` - loader that maps `pageContent` markdown paths to committed page JSON files.
  - `booking-model/test/property-page-repository.test.ts` - repository mapping and error-handling coverage.
- `chrome-scrape-control/` - Reusable in-tab Chrome debugging and scraping automation skill package.
- `ultimate-dashboard/` - React/Rsbuild static dashboard published under `ultimate/` by the root GitHub Pages workflow.
- `skyscanner/` - DDD-style Skyscanner flight matrix model and CSV roundtrip tooling.
- `gpt/AGENTS.md` - regeneration guide for the final vacation reports.
- `gpt/README.md` - historical report timeline and handoff notes.
- `gpt/MANIFEST.txt` - packaged final report file list.
- `gpt/sources/*.md` - raw Booking.com property source cards.
- `gpt/sources/*.csv` - structured accommodation matrices.
- `gpt/ultimate-desktop.html` and `gpt/ultimate-mobile.html` - canonical final HTML reports.
- `gemini/*.html` - standalone Gemini-produced comparison/report artifacts.

## File Safety Rules

Never modify these unless explicitly asked:

- `.git/`
- dependency folders such as `node_modules/`, `.venv/`, `venv/`, vendor folders
- build outputs such as `dist/`, `build/`, `out/`, `target/`, `bin/`
- caches such as `.cache/`, `__pycache__/`, coverage outputs
- generated files unless the generation step is part of the task
- reference repositories or third-party source snapshots
- secret-bearing files such as `.env`, private keys, credential exports, and local config containing tokens

Before editing, identify whether a file is source, generated output, dependency material, reference material, or user-owned scratch.

Project-specific boundaries:

- The root workspace is a public GitHub repository at `https://github.com/KRZ303/holidai.git` on branch `main`.
- GitHub Pages for the root repository is deployed by a GitHub Actions workflow and publishes `index.html`, `ultimate/`, `gpt/ultimate-desktop.html`, `gpt/ultimate-mobile.html`, `gemini/2026-holidai-v1.html`, and `gemini/2026-holidai-v2.html`.
- `booking-scraper-flow/` is a private Git submodule at `https://github.com/KRZ303/booking-scraper-flow.git` with its own `AGENTS.md`; follow it when working there.
- Commit and push root changes in the root repository. Commit and push nested scraper changes inside `booking-scraper-flow/` first, then update and commit the root submodule pointer.
- Treat `booking-scraper-flow/examples/booking/` as reference/example data unless the user asks to regenerate examples.
- Treat `gpt/sources/` as source material and previous report artifacts. Do not overwrite it unless explicitly updating the vacation-report source set.
- Root `.DS_Store`, `gpt/.DS_Store`, nested `.DS_Store`, and Python `__pycache__/` output are generated/local artifacts. Keep them ignored and out of Git history.
- `booking-model/` and `skyscanner/` are source code folders for CSV roundtrip tooling. Keep them separate from report artifacts and source matrices.

## Verification Commands

Project-specific commands should be discovered during bootstrap and kept current here.

```bash
# Build:
# No root build system was found. Static HTML reports can be opened directly.
cd ultimate-dashboard && npm run build

# Test:
cd ultimate-dashboard && npm test
cd ultimate-dashboard && npm run typecheck
bun test booking-model/test/roundtrip.test.ts
bun test booking-model/test/property-page-repository.test.ts
bun test skyscanner/test/roundtrip.test.ts

# Lint/typecheck:
# No linter or typechecker was found. Use this Python syntax check for scraper scripts:
PYTHONPYCACHEPREFIX=/tmp/holidai-pycache python3 -m py_compile booking-scraper-flow/scripts/scrape_booking.py booking-scraper-flow/scripts/consolidate.py

# End-to-end or smoke test:
# Scraper smoke test requires agent-browser and a file containing Booking.com links:
python3 booking-scraper-flow/scripts/scrape_booking.py <path-to-file-containing-booking-links>

# Consolidation smoke test requires a Booking output directory containing index.md:
python3 booking-scraper-flow/scripts/consolidate.py <path-to-booking-directory>

# Skyscanner smoke test:
bun run skyscanner/src/cli.ts roundtrip <path-to-skyscanner-csv>

# Static report smoke test:
# Open index.html, ultimate/, gpt/ultimate-desktop.html, gpt/ultimate-mobile.html, and relevant gemini/*.html in a browser.
```

## Project Map

Update this section during bootstrap and later discovery.

```text
.
|-- AGENTS.md
|-- README.md
|-- .gitignore
|-- .gitmodules
|-- .github/
|   `-- workflows/
|       `-- deploy-pages.yml
|-- index.html
|-- booking-scraper-flow/
|   |-- .git/                  # submodule Git metadata, never version directly
|   |-- .gitignore
|   |-- AGENTS.md
|   |-- README.md
|   |-- SKILL.md
|   |-- scripts/
|   |   |-- scrape_booking.py
|   |   `-- consolidate.py
|   `-- examples/booking/         # reference scraped output and country summaries
|-- booking-model/
|   |-- src/
|   |   `-- infrastructure/property-page-repository.ts
|   |-- pages/
|   `-- test/
|       `-- property-page-repository.test.ts
|-- chrome-scrape-control/
|   |-- SKILL.md               # documentation of the CDP browser control skill
|   `-- cdp_helper.js          # native Node.js CDP WebSocket controller
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
        |-- albania.md
        |-- grecja.md
        |-- cypr.md
        |-- booking_pralka_matrix.csv
        |-- ultimate_booking_matrix.csv
        `-- *.html                 # previous and audited report artifacts
```

## Pending Plans

Add active plan folders here. Remove them after the full plan is completed, verified, committed, and the plan folder is deleted.
