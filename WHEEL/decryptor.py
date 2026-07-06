#!/usr/bin/env python3
"""
Wheel of Fortune - DB File Decryptor/Editor
opencode -s ses_0c87a7528ffeMKGqXGNsr3yLFE
Category DB files come in two formats:

  OLD "slot" format (game uses divisor 0x5DD):
    384256 bytes per entry = 1501 × 256 (first 256 = data, rest = zeros)
    Total = N × 384256 bytes

  NEW "packed" format (game patched to use divisor 1):
    256 bytes per entry (just the data header)
    Total = N × 256 bytes

Both formats store each entry as a Pascal string XOR'd with 0x41:
  byte 0: string length (NOT XOR'd)
  bytes 1..length: characters XOR'd with 0x41 (Hebrew, windows-1255)

HSCORE.DB is a separate format (260-byte records, plain binary, no XOR).

Usage:
  python3 decryptor.py list                       # list all categories
  python3 decryptor.py dump <file> [<count>]      # dump entries
  python3 decryptor.py set <file> <idx> <text>    # modify entry
  python3 decryptor.py add <file> <text>          # add to first empty slot
  python3 decryptor.py create <file> <num>         # create packed DB (use --old for slot format)
  python3 decryptor.py pack <src> <dst>           # convert old slot → packed
  python3 decryptor.py unpack <src> <dst>         # convert packed → old slot
"""

import os
import sys

RECORD_HEADER_SIZE = 256
SLOT_MULTIPLIER = 0x5DD
SLOT_SIZE = SLOT_MULTIPLIER * RECORD_HEADER_SIZE  # 384256
XOR_KEY = 0x41

HSCORE_RECORD_SIZE = 260
HSCORE_SLOTS = 11
HSCORE_SIZE = HSCORE_SLOTS * HSCORE_RECORD_SIZE   # 2860

DB_CATEGORIES = {
    "ANIMAL.DB":    (100, "Animals"),
    "BANDS.DB":     (32,  "Bands"),
    "CHARACTR.DB":  (63,  "Characters"),
    "CITY.DB":      (83,  "Cities"),
    "COUNTRY.DB":   (71,  "Countries"),
    "FAME.DB":      (209, "Famous People"),
    "GENERAL.DB":   (104, "General Knowledge"),
    "ITEMS.DB":     (100, "Items"),
    "MOVIES.DB":    (267, "Movies"),
    "PHRASE.DB":    (107, "Phrases"),
    "SONGS.DB":     (101, "Songs"),
    "TV.DB":        (86,  "TV Shows"),
}


#
# Core encryption / decryption
#

def encrypt_pascal_string(text: str) -> bytes:
    encoded = text.encode('windows-1255', errors='replace')
    if len(encoded) > 255:
        encoded = encoded[:255]
    encrypted = bytes([b ^ XOR_KEY for b in encoded])
    return bytes([len(encoded)]) + encrypted


def decrypt_pascal_string(raw_buffer: bytes) -> str:
    if not raw_buffer:
        return ""
    string_len = raw_buffer[0]
    if string_len == 0 or string_len > 255:
        return ""
    decrypted = bytes([b ^ XOR_KEY for b in raw_buffer[1:1 + string_len]])
    try:
        return decrypted.decode('windows-1255', errors='replace').strip()
    except Exception:
        return decrypted.decode('ascii', errors='replace').strip()


def write_256_buf(text: str) -> bytes:
    enc = encrypt_pascal_string(text)
    return enc + b'\x00' * (RECORD_HEADER_SIZE - len(enc))


#
# Format detection
#

def detect_type(file_path: str):
    size = os.path.getsize(file_path)
    if size == HSCORE_SIZE:
        return "hscore"
    if size % SLOT_SIZE == 0:
        return "slot"
    if size > 0 and size % RECORD_HEADER_SIZE == 0:
        return "packed"
    return "unknown"


def num_entries(file_path: str):
    size = os.path.getsize(file_path)
    dtype = detect_type(file_path)
    if dtype == "slot":
        return size // SLOT_SIZE
    if dtype == "packed":
        return size // RECORD_HEADER_SIZE
    if dtype == "hscore":
        return HSCORE_SLOTS
    return 0


#
# Readers
#

def read_slot_based(file_path: str):
    size = os.path.getsize(file_path)
    total = size // SLOT_SIZE
    entries = []
    with open(file_path, "rb") as f:
        for i in range(total):
            f.seek(i * SLOT_SIZE)
            buf = f.read(RECORD_HEADER_SIZE)
            entries.append(decrypt_pascal_string(buf))
    return entries


def read_packed(file_path: str):
    size = os.path.getsize(file_path)
    total = size // RECORD_HEADER_SIZE
    entries = []
    with open(file_path, "rb") as f:
        for _ in range(total):
            buf = f.read(RECORD_HEADER_SIZE)
            entries.append(decrypt_pascal_string(buf))
    return entries


