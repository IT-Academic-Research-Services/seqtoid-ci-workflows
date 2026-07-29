# seqtoid-ci-workflows — shared reusable CI workflows

The single source of truth for cross-repo CI gating on the platform. Instead of each repo
carrying its own copy of the same scan (which drifts), every repo calls the reusable workflow here. One
definition, updated once, used everywhere.

**SSOT propagation:** callers pin to the moving major tag `@v1`. Change the reusable workflow here, move
`v1`, and every caller picks it up with **no downstream edit**. (Renamed from `ci-workflows`; also hosts
the `flake8-action` collapsed in from its former standalone repo.)

## Available workflows

### `security.yml` — reusable security scan
gitleaks (secrets) + trivy (vuln + misconfig, hard-fail HIGH/CRITICAL — secrets are gitleaks' job, not trivy's) + tflint + opt-in checkov.

**Call it from a repo** (`.github/workflows/security.yml`):

```yaml
name: security
on:
  push:
  pull_request:
  merge_group:
  workflow_dispatch:
    inputs:
      run_checkov:
        type: boolean
        default: false

jobs:
  security:
    uses: thorvath-slower/seqtoid-ci-workflows/.github/workflows/security.yml@v1
    with:
      run_checkov: ${{ inputs.run_checkov || false }}
```

- The reusable's jobs check out the **caller's** repo, so each repo keeps its own **`.trivyignore`** baseline
  (accept inherited findings, hard-fail on NEW).
- Public repo, so any platform repo (public or private) can call it without an org-access setting.

### `terraform-ci.yml` — reusable Terraform fmt + validate gate
`terraform fmt -check` + per-stack (or custom) `terraform validate -backend=false` + optional codegen +
optional per-stack provider-lockfile pin (CZID-30). Pure correctness — no cloud creds / remote state.
(Converted from the earlier OpenTofu gate — the platform reverted OpenTofu → native Terraform, #370.)

**Call it from a repo** (`.github/workflows/terraform-ci.yml`):

```yaml
name: terraform-ci
on:
  push: { branches: [main] }
  pull_request:

jobs:
  terraform-ci:
    uses: thorvath-slower/seqtoid-ci-workflows/.github/workflows/terraform-ci.yml@v1
    with:
      fmt_path: infra/          # what to `terraform fmt -check -recursive`
      check_lockfile: true      # per-stack .terraform.lock.hcl pin gate (optional)
      stacks: |                 # each dir gets init(-backend=false) + validate
        infra/state-foundation/foundation
        infra/state-foundation/consumers/seqtoid-web
```

- Inputs: `fmt_path`, `stacks` (newline list) **or** `validate_command` (e.g. `make validate`, or a
  codegen+root validate), `prepare` (codegen, run after fmt), `check_lockfile`, `terraform_version`
  (default `latest`). The git-over-HTTPS config for public modules is built in.
- Repos with a more capable, repo-specific gate (e.g. cypherid-web-infra's changed-files + tiered
  validation) keep their own — uniformity only where it doesn't lose function.

### `terraform-plan.yml` — reusable Terraform plan (PR diff)

Shows the **plan diff on the PR** before merge/apply — the piece `terraform-ci` (fmt+validate, no
creds) deliberately leaves out. Assumes a **read-only** OIDC role (`czid-<env>-gh-actions-plan`, or an
override ARN), runs `terraform plan -lock=false` with **refresh ON** (so the diff reflects real drift
vs AWS), uploads the saved `tf.plan`, and posts/updates the diff as a PR comment. Hand the saved
`tf.plan` artifact to an apply job to apply the **exact reviewed plan** (no re-plan against live).

**Call it from a repo** (`.github/workflows/terraform-plan.yml`):

```yaml
name: terraform-plan
on:
  pull_request:

jobs:
  plan-dev:
    uses: thorvath-slower/seqtoid-ci-workflows/.github/workflows/terraform-plan.yml@v1
    with:
      working_directory: terraform/envs/dev/web   # dir to init/plan in
      environment: dev                            # selects the czid-dev-gh-actions-plan role
    # role_to_assume: arn:aws:iam::ACCT:role/...  # override the default role if named differently
```

- Requires the caller repo to have `AWS_ACCOUNT_ID` set as a variable (for the default role ARN) and a
  read-only `czid-<env>-gh-actions-plan` OIDC role trusting the repo. It sets `id-token: write` +
  `pull-requests: write` itself.
- Not in `selftest` (it needs a live backend + role) — validated by the adopting repos' own runs.

## Versioning

Pin to `@v1` (a moving major tag). Breaking changes bump the major. Renovate keeps the pinned tool/action
versions inside the reusable current.

## Actions

- **`flake8-action/`** — Python flake8 linter action (collapsed in from the standalone
  `thorvath-slower/flake8-action` repo). Consume as
  `uses: thorvath-slower/seqtoid-ci-workflows/flake8-action@v1`.

## Design & policy

How this SSOT works, the `@v1` moving-tag propagation model, hardening, and the
exception list: [`docs/DESIGN.md`](docs/DESIGN.md) — the authoritative reference.
