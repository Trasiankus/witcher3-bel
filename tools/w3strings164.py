#!/usr/bin/env python3
r"""Read/write Witcher 3 .w3strings, including the Remastered (v5.00) format.

Remastered bumped the container to **version 164** and switched the string payload from
UTF-16 to **UTF-8** (offsets/lengths are now in bytes instead of UTF-16 units). The old
w3strings encoder v0.4.1 only handles 162/163, and a v162 file still *loads* in the
Remastered but every character is misread - that's the garbage the mod showed.

Ported from the MIT-licensed Witcher3StringEditor 2.0 branch
(https://github.com/0x7A2C9E5D/Witcher3StringEditor, Witcher3StringEditor.W3Strings/).

Container layout (little-endian):
    "RTSW" | u32 version | u16 key1
    count1 (bit6 varint) | count1 x {u32 id^magic, u32 offset, u32 length}   string table
    count2 (bit6 varint) | count2 x {u32 keyhash, u32 id^magic}               key mappings
    count3 (bit6 varint) | count3 x unit bytes                                string buffer
    [trailer] | u16 key2

    python w3strings164.py decode in.w3strings out.csv
    python w3strings164.py encode in.csv out.w3strings [--lang ru] [--version 164]
"""
import argparse, io, struct, sys

FIRST_UTF8_VERSION = 164

# code -> (key, magic); key = (key1 << 16) | key2 identifies the language in the header
LANGUAGES = {
    "ar": (0x00000000, 0x00000000), "br": (0x00000000, 0x00000000),
    "cn": (0x00000000, 0x00000000), "cz": (0x24987354, 0x21793217),
    "de": (0x75886138, 0x42791159), "en": (0x43975139, 0x79321793),
    "es": (0x18796651, 0x42387566), "esmx": (0x00000000, 0x00000000),
    "fr": (0x23863176, 0x75921975), "hu": (0x42378932, 0x67823218),
    "it": (0x45931894, 0x12375973), "jp": (0x54834893, 0x59825646),
    "kr": (0x00000000, 0x00000000), "pl": (0x83496237, 0x73946816),
    "ru": (0x63481486, 0x42386347), "zh": (0x18632176, 0x16875467),
    "tr": (0x00000000, 0x00000000), "ua": (0x00000000, 0x00000000),
}


def unit_size(version):
    return 1 if version >= FIRST_UTF8_VERSION else 2


# ---- bit6 variable-length counts ---------------------------------------------------------

def read_count(data, p):
    value, shift, index = 0, 0, 1
    while True:
        x = data[p]; p += 1
        if x > 127:
            mask, step = 0x7F, 7
        elif x > 63 and index == 1:
            mask, step = 0x3F, 6
        else:
            mask, step = 0xFF, 6
        value |= (x & mask) << shift
        shift += step
        if x < 64 or (index >= 3 and x < 128):
            break
        index += 1
    return value, p


def _build_count(value, groups, term_bits):
    if groups == 1:
        return bytes([value]) if value < 64 else None
    if value >> (6 + 7 * (groups - 2) + term_bits):
        return None
    out, v = [], value
    out.append(v & 0x3F); v >>= 6
    for _ in range(groups - 2):
        out.append(v & 0x7F); v >>= 7
    out.append(v & ((1 << term_bits) - 1)); v >>= term_bits
    if v:
        return None
    out[0] |= 0x40
    for i in range(1, groups - 1):
        out[i] |= 0x80
    return None if out[-1] & 0x40 else bytes(out)


def write_count(value):
    for groups in range(1, 7):
        for term_bits in (6, 7, 8):
            cand = _build_count(value, groups, term_bits)
            if cand is not None and read_count(cand, 0)[0] == value:
                return cand
    raise ValueError(f"cannot encode count {value}")


# ---- payload obfuscation -----------------------------------------------------------------

def _rotl16(x):
    return ((x << 1) | (x >> 15)) & 0xFFFF


def xor_payload(buf, length, magic, unit):
    """In-place, symmetric (same call encodes and decodes). `length` is in units."""
    key = (magic >> 8) & 0xFFFF
    if unit == 1:
        for i in range(length):
            buf[i] ^= ((length + 1) * key) & 0xFF
            key = _rotl16(key)
    else:
        for i in range(length):
            ck = ((length + 1) * key) & 0xFFFF
            buf[2 * i] ^= ck & 0xFF
            buf[2 * i + 1] ^= ck >> 8
            key = _rotl16(key)


def key_hash(key_str):
    """Hash of a string key (e.g. 'panel_Mods'), as stored in the key-mapping block."""
    h = 0
    data = key_str.lower().encode("utf-16-le")
    for i in range(0, len(data), 2):
        h = (h * 31 + (data[i] | (data[i + 1] << 8))) & 0xFFFFFFFF
    return h


# ---- read / write ------------------------------------------------------------------------

