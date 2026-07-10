#!/usr/bin/env python3
"""Assert each platform repo uses the SSOT reusables it's expected to (ci-adoption.yaml), or is a
documented exception. Report-only by default; set DRIFT_STRICT=true to exit non-zero on drift.
Reads each repo's workflows on the configured branch (public repos, GH_TOKEN)."""
import os, sys, json, base64, subprocess, re
try:
    import yaml
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyyaml"], check=True); import yaml

ORG, SSOT = "thorvath-slower", "seqtoid-ci-workflows"
m = yaml.safe_load(open("ci-adoption.yaml"))
branch = m.get("branch", "main")

def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

def workflows_blob(repo):
    items = gh(f"repos/{ORG}/{repo}/contents/.github/workflows?ref={branch}") or []
    blob = ""
    for it in items if isinstance(items, list) else []:
        if it["name"].endswith((".yml", ".yaml")):
            c = gh(f"repos/{ORG}/{repo}/contents/.github/workflows/{it['name']}?ref={branch}")
            if c and c.get("content"):
                blob += base64.b64decode(c["content"]).decode("utf-8", "ignore") + "\n"
    return blob

ok, drift, notes = [], [], []
for repo, gates in m["repos"].items():
    blob = None
    for gate, val in (gates or {}).items():
        if isinstance(val, str) and (val.startswith("exception:") or val.startswith("review:")):
            notes.append(f"  {repo}/{gate}: {val}"); continue
        if blob is None: blob = workflows_blob(repo)
        expected = f"{ORG}/{SSOT}/{val}"
        if re.search(re.escape(expected) + r"@", blob):
            ok.append(f"  {repo}/{gate} -> {expected}")
        else:
            drift.append(f"  {repo}/{gate}: MISSING {expected}@... on '{branch}' (re-inlined or not adopted)")

print(f"== CI SSOT drift-check (branch: {branch}) ==")
print("\nADOPTED:\n" + ("\n".join(ok) or "  (none)"))
print("\nEXCEPTIONS / REVIEW (not enforced):\n" + ("\n".join(notes) or "  (none)"))
if drift:
    print("\nDRIFT:\n" + "\n".join(drift))
    if os.environ.get("DRIFT_STRICT", "").lower() == "true":
        sys.exit(1)
    print("\n(report-only; set DRIFT_STRICT=true to fail. Adoptions live on integration until synced to main.)")
else:
    print("\nNo drift — every expected repo uses the SSOT.")
