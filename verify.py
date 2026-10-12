"""Checks that the pinned sources are untouched and that a fresh build reproduces the published tables exactly.

    python verify.py            # rebuild, then compare every file against SHA256SUMS
    python verify.py --update   # (maintainer) rewrite SHA256SUMS from the current build
"""
import glob, hashlib, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUMS = os.path.join(HERE, "SHA256SUMS")
sha = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()


def current():
    files = sorted(glob.glob(os.path.join(HERE, "sources", "*.*")))
    files = [f for f in files if not f.endswith("README.md")]
    files += sorted(glob.glob(os.path.join(HERE, "salo-evening-dataset", "*.csv")))
    return {os.path.relpath(f, HERE).replace("\\", "/"): sha(f) for f in files}


subprocess.run([sys.executable, os.path.join(HERE, "build_dataset.py")], cwd=HERE, check=True,
               stdout=subprocess.DEVNULL)
now = current()
if "--update" in sys.argv:
    with open(SUMS, "w", encoding="utf-8", newline="\n") as fh:
        for k, v in now.items():
            fh.write(f"{v}  {k}\n")
    print(f"wrote {len(now)} checksums to SHA256SUMS")
    sys.exit(0)

expected = {}
for line in open(SUMS, encoding="utf-8"):
    h, name = line.strip().split("  ", 1)
    expected[name] = h
bad = [n for n, h in expected.items() if now.get(n) != h]
missing = [n for n in expected if n not in now]
for n in bad:
    print(("MISSING  " if n in missing else "DIFFERS  ") + n)
print(f"{len(expected) - len(bad)} of {len(expected)} files match SHA256SUMS")
sys.exit(1 if bad else 0)