def read(path):
    """-> dict(version, lang, key1, key2, magic, strings=[(id, text)], keys=[(hash, id)],
    trailer=bytes)"""
    data = open(path, "rb").read()
    if data[:4] != b"RTSW":
        raise ValueError(f"{path}: bad magic {data[:4]!r}")
    version = struct.unpack_from("<I", data, 4)[0]
    key1 = struct.unpack_from("<H", data, 8)[0]
    key2 = struct.unpack_from("<H", data, len(data) - 2)[0]
    key = (key1 << 16) | key2
    lang = next((c for c, (k, _) in LANGUAGES.items() if k == key and k), None)
    if lang is None:  # fall back to key1 alone, if it is unambiguous
        hits = [c for c, (k, _) in LANGUAGES.items() if k and (k >> 16) == key1]
        lang = hits[0] if len(hits) == 1 else None
    magic = LANGUAGES[lang][1] if lang else 0
    unit = unit_size(version)

    count1, p = read_count(data, 10)
    b1 = p
    count2, p = read_count(data, b1 + count1 * 12)
    b2 = p
    count3, p = read_count(data, b2 + count2 * 8)
    buf_start = p
    buf_end = buf_start + count3 * unit
    if buf_end > len(data):
        raise ValueError(f"{path}: string buffer overruns file")
    trailer = data[buf_end:len(data) - 2]

    strings = []
    for i in range(count1):
        sid, off, length = struct.unpack_from("<III", data, b1 + i * 12)
        a = buf_start + off * unit
        raw = bytearray(data[a:a + length * unit])
        xor_payload(raw, length, magic, unit)
        text = raw.decode("utf-8" if unit == 1 else "utf-16-le", errors="replace")
        strings.append((sid ^ magic, text))
    keys = []
    for i in range(count2):
        h, sid = struct.unpack_from("<II", data, b2 + i * 8)
        keys.append((h, sid ^ magic))
    return dict(version=version, lang=lang, key1=key1, key2=key2, magic=magic,
                strings=strings, keys=keys, trailer=trailer)


def write(path, strings, lang, keys=(), version=FIRST_UTF8_VERSION, trailer=b""):
    """strings: [(id, text)] in any order; keys: [(hash, id)]."""
    # Languages added later (tr, ua, ar, ...) ship as cleartext: key 0, magic 0 - valid.
    key, magic = LANGUAGES[lang]
    key1, key2 = key >> 16, key & 0xFFFF
    unit = unit_size(version)
    enc = "utf-8" if unit == 1 else "utf-16-le"

    # The game binary-searches both tables, so they MUST be sorted: strings by the
    # *obfuscated* id (id ^ magic, which differs per language - an EN-ordered table
    # written under the RU key is silently ignored), key mappings by hash.
    strings = sorted(strings, key=lambda s: (s[0] ^ magic) & 0xFFFFFFFF)
    keys = sorted(keys, key=lambda k: (k[0], (k[1] ^ magic) & 0xFFFFFFFF))

    table, buf, cursor = [], bytearray(), 0
    for sid, text in strings:
        raw = bytearray(text.encode(enc))
        length = len(raw) // unit
        xor_payload(raw, length, magic, unit)
        table.append((sid, cursor, length))
        buf += raw + b"\x00" * unit          # NUL terminator, one unit wide
        cursor += length + 1

    out = io.BytesIO()
    out.write(b"RTSW")
    out.write(struct.pack("<IH", version, key1))
    out.write(write_count(len(table)))
    for sid, off, length in table:
        out.write(struct.pack("<III", sid ^ magic, off, length))
    out.write(write_count(len(keys)))
    for h, sid in keys:
        out.write(struct.pack("<II", h, sid ^ magic))
    out.write(write_count(len(buf) // unit))
    out.write(buf)
    out.write(trailer)
    out.write(struct.pack("<H", key2))
    with open(path, "wb") as f:
        f.write(out.getvalue())


# ---- CSV (same format as w3strings encoder v0.4.1) ---------------------------------------

def to_csv(path, parsed):
    ids_to_key = {}
    for h, sid in parsed["keys"]:
        ids_to_key.setdefault(sid, h)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f";meta[language={parsed['lang'] or 'unknown'}]\n; id|key(hex)|key(str)|text\n")
        for sid, text in parsed["strings"]:
            f.write(f"{sid}|{ids_to_key.get(sid, 0):08x}||{text}\n")


def from_csv(path):
    strings, keys = [], []
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.rstrip("\r\n")
        if not line or line.lstrip().startswith(";"):
            continue
        sid, keyhex, _keystr, text = line.split("|", 3)
        sid = int(sid)
        strings.append((sid, text))
        if keyhex.strip() and int(keyhex, 16):
            keys.append((int(keyhex, 16), sid))
    return strings, keys


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode"); d.add_argument("src"); d.add_argument("dst")
    e = sub.add_parser("encode"); e.add_argument("src"); e.add_argument("dst")
    e.add_argument("--lang", default="en"); e.add_argument("--version", type=int, default=FIRST_UTF8_VERSION)
    a = ap.parse_args()
    if a.cmd == "decode":
        p = read(a.src)
        to_csv(a.dst, p)
        print(f"v{p['version']} lang={p['lang']} strings={len(p['strings'])} "
              f"keys={len(p['keys'])} trailer={len(p['trailer'])}B -> {a.dst}")
    else:
        strings, keys = from_csv(a.src)
        write(a.dst, strings, a.lang, keys, a.version)
        print(f"v{a.version} lang={a.lang} strings={len(strings)} keys={len(keys)} -> {a.dst}")


if __name__ == "__main__":
    sys.exit(main())
