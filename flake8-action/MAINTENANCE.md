# Maintenance register — flake8-action

**Purpose.** A complete inventory of what in this repo is kept current automatically
(SSOT version files + Renovate) versus what a human must maintain by hand, with the
exact file path and in-file location of each. If it's in the "human-maintained" table,
nothing will remind you — so this list is how we avoid silently drifting.

> ⚠️ **Renovate is configured (`renovate.json`) but the GitHub app is not enabled yet
> (CZID-212).** Until it is, *everything* in table B is effectively human-maintained too.

> ℹ️ **This is a GitHub Action consumed via the moving `@v2` tag.** Its two most
> important maintenance points (the `@v2` tag and the committed `dist/` bundle) have **no**
> automated updater and are easy to forget — see A1/A2.

## A. Human-maintained (Renovate / SSOT cannot track these)

| # | Item | Where (path → location in file) | Why it's manual | How to update |
|---|------|--------------------------------|-----------------|---------------|
| A1 | **The moving `@v2` major release tag** | Git ref `refs/tags/v2` (not a file); consumers do `uses: …/flake8-action@v2` | Renovate never moves *your own* release tag. This is the SSOT release mechanism: cutting a release = force-moving `v2` (and `v2-node24`) to the new commit | On release: `git tag -f v2 <sha> && git push -f origin v2` (repeat for `v2-node24`). No release workflow exists to do this — consider adding a `RELEASING.md` |
| A2 | **Committed `dist/index.js` (the bundle the runtime executes)** | `dist/index.js` (git-tracked); `action.yml` → `main: "dist/index.js"` | The Action runtime runs `dist/index.js`, not `index.js`. After any change to `index.js`/`parser.js` or a dependency bump, the bundle must be rebuilt. CI **guards** staleness (`test.yml` job `units` runs `npm run package` then `git diff --exit-code dist/`) but does **not** rebuild/commit it | `npm run package` (`ncc build index.js -o dist`), then commit `dist/`. Skipping it fails CI |
| A3 | **`runs.using:` Node runtime version** | `action.yml` → `using: "node24"` | Hardcoded string; no manager reads it. This is the point of the fork (node16→node24, CZID-204) | Edit by hand on a runtime migration; keep in lockstep with A4 and the `dist/` rebuild |
| A4 | **Self-test Node version** (must track A3) | `.github/workflows/test.yml` → `node-version: 24` | Plain literal in `with:`; Renovate doesn't bump inline tool-version literals. Must equal `action.yml` `runs.using` | Edit by hand together with A3 |
| A5 | **Self-test Python version** | `.github/workflows/test.yml` → `python-version: "3.12"` | Literal input to `setup-python`; not a tracked dependency | Edit by hand when bumping the tested Python |
| A6 | **`@actions/*` toolkit MAJOR upgrades** | `package.json` (`@actions/core`, `@actions/exec`, `@actions/github`); hold rule in `renovate.json` | Renovate is **explicitly disabled** for these majors (they need an ESM migration of `index.js` + ncc rebuild first) | Do the ESM migration, bump, `npm install`, `npm run package`, commit `dist/`; then relax the `renovate.json` hold. Minors/patches still flow via Renovate |
| A7 | **Fork-provenance / usage notes in README** | `README.md` (fork banner + usage example) | Free-form prose; no updater. **Drift:** the example still points at upstream `julianwachholz/...@v2` with stale `checkout@v3`/`setup-python@v4`, and the banner says consumers "pin by commit SHA" while the model here is the moving `@v2` tag — reconcile | Edit by hand on each release / ownership change |
| A8 | **`package.json` provenance metadata** | `package.json` (`repository.url`, `author`, `bugs`, `homepage` → upstream julianwachholz) | Carried over from upstream; not auto-updated | Edit by hand to reflect the fork |
| A9 | **Lint rules / test fixtures** | `.eslintrc.json`, `flake8_test.ini`, `lintme.py` | Config/test fixtures; no dependency manager tracks their contents | Edit by hand as the lint surface changes |

## B. Automated — SSOT version files + Renovate

| # | Item | Where (path → location in file) | Maintained by |
|---|------|--------------------------------|---------------|
| B1 | npm runtime deps (`@actions/*`) — **minor/patch only** | `package.json` `dependencies` | Renovate `npm` manager; `@actions/*` grouped (`renovate.json`). Majors held (A6) |
| B2 | npm devDeps (`@vercel/ncc`, `eslint`, `jest`) | `package.json` `devDependencies` | Renovate `npm` manager |
| B3 | Full transitive dependency tree | `package-lock.json` | Renovate `npm` (with `npmDedupe` post-update per `renovate.json`) |
| B4 | GitHub Actions `uses:` pins in this repo's CI | `.github/workflows/test.yml` (`actions/checkout@v5`, `setup-node@v6`, `setup-python@v6`) | Renovate `github-actions` manager |

> **No `.node-version`/`.nvmrc`/`.tool-versions` file exists** — so there is no SSOT Node
> file for a manager to read; the two Node literals (`action.yml`, `test.yml`) are
> independent and must be hand-synced (A3/A4).

## When you add something, update the register

If you add a new hardcoded version, a new workflow, a new moving tag, or a new
config/fixture file, add a row here. Anything not covered by Renovate's `npm` or
`github-actions` managers (or an SSOT file something actually reads) is human-maintained
by default — put it in table A. **Never forget the `dist/` rebuild (A2) and the `@v2` tag
move (A1) on release.**
