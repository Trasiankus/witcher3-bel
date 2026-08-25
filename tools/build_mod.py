#!/usr/bin/env python3
"""Build the Belarusian .w3strings mod from data/*.json.

  python tools/build_mod.py --encoder path/to/w3strings.exe

Reads the `bel` field from every data file (translated-only), merges them in the
game's load order, applies tools/overrides.json, neutralises stray newlines, and
encodes a single en.w3strings into mod/mods/mod000_Belarusian/content/.

Data files are named after the game archives they came from:
  data/content0..12.json        base game + patches
  data/dlc/{dlcN,ep1,bob}.json  DLCs and expansions
Later files win on duplicate ids, mirroring how the game applies them.

w3strings encoder v0.4.1: https://www.nexusmods.com/witcher3/mods/1055
"""
import argparse, io, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
OUT_DIR = os.path.join(REPO, "mod", "mods", "mod000_Belarusian", "content")
CSV = os.path.join(HERE, "be.csv")


def load_order(path):
    """Game load order: base content -> patches -> DLCs -> ep1 -> bob (last-wins)."""
    stem = os.path.basename(path)[:-5]
    if stem.startswith("content"): cat = 0
    elif stem.startswith("dlc"):   cat = 1
    elif stem == "ep1":            cat = 2
    else:                          cat = 3
    m = re.search(r"(\d+)$", stem)
    return (cat, int(m.group(1)) if m else 0, stem)


def data_files():
    out = []
    for dirpath, _, filenames in os.walk(DATA):
        out += [os.path.join(dirpath, fn) for fn in filenames if fn.endswith(".json")]
    if not out:
        sys.exit(f"no data files under {DATA}")
    return sorted(out, key=load_order)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", default=shutil.which("w3strings") or "w3strings.exe",
                    help="path to the w3strings encoder executable")
    args = ap.parse_args()

    overrides = {}
    ovr_path = os.path.join(HERE, "overrides.json")
    if os.path.isfile(ovr_path):
        overrides = json.load(io.open(ovr_path, encoding="utf-8-sig"))

    merged, order = {}, []
    for path in data_files():
        d = json.load(io.open(path, encoding="utf-8-sig"))
        for k, rec in d.items():
            if k not in merged:
                order.append(k)
            merged[k] = rec
        print(f"  {os.path.relpath(path, DATA)}: {len(d)}")

    rows, skip_empty, fixed_nl = [], 0, 0
    for k in order:
        bel = overrides.get(k, merged[k].get("bel", ""))
        if not bel or not bel.strip():      # data is translated-only; just guard empties
            skip_empty += 1
            continue
        if "\n" in bel or "\r" in bel:
            bel = re.sub(r"  +", " ", bel.replace("\r\n", " ").replace("\n", " ").replace("\r", " "))
            fixed_nl += 1
        sid, keyhex = k.split("_", 1)
        rows.append((int(sid), f"{sid}|{keyhex}||{bel}"))

    rows.sort(key=lambda r: r[0])
    with io.open(CSV, "w", encoding="utf-8", newline="\n") as f:   # UTF-8, NO BOM
        f.write(";meta[language=en]\n; id|key(hex)|key(str)|text\n")
        for _, line in rows:
            f.write(line + "\n")
    print(f"rows: {len(rows)}  skipped(empty): {skip_empty}  nl-fixed: {fixed_nl}")

    if not (os.path.isfile(args.encoder) or shutil.which(args.encoder)):
        print(f"\nCSV written to {CSV}\nEncoder not found ({args.encoder}); "
              f"run it manually with --force-ignore-id-space-check.", file=sys.stderr)
        return
    subprocess.run([args.encoder, "-e", CSV,
                    "--force-ignore-id-space-check-i-know-what-i-am-doing"], check=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.move(CSV + ".w3strings", os.path.join(OUT_DIR, "en.w3strings"))
    for junk in (CSV, CSV + ".w3strings.ws"):
        if os.path.isfile(junk):
            os.remove(junk)
    print("built:", os.path.join(OUT_DIR, "en.w3strings"))


if __name__ == "__main__":
    main()