def read_entries(file_path: str):
    dtype = detect_type(file_path)
    if dtype == "slot":
        return read_slot_based(file_path)
    if dtype == "packed":
        return read_packed(file_path)
    return []


#
# Writers
#

def write_slot_based(file_path: str, entries: list):
    size = os.path.getsize(file_path)
    total = size // SLOT_SIZE
    if len(entries) > total:
        entries = entries[:total]
    with open(file_path, "r+b") as f:
        for i, text in enumerate(entries):
            buf = write_256_buf(text)
            f.seek(i * SLOT_SIZE)
            f.write(buf)


def write_packed(file_path: str, entries: list):
    with open(file_path, "wb") as f:
        for text in entries:
            f.write(write_256_buf(text))


def write_entries(file_path: str, entries: list):
    dtype = detect_type(file_path)
    if dtype == "slot":
        write_slot_based(file_path, entries)
    elif dtype == "packed":
        write_packed(file_path, entries)
    else:
        return


#
# Commands
#

def list_categories():
    print("DB Categories:")
    print("=" * 60)
    for fname, (count, cat) in sorted(DB_CATEGORIES.items()):
        path = f'/mnt/d/games/WheelOfFortune/WHEEL/{fname}'
        if os.path.exists(path):
            size = os.path.getsize(path)
            dtype = detect_type(path)
            n = num_entries(path)
            if dtype == "packed":
                info = f"{n} entries (packed, {size} bytes)"
            else:
                info = f"{n} entries ({size} bytes, {size//SLOT_SIZE} slots)"
        else:
            info = "not found"
        print(f"  {fname:15s}  {cat:20s}  {info}")
    print()
    h_path = '/mnt/d/games/WheelOfFortune/WHEEL/HSCORE.DB'
    h_size = os.path.getsize(h_path) if os.path.exists(h_path) else 0
    print(f"  HSCORE.DB          High Scores          {HSCORE_SLOTS} entries ({h_size} bytes)")


def dump(file_path: str, show_all=True):
    if not os.path.exists(file_path):
        print(f"[-] File not found: {file_path}")
        return

    size = os.path.getsize(file_path)
    fname = os.path.basename(file_path).upper()
    dtype = detect_type(file_path)
    n = num_entries(file_path)

    cat = DB_CATEGORIES.get(fname, None)
    cat_info = f" — {cat[1]}" if cat else ""
    expected = cat[0] if cat else None

    if dtype == "hscore":
        print(f"[+] {fname}{cat_info} ({size} bytes, {HSCORE_SLOTS} high score slots)")
        print(f"[+] Structure: {HSCORE_RECORD_SIZE}-byte records, plain binary (no XOR)")
        print("=" * 60)
        print("   (No scores recorded — game was never played)")
        print("=" * 60)
        return

    entries = read_entries(file_path)
    match_str = "✓" if (expected and n == expected) else "?"

    if dtype == "slot":
        print(f"[+] {fname}{cat_info} ({n} entries, {n * SLOT_SIZE} bytes, {n} slots) {match_str}")
        print(f"[+] Structure: old slot format ({SLOT_SIZE} bytes/slot), XOR 0x41")
    elif dtype == "packed":
        print(f"[+] {fname}{cat_info} ({n} entries, {n * RECORD_HEADER_SIZE} bytes) {match_str}")
        print(f"[+] Structure: packed format ({RECORD_HEADER_SIZE} bytes/entry), XOR 0x41")
    else:
        print(f"[-] Unknown DB format: {fname} ({size} bytes)")
        return

    print("=" * 60)
    for i, text in enumerate(entries):
        if show_all or text:
            print(f"  {i + 1:3d}. {text}")
    print("=" * 60)


def dump_first_n(file_path: str, count: int):
    entries = read_entries(file_path)
    print(f"=== {os.path.basename(file_path)} (first {count}) ===")
    for i, text in enumerate(entries[:count]):
        print(f"  {i + 1:3d}. {text}")


def set_entry(file_path: str, index: int, text: str):
    dtype = detect_type(file_path)
    n = num_entries(file_path)
    if index < 0 or index >= n:
        print(f"[-] Index {index} out of range (0..{n - 1})")
        return
    buf = write_256_buf(text)
    with open(file_path, "r+b") as f:
        if dtype == "slot":
            f.seek(index * SLOT_SIZE)
        elif dtype == "packed":
            f.seek(index * RECORD_HEADER_SIZE)
        else:
            print(f"[-] Unsupported format: {dtype}")
            return
        f.write(buf)
    print(f"[+] Entry {index} set to: {text}")


def add_entry(file_path: str, text: str):
    entries = read_entries(file_path)
    for i, entry in enumerate(entries):
        if not entry:
            set_entry(file_path, i, text)
            return
    print(f"[-] All slots are full ({len(entries)} entries).")


