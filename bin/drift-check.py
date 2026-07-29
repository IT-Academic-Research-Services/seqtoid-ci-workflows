#!/usr/bin/env python3
"""Assert each platform repo uses the SSOT reusables it's expected to (ci-adoption.yaml), or is a
documented exception. Report-only by default; set DRIFT_STRICT=true to exit non-zero on drift.
Reads each repo's workflows on the configured branch (public repos, GH_TOKEN)."""
import os, sys, json, base64, subprocess, re
try:
    import yaml
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyyaml"], check=True); import yaml

ORG, SSOT = "IT-Academic-Research-Services", "seqtoid-ci-workflows"
m = yaml.safe_load(open("ci-adoption.yaml"))
branch = m.get("branch", "main")

def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

def workflows_blob(repo):
    # Returns the concatenated workflow YAML, or None if the repo's workflows dir could not be
    # READ at all (404/403 -- e.g. an internal repo the default GITHUB_TOKEN can't see cross-repo).
    # None means "unverifiable", which must NOT be conflated with "read but adoption missing" (drift).
    items = gh(f"repos/{ORG}/{repo}/contents/.github/workflows?ref={branch}")
    if not isinstance(items, list):
        return None
    blob = ""
    for it in items:
        if it["name"].endswith((".yml", ".yaml")):
            c = gh(f"repos/{ORG}/{repo}/contents/.github/workflows/{it['name']}?ref={branch}")
            if c and c.get("content"):
                blob += base64.b64decode(c["content"]).decode("utf-8", "ignore") + "\n"
    return blob

ok, drift, notes, unverified = [], [], [], []
FETCHED = {}
for repo, gates in m["repos"].items():
    for gate, val in (gates or {}).items():
        if isinstance(val, str) and (val.startswith("exception:") or val.startswith("review:")):
            notes.append(f"  {repo}/{gate}: {val}"); continue
        if repo not in FETCHED: FETCHED[repo] = workflows_blob(repo)
        blob = FETCHED[repo]
        expected = f"{ORG}/{SSOT}/{val}"
        if blob is None:
            # Access failure, not drift: cannot read this repo's workflows (token can't see it).
            unverified.append(f"  {repo}/{gate}: UNVERIFIED — cannot read {repo} workflows on '{branch}' (token lacks access; internal repo?)")
        elif re.search(re.escape(expected) + r"@", blob):
            ok.append(f"  {repo}/{gate} -> {expected}")
        else:
            drift.append(f"  {repo}/{gate}: MISSING {expected}@... on '{branch}' (re-inlined or not adopted)")

print(f"== CI SSOT drift-check (branch: {branch}) ==")
print("\nADOPTED:\n" + ("\n".join(ok) or "  (none)"))
print("\nEXCEPTIONS / REVIEW (not enforced):\n" + ("\n".join(notes) or "  (none)"))
if unverified:
    # Not drift: the check simply could not see these repos (e.g. internal repo, default
    # GITHUB_TOKEN). Warn loudly so the gap is visible, but never fail strict on it.
    print("\nUNVERIFIED (access — not counted as drift):\n" + "\n".join(unverified))
if drift:
    print("\nDRIFT:\n" + "\n".join(drift))
    if os.environ.get("DRIFT_STRICT", "").lower() == "true":
        sys.exit(1)
    print("\n(report-only; set DRIFT_STRICT=true to fail. Adoptions live on integration until synced to main.)")
else:
    print("\nNo drift — every readable repo uses the SSOT."
          + (" (some repos UNVERIFIED — see above.)" if unverified else ""))
