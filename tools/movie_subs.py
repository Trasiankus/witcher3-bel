#!/usr/bin/env python3
r"""Pre-rendered video subtitles (.subs) for Witcher 3 Remastered.

Cinematic videos (recap, flashbacks rs_*, final boards fb_*, storybook st_*) don't take
their subtitles from en.w3strings: each video has a `.subs` file per language, packed
zlib-compressed in content\content0\bundles\movies.bundle, e.g.
    movies\cutscenes\gamestart\subs\recap_wip_en.subs
Decompressed it's UTF-16LE text with a BOM, CRLF line endings:
    1000                       <- header (time base: ms)
    1700, 7200, I see you...   <- start_ms, end_ms, text

    python movie_subs.py crowdin      # Crowdin\<Lang>\subtitles.json (EN source, RU/PL refs)
"""
import argparse, io, json, os, re, struct, sys, zlib

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE  = r"C:\Games\Steam\steamapps\common\The Witcher 3\content\content0\bundles\movies.bundle"
CROWDIN = os.path.join(ROOT, "Crowdin")
TOC_ENTRY = 0x130


def bundle_entries(path=BUNDLE):
    """-> [(name, offset, size, zsize)] from a POTATO70 bundle's table of contents."""
    with open(path, "rb") as f:
        head = f.read(0x20)
        if head[:8] != b"POTATO70":
            raise ValueError(f"{path}: not a POTATO70 bundle")
        toc = f.read(struct.unpack_from("<I", head, 16)[0])
    out = []
    for i in range(len(toc) // TOC_ENTRY):
        e = toc[i * TOC_ENTRY:(i + 1) * TOC_ENTRY]
        name = e[:0x100].split(b"\0")[0].decode("ascii")
        if not name:
            break
        lo, hi, size, zsize = struct.unpack_from("<IIII", e, 0x110)
        out.append((name, lo | (hi << 32), size, zsize))
    return out


def read_all_subs(path=BUNDLE):
    """-> {bundle path: decoded text} for every .subs file in the bundle."""
    out = {}
    with open(path, "rb") as f:
        for name, off, size, zsize in bundle_entries(path):
            if not name.endswith(".subs"):
                continue
            f.seek(off)
            raw = f.read(zsize)
            data = zlib.decompress(raw) if zsize != size else raw
            out[name] = data.decode("utf-16")          # BOM-aware
    return out


def parse(text):
    """-> (header, [(start_ms, end_ms, text)])"""
    lines = text.replace("\r\n", "\n").split("\n")
    header, cues = lines[0].strip(), []
    for line in lines[1:]:
        if not line.strip():
            continue
        start, end, body = line.split(",", 2)
        cues.append((int(start), int(end), body.strip()))
    return header, cues


def render(header, cues):
    """Back to the game's on-disk form: UTF-16LE + BOM, CRLF endings."""
    text = header + "\r\n" + "".join(f"{s}, {e}, {t}\r\n" for s, e, t in cues)
    return text.encode("utf-16")                       # Python writes the FFFE BOM


def subs_sets(all_subs):
    """-> {set name: {lang: bundle path}}, e.g. 'recap_wip': {'en': 'movies\\...\\recap_wip_en.subs'}"""
    sets = {}
    for path in all_subs:
        base = os.path.basename(path)[:-5]
        stem, lang = base.rsplit("_", 1)
        sets.setdefault(stem, {})[lang] = path
    return sets


def export_crowdin(dry_run=False):
    """One JSON per language, keyed `<set>_<NN>` by English cue order; RU/PL matched by
    start time (their cue splits occasionally differ - unmatched cues fall back to EN)."""
    all_subs = read_all_subs()
    sets = subs_sets(all_subs)
    out = {"English": {}, "Russian": {}, "Polish": {}}
    fallback = {"Russian": 0, "Polish": 0}
    for stem in sorted(sets, key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s)]):
        _, en = parse(all_subs[sets[stem]["en"]])
        refs = {}
        for lang, code in (("Russian", "ru"), ("Polish", "pl")):
            _, cues = parse(all_subs[sets[stem][code]]) if code in sets[stem] else ("", [])
            if len(cues) == len(en):                  # same split: align by position
                refs[lang] = {i: t for i, (_, _, t) in enumerate(cues)}
            else:                                     # different split: align by start time
                by_start = {s: t for s, _, t in cues}
                refs[lang] = {i: by_start[s] for i, (s, _, _) in enumerate(en) if s in by_start}
        for n, (_start, _end, text) in enumerate(en):
            key = f"{stem}_{n + 1:02d}"
            out["English"][key] = text
            for lang in ("Russian", "Polish"):
                if n in refs[lang]:
                    out[lang][key] = refs[lang][n]
                else:
                    out[lang][key] = text
                    fallback[lang] += 1
    for lang, d in out.items():
        print(f"  {lang:8s} subtitles.json: {len(d)} lines"
              + (f" ({fallback[lang]} EN fallback)" if fallback.get(lang) else ""))
        if not dry_run:
            p = os.path.join(CROWDIN, lang, "subtitles.json")
            with io.open(p, "w", encoding="utf-8-sig", newline="\n") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"  {len(sets)} subtitled videos")


def build_bundle(translations, content_dir, slot="ua", marker="", bundle=BUNDLE):
    """Pack Belarusian .subs into <content_dir>/blob0.bundle + metadata.store.

    translations: {"<set>_<NN>": text}. Each touched video gets a full .subs under the
    `slot` language's name, keeping the English timing; cues without a translation stay
    English. The slot must be one WITHOUT an embedded video subtitle track (ua, tr) -
    otherwise the game shows the embedded track and ignores .subs. `marker` prefixes
    cue 1 (in-game tests). `bundle` is the game's movies.bundle."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import w3bundle
    all_subs = read_all_subs(bundle)
    sets = subs_sets(all_subs)
    files, done = [], 0
    for stem in sorted(sets):
        header, en = parse(all_subs[sets[stem]["en"]])
        keys = [f"{stem}_{n + 1:02d}" for n in range(len(en))]
        if not any(k in translations for k in keys):
            continue
        cues = []
        for n, ((s, e, text), k) in enumerate(zip(en, keys)):
            t = translations.get(k, text)
            done += k in translations
            cues.append((s, e, (marker + t) if n == 0 and marker else t))
        path = sets[stem]["en"].replace("_en.subs", f"_{slot}.subs")
        files.append((path, render(header, cues)))
    os.makedirs(content_dir, exist_ok=True)
    w3bundle.write(content_dir, files)
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["crowdin", "build"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--translations", help="JSON {key: text} (build)")
    ap.add_argument("--out", help="mod content dir (build)")
    ap.add_argument("--marker", default="", help="prefix for cue 1, for in-game tests (build)")
    a = ap.parse_args()
    if a.cmd == "crowdin":
        export_crowdin(a.dry_run)
    else:
        tr = json.load(io.open(a.translations, encoding="utf-8-sig"))
        build_bundle(tr, a.out, marker=a.marker)
