# CI SSOT — design & rollout plan

**Goal:** make `seqtoid-ci-workflows` a *real* single source of truth for cross-repo CI — clean, strong, and
propagating so that **one edit in the SSOT rolls out everywhere with no downstream change**.

**Status: APPROVED (2026-07-01) — the hybrid model (§2 option C).** This is the authoritative reference doc.
Implementation epic: #408 (+ children). Prior: #406/#405 (rename/flake8, done), #407 folded into #408.

---

## 1. Current state (surveyed)

| Gate | Where it lives today | Problem |
|---|---|---|
| Security scan (gitleaks/trivy/tflint/checkov) | inline in **seqtoid-web/security-scan.yml** + **czid-infra/security.yml** | 2 full copies; a reusable `security.yml` exists in the SSOT but is unused |
| Terraform fmt+validate | inline in **cypherid-workflow-infra/validate.yml**, **cypherid-web-infra/terraform_ci.yml**, **czid-infra/terraform-ci.yml** | 3 copies of the same gate; the SSOT reusable `terraform-ci.yml` consolidates them |
| flake8 | **SSOT** (`seqtoid-ci-workflows/flake8-action@v1`) | ✅ the one thing centralized |
| Richer per-repo gate | **cypherid-web-infra/validate-stack.yml** (internal reusable) | intentional exception (tiered validation) |

Consequence: a CI change (e.g. the OpenTofu→Terraform revert) has to be made in every repo. That's the drift
the SSOT was meant to kill.

## 2. The core decision — propagation model

This is the crux: "update the SSOT only" (moving ref) vs "strong/secure/reproducible" (immutable pins).

| Option | Consumer pins | Rollout | Verdict |
|---|---|---|---|
| **A. Moving major tag `@v1`** | `…/security.yml@v1` | move `v1` → instant everywhere | ✅ single-edit, but a mutable ref = trust/repro concern |
| **B. Immutable `@sha` + Renovate** | `…@<sha>` | Renovate opens N bump PRs | secure/reproducible, but rollout = N downstream PRs (violates "SSOT-only") **and needs Renovate enabled (blocked, CZID-212)** |
| **C. HYBRID (recommended)** | `…@v1` (moving) for **our** SSOT | move `v1` → instant | ✅ SSOT-only rollout **and** strong — see below |

### Recommendation: **Option C — hybrid**
- **Consumer → SSOT edge:** pin our reusable workflows/actions by the **`@v1` moving major tag**. One edit +
  moving `v1` propagates to every repo. Exactly the "only update the SSOT" property you want.
- **SSOT → third-party edge:** *inside* the reusable workflows, pin every third-party action **by full SHA**,
  and let Renovate bump those **in one place (the SSOT)**. So third-party supply-chain risk is controlled, and
  a tool/action bump is **one PR in the SSOT**, never N across consumers.
- **Why the moving `@v1` is safe here (unlike a random third-party action):** it's *our* repo, and we harden it
  (below). The classic moving-tag risk is a compromised upstream; we remove that by controlling + gating the repo.

Net: consumers get instant, zero-downstream-edit propagation; the platform keeps SHA-level security where it
matters (third-party code); tool versions are managed in exactly one file each.

## 3. What is centralized vs. stays local

**Centralize (uniform gates, in the SSOT):**
- `security.yml` — gitleaks + trivy + tflint + checkov, tuned per caller via inputs (`trivy_scanners`,
  `run_checkov`, per-repo `.trivyignore` read from the caller). Works for IaC *and* app repos.
- `terraform-ci.yml` — fmt + validate (+ per-stack lockfile gate), shaped by inputs (`fmt_path`, `stacks`,
  `validate_command`, `prepare`, `check_lockfile`).
- `flake8-action/` (done).
- **Tool version pins** (trivy/tflint/checkov/terraform versions) live *inside* these reusables → bumping a
  scanner = one SSOT edit.

