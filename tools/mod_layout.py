#!/usr/bin/env python3
r"""Assemble the Belarusian mod for Witcher 3 Remastered (v5.00+), Ukrainian text slot.

Why the Ukrainian slot (tested in-game, Oct 2026):
  * Pre-rendered videos carry embedded subtitles for ~15 languages, and the game prefers
    those over the per-language .subs files. Ukrainian has no embedded track, so in the
    Ukrainian slot the game reads .subs - which a mod bundle can replace. Cinematic
    subtitles can only be Belarusian here (or in the Turkish slot).
  * The Ukrainian UI font has full Cyrillic incl. і and ў -> no font mod needed.
    (The English and Turkish slots both need modBelarusianFont.)
  * Ukrainian uppercase rules (unlike Turkish: "HİGHLİGHTS").

What gets written to <out_dir> (= mods\mod000_Belarusian\content):
  ua.w3strings          EVERY game string: Belarusian where translated, the game's English
                        everywhere else - so untranslated lines show English, never
                        Ukrainian. Language names: Ukrainian -> Беларуская, English -> Англійская.
  en.w3strings          one entry: Ukrainian -> "Belarusian" (Latin - the English font has
                        no Cyrillic), so players can find it from an English menu.
  blob0.bundle +        Belarusian video subtitles as <video>_ua.subs, English timing
  metadata.store        (only if any subtitle is translated).
Anything else in <out_dir> is removed, so stale files from older layouts can't linger.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import w3strings164 as W3
import movie_subs
import w3bundle

DEFAULT_GAME = r"C:\Games\Steam\steamapps\common\The Witcher 3"
SLOT = "ua"
UKRAINIAN_NAME = (1465127,)               # language-menu entry "Ukrainian"
ENGLISH_NAME = (1084957, 1263244)         # old + Remastered menu entries "English"


def game_paths(game_dir):
    c0 = os.path.join(game_dir, "content", "content0")
    paths = {"en": os.path.join(c0, "en.w3strings"),
             "movies": os.path.join(c0, "bundles", "movies.bundle")}
    for p in paths.values():
        if not os.path.isfile(p):
            raise SystemExit(f"game file not found: {p}\n(pass the Witcher 3 Remastered install dir)")
    return paths


def build(out_dir, be_strings, game_dir=DEFAULT_GAME, subtitles=None):
    """be_strings: {id: text} (already cleaned); subtitles: {"<video>_<NN>": text} or None."""
    paths = game_paths(game_dir)
    os.makedirs(out_dir, exist_ok=True)
    en = W3.read(paths["en"])
    keyof = {}
    for h, sid in en["keys"]:
        keyof.setdefault(sid, h)

    table = dict(en["strings"])
    translated = sum(1 for i in be_strings if i in table)
    table.update(be_strings)
    for i in UKRAINIAN_NAME:
        table[i] = "Беларуская"
    for i in ENGLISH_NAME:
        table[i] = "Англійская"
    W3.write(os.path.join(out_dir, f"{SLOT}.w3strings"), list(table.items()), SLOT, en["keys"])
    W3.write(os.path.join(out_dir, "en.w3strings"), [(i, "Belarusian") for i in UKRAINIAN_NAME],
             "en", [(keyof[i], i) for i in UKRAINIAN_NAME if i in keyof])
    produced = {f"{SLOT}.w3strings", "en.w3strings"}

    subs_files = []
    if subtitles:
        subs_files = movie_subs.build_bundle(subtitles, out_dir, slot=SLOT, bundle=paths["movies"])
        produced |= {"blob0.bundle", "metadata.store"}
    for fn in os.listdir(out_dir):                 # drop leftovers from older layouts
        if fn not in produced:
            p = os.path.join(out_dir, fn)
            if os.path.isfile(p):
                os.remove(p)
    print(f"  {SLOT}.w3strings: {len(table)} strings ({translated} Belarusian, rest English)"
          f" | video subtitles: {sum(1 for k in (subtitles or {}))} lines in {len(subs_files)} videos")
    return sorted(produced)
