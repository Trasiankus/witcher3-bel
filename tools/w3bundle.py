#!/usr/bin/env python3
r"""Write a Witcher 3 mod bundle (blob0.bundle) + its metadata.store.

The game only picks up loose resources from a mod when they're packed in a bundle that
metadata.store indexes (loose files in mods\X\content\ or content\content0\ are ignored -
tested). WolvenKit can read metadata.store but its writer is an empty stub, so this
generates both from scratch, modelled field-for-field on the font mod's 352-byte store,
which the Remastered loads fine.

Bundle (classic POTATO70 layout - the Remastered's own bundles use a newer 0x130-byte
TOC entry with 64-bit offsets, but still loads this one):
    0x00 "POTATO70" | u32 bundle size (4096-aligned) | u32 0 | u32 TOC size | 12 magic bytes
    0x20 TOC, 0x140 per file: name[0x100] hash[16] u32 0 | u32 size | u32 zsize
         u32 offset | u32 date | u32 time | 16x00 | u32 crc32(plain) | u32 compression
    data: each file at a 4096-aligned offset

metadata.store ("\x03VTM", version 6): string table, then fileInfo / fileEntryInfo /
bundleInfo tables (index 0 is a null record), dir + file init trees, and a list of
(FNV-1a-64 of the lowercase path, file index) sorted by hash.
"""
import io, os, struct, zlib

ALIGN = 4096
COMP_NONE, COMP_ZLIB = 0, 1
BUNDLE_MAGIC_TAIL = bytes([0x03, 0x00, 0x01, 0x00, 0x00, 0x13, 0x13, 0x13, 0x13, 0x13, 0x13, 0x13])
TOC_ENTRY = 0x140


def fnv1a64(data):
    h = 0xcbf29ce484222325
    for b in data:
        h = ((h ^ b) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def _vlq(value):
    """WolvenKit/REDengine VLQ: 6 data bits + continue flag in byte 0, then 7 bits each."""
    out = bytearray()
    b = value & 0x3F
    value >>= 6
    if value:
        b |= 0x40
    out.append(b)
    while value:
        b = value & 0x7F
        value >>= 7
        if value:
            b |= 0x80
        out.append(b)
    return bytes(out)


def _align(n):
    return (n + ALIGN - 1) // ALIGN * ALIGN


def write(content_dir, files, bundle_name="blob0.bundle", compression=COMP_ZLIB):
    """files: [(depot path with backslashes, bytes)]. Writes <content_dir>/<bundle_name>
    and <content_dir>/metadata.store."""
    files = [(p.lower(), d) for p, d in files]
    n = len(files)
    toc_size = TOC_ENTRY * n
    data_start = 0x20 + toc_size

    packed, cursor = [], _align(data_start)
    for path, plain in files:
        stored = zlib.compress(plain, 9) if compression == COMP_ZLIB else plain
        packed.append((path, plain, stored, cursor))
        cursor = _align(cursor + len(stored))
    bundle_size = cursor                            # aligned end, as the header records it

    # ---- bundle ----
    out = io.BytesIO()
    out.write(b"POTATO70" + struct.pack("<III", bundle_size, 0, toc_size) + BUNDLE_MAGIC_TAIL)
    for path, plain, stored, off in packed:
        name = path.encode("ascii")
        if len(name) >= 0x100:
            raise ValueError(f"path too long for a bundle: {path}")
        out.write(name.ljust(0x100, b"\0"))
        out.write(b"\0" * 16)                                       # hash: unused (font mod: 0)
        out.write(struct.pack("<IIIIII", 0, len(plain), len(stored), off, 0, 0))
        out.write(b"\0" * 16)
        out.write(struct.pack("<II", zlib.crc32(plain), compression))
    for path, plain, stored, off in packed:
        out.write(b"\0" * (off - out.tell()))
        out.write(stored)
    with open(os.path.join(content_dir, bundle_name), "wb") as f:
        f.write(out.getvalue())                     # no trailing pad, like the font mod

    entries = [(path, len(plain), len(stored), off, compression) for path, plain, stored, off in packed]
    with open(os.path.join(content_dir, "metadata.store"), "wb") as f:
        f.write(build_store(entries, bundle_name, bundle_size, toc_size))
    return bundle_size


def build_store(entries, bundle_name, bundle_size, toc_size):
    """entries: [(lowercase depot path, plain size, stored size, offset in bundle, compression)]"""
    n = len(entries)
    strings = bytearray(b"\0")                      # offset 0 = ""
    offsets = {}

    def sref(s):
        if s not in offsets:
            offsets[s] = len(strings)
            strings.extend(s.encode("ascii") + b"\0")
        return offsets[s]

    bundle_ref = sref(bundle_name)
    path_refs = [sref(p) for p, *_ in entries]
    root_ref = len(strings)                         # the root dir gets its own "" entry
    strings.extend(b"\0")

    dirs = {"": 0}                                  # dir path -> dir index; 0 = root
    dir_list = [(root_ref, 0)]
    file_init = []
    for i, (path, *_rest) in enumerate(entries, 1):
        parts = path.split("\\")
        parent, acc = 0, ""
        for comp in parts[:-1]:
            acc = f"{acc}\\{comp}" if acc else comp
            if acc not in dirs:
                dirs[acc] = len(dir_list)
                dir_list.append((sref(comp), parent))
            parent = dirs[acc]
        file_init.append((i, parent, sref(parts[-1])))

    m = io.BytesIO()
    m.write(b"\x03VTM" + struct.pack("<iii", 6,
                                     max(e[2] for e in entries),           # max stored size
                                     max(e[1] for e in entries)))          # max plain size
    m.write(_vlq(len(strings)) + bytes(strings))

    m.write(_vlq(n + 1) + struct.pack("<8I", *[0] * 8))                       # fileInfo
    for i, (path, plain, stored, off, comp) in enumerate(entries, 1):
        m.write(struct.pack("<8I", path_refs[i - 1], 0, stored, plain, i, comp, 0, 0))
    m.write(_vlq(n + 1) + struct.pack("<5I", *[0] * 5))                       # fileEntryInfo
    for i, (path, plain, stored, off, comp) in enumerate(entries, 1):
        m.write(struct.pack("<5I", i, 1, off, stored, 0))
    data_block_offset = 0x20 + toc_size                                      # bundleInfo
    m.write(_vlq(2) + struct.pack("<6I", *[0] * 6))
    m.write(struct.pack("<6I", bundle_ref, 1, n, bundle_size - data_block_offset, data_block_offset, 0))
    m.write(b"\x80")                # buffers: empty - stored as a sign-flagged 0, like the engine
    m.write(_vlq(len(dir_list)) + b"".join(struct.pack("<ii", a, b) for a, b in dir_list))
    m.write(_vlq(len(file_init)) + b"".join(struct.pack("<iii", *x) for x in file_init))
    hashes = sorted((fnv1a64(p.encode("ascii")), i) for i, (p, *_r) in enumerate(entries, 1))
    m.write(_vlq(len(hashes)) + b"".join(struct.pack("<Qq", h, i) for h, i in hashes))
    return m.getvalue()