**Stays local (repo-specific, layered on top):**
- App test suites (seqtoid-web Ruby/JS/rspec/jest), build/deploy/argocd workflows.
- Genuinely richer gates (cypherid-web-infra `validate-stack.yml`) — kept, but its *security* portion still
  calls the reusable `security.yml`. Uniformity only where it doesn't lose function.

**Explicit exception list** is documented in the SSOT README so "why isn't repo X on the SSOT" is never a mystery.

## 4. Making it strong (not just centralized)

1. **Harden the SSOT repo:** branch protection on `main`/`integration` (required review, no force-push) +
   **tag protection on `v1*`** so the moving tag can't be moved without a reviewed release. This is what makes a
   moving tag trustworthy.
2. **Self-test (dogfood):** the SSOT runs its *own* reusable workflows against its own content on every PR, and
   a release/move of `v1` is gated on that passing. The SSOT can't ship a broken gate.
3. **Drift enforcement:** a small meta-check (in the SSOT or the platform-harness) that asserts every platform
   repo's CI either calls the SSOT reusables or is on the documented exception list — so nobody silently
   re-inlines. Runs on a schedule + on the SSOT.
4. **Third-party SHA-pinning + Renovate** in the SSOT (per §2) — the security floor.

## 5. SSOT repo structure (target)

```
seqtoid-ci-workflows/
  .github/workflows/
    security.yml         # reusable (workflow_call) — SHA-pinned third-party actions inside
    terraform-ci.yml     # reusable (workflow_call)
    selftest.yml         # dogfoods the reusables on this repo (gates releases)
  flake8-action/         # composite/JS action
  renovate.json          # bumps the internal third-party SHA pins (one place)
  README.md              # the contract, @v1 versioning policy, exception list
```
Callers add a thin wrapper (≤10 lines) per gate, pinned `@v1`.

## 6. Rollout plan (order — one verified PR each)

0. **Harden + self-test the SSOT** (§4.1/4.2), SHA-pin its internals, add Renovate config. *(No consumer impact.)*
1. **SSOT dogfoods itself** — replace czid-infra's inline `security.yml` + `terraform-ci.yml` with thin `@v1`
   wrappers. Proves the pattern on the repo we control.
2. **cypherid-workflow-infra** — `validate.yml` → `terraform-ci.yml@v1`; normalize `check.yml` triggers.
3. **seqtoid-web** — `security-scan.yml` → `security.yml@v1` (app-tuned inputs).
4. **cypherid-web-infra** — keep `validate-stack.yml`; adopt `security.yml@v1` for its security portion; rename
   `tofu_ci.yml`.
5. **Add the drift meta-check** (§4.3) once ≥2 repos are on it.

**Per-repo recipe:** read the inline job → map to reusable inputs → replace with the `@v1` wrapper → **verify CI
preserves behavior** (manual `workflow_dispatch` where a gate isn't PR-triggered) → merge to integration. Never
batch — each PR changes how a repo's CI runs.

**Trigger policy (normalize while adopting):** CI gates fire on `pull_request` + `push:[main]` + `merge_group`.
The current `workflow_dispatch`-only gates (cwi `check.yml`) get proper PR triggers so they actually gate.

## 7. Decisions (approved 2026-07-01)
1. **Propagation model → HYBRID.** Consumers pin our reusables by the `@v1` moving major tag (SSOT-only,
   zero-downstream rollout); third-party actions/tools are SHA-pinned *inside* the reusables and bumped in the
   one SSOT repo. Not full SHA-pinning of our own SSOT (that would reintroduce downstream churn).
2. **Renovate → proceed now with manual internal bumps** (still one place); wire Renovate to auto-bump the
   internal SHA pins once the app is enabled (CZID-212). Not blocked on it.
3. **Exception → yes.** cypherid-web-infra's `validate-stack.yml` stays a richer local gate; its **security**
   portion still calls the reusable `security.yml@v1`. Exceptions are listed in the SSOT README.
4. **Triggers → normalize.** Dispatch-only gates get real `pull_request` + `push:[main]` + `merge_group`
   triggers as they adopt, so they actually gate.