def create_db(file_path: str, num_slots: int, old_format=False):
    if old_format:
        with open(file_path, "wb") as f:
            slot = b'\x00' * SLOT_SIZE
            for _ in range(num_slots):
                f.write(slot)
        print(f"[+] Created {file_path} with {num_slots} slots ({num_slots * SLOT_SIZE} bytes, old format)")
    else:
        write_packed(file_path, [""] * num_slots)
        print(f"[+] Created {file_path} with {num_slots} entries ({num_slots * RECORD_HEADER_SIZE} bytes, packed)")


def pack_file(src_path: str, dst_path: str):
    entries = read_slot_based(src_path)
    write_packed(dst_path, entries)
    n = len(entries)
    old_size = os.path.getsize(src_path)
    new_size = os.path.getsize(dst_path)
    print(f"[+] Converted: {n} entries, {old_size} → {new_size} bytes ({(1 - new_size / old_size) * 100:.1f}% saved)")


def unpack_file(src_path: str, dst_path: str):
    entries = read_packed(src_path)
    n = len(entries)
    with open(dst_path, "wb") as f:
        slot = b'\x00' * SLOT_SIZE
        for _ in range(n):
            f.write(slot)
    write_slot_based(dst_path, entries)
    new_size = os.path.getsize(dst_path)
    print(f"[+] Unpacked: {n} entries → {new_size} bytes (old slot format)")


#
# CLI
#

def usage():
    print("Usage:")
    print("  python3 decryptor.py list                        # list all categories")
    print("  python3 decryptor.py dump <file> [<count>]       # dump entries")
    print("  python3 decryptor.py set <file> <idx> <text>     # modify entry")
    print("  python3 decryptor.py add <file> <text>           # add to first empty slot")
    print("  python3 decryptor.py create <file> <num> [--old] # create DB (packed by default)")
    print("  python3 decryptor.py pack <src> <dst>            # old slot → packed")
    print("  python3 decryptor.py unpack <src> <dst>          # packed → old slot")
    print()
    print("Examples:")
    print("  python3 decryptor.py dump CITY.DB")
    print("  python3 decryptor.py dump ANIMAL.DB 5")
    print("  python3 decryptor.py set CITY.DB 1 לונדון")
    print("  python3 decryptor.py add CITY.DB תל אביב")
    print("  python3 decryptor.py create NEW.DB 50")
    print("  python3 decryptor.py pack CITY.DB.orig CITY.DB")  # noqa: SC100 (bare string comment)


if __name__ == "__main__":
    wd = '/mnt/d/games/WheelOfFortune/WHEEL'

    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        list_categories()
        sys.exit(0)

    if cmd == "dump":
        fname = sys.argv[2] if len(sys.argv) > 2 else "CITY.DB"
        path = fname if os.path.exists(fname) else f'{wd}/{fname}'
        show_count = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        if show_count:
            dump_first_n(path, show_count)
        else:
            dump(path, show_all=True)
        sys.exit(0)

    if cmd == "set":
        if len(sys.argv) < 5:
            print("Usage: decryptor.py set <file> <index> <text>")
            sys.exit(1)
        fname = sys.argv[2]
        path = fname if os.path.exists(fname) else f'{wd}/{fname}'
        idx = int(sys.argv[3])
        text = sys.argv[4]
        set_entry(path, idx, text)
        sys.exit(0)

    if cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: decryptor.py add <file> <text>")
            sys.exit(1)
        fname = sys.argv[2]
        path = fname if os.path.exists(fname) else f'{wd}/{fname}'
        text = sys.argv[3]
        add_entry(path, text)
        sys.exit(0)

    if cmd == "create":
        if len(sys.argv) < 4:
            print("Usage: decryptor.py create <file> <num_slots> [--old]")
            sys.exit(1)
        fname = sys.argv[2]
        path = fname if os.path.exists(fname) else f'{wd}/{fname}'
        slots = int(sys.argv[3])
        old_format = "--old" in sys.argv
        create_db(path, slots, old_format=old_format)
        sys.exit(0)

    if cmd == "pack":
        if len(sys.argv) < 4:
            print("Usage: decryptor.py pack <src> <dst>")
            sys.exit(1)
        src = sys.argv[2] if os.path.exists(sys.argv[2]) else f'{wd}/{sys.argv[2]}'
        dst = sys.argv[3] if os.path.exists(os.path.dirname(sys.argv[3]) or '.') else f'{wd}/{sys.argv[3]}'
        pack_file(src, dst)
        sys.exit(0)

    if cmd == "unpack":
        if len(sys.argv) < 4:
            print("Usage: decryptor.py unpack <src> <dst>")
            sys.exit(1)
        src = sys.argv[2] if os.path.exists(sys.argv[2]) else f'{wd}/{sys.argv[2]}'
        dst = sys.argv[3] if os.path.exists(os.path.dirname(sys.argv[3]) or '.') else f'{wd}/{sys.argv[3]}'
        unpack_file(src, dst)
        sys.exit(0)

    print(f"[-] Unknown command: {cmd}")
    usage()
    sys.exit(1)
