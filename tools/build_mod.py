#!/usr/bin/env python3
"""Build the Belarusian mod for The Witcher 3 Remastered (v5.00+) from data/*.json.

  python tools/build_mod.py --game "C:/Games/Steam/steamapps/common/The Witcher 3"

The game install is needed for two things the repo doesn't ship: the English text used
as fallback for untranslated lines (content/content0/en.w3strings) and the timing of the
video subtitles (content/content0/bundles/movies.bundle).

Reads the `bel` field from every data file (translated-only), merges them in the game's
load order, applies tools/overrides.json, neutralises stray newlines, and writes the mod
into mod/mods/mod000_Belarusian/content/ via tools/mod_layout.py:

  ua.w3strings     every game string - Belarusian where translated, English elsewhere
                   (the mod lives in the Ukrainian text slot; see mod_layout.py for why)
  en.w3strings     the language-menu entry "Belarusian"
  blob0.bundle,    Belarusian video subtitles (data/subtitles.json)
  metadata.store

Data files are named after the game archives they came from:
  data/content0..13.json        base game, patches, Remastered additions (content13)
  data/dlc/{dlcN,ep1,bob}.json  DLCs and expansions
  data/subtitles.json           pre-rendered video subtitles
Later files win on duplicate ids, mirroring how the game applies them.
"""
import argparse, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
OUT_DIR = os.path.join(REPO, "mod", "mods", "mod000_Belarusian", "content")
sys.path.insert(0, HERE)
import mod_layout


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
        out += [os.path.join(dirpath, fn) for fn in filenames
                if fn.endswith(".json") and fn != "subtitles.json"]
    if not out:
        sys.exit(f"no data files under {DATA}")
    return sorted(out, key=load_order)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=mod_layout.DEFAULT_GAME,
                    help="The Witcher 3 Remastered install dir")
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

    be, skip_empty, fixed_nl = {}, 0, 0
    for k in order:
        bel = overrides.get(k, merged[k].get("bel", ""))
        if not bel or not bel.strip():      # data is translated-only; just guard empties
            skip_empty += 1
            continue
        if "\n" in bel or "\r" in bel:
            bel = re.sub(r"  +", " ", bel.replace("\r\n", " ").replace("\n", " ").replace("\r", " "))
            fixed_nl += 1
        be[int(k.split("_", 1)[0])] = bel
    print(f"rows: {len(be)}  skipped(empty): {skip_empty}  nl-fixed: {fixed_nl}")

    subtitles = {}
    subs_path = os.path.join(DATA, "subtitles.json")
    if os.path.isfile(subs_path):
        subtitles = {k: rec["bel"] for k, rec in json.load(io.open(subs_path, encoding="utf-8-sig")).items()
                     if rec.get("bel", "").strip()}

    files = mod_layout.build(OUT_DIR, be, args.game, subtitles)
    print("built:", OUT_DIR, files)


if __name__ == "__main__":
    main()
