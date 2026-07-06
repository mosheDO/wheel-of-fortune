# Wheel of Fortune (1997) — Hebrew Edition

A Hebrew version of *Wheel of Fortune* (גלגל המזל) for **Windows 3.x**, released in 1997.

## Running the game

```bat
GO.bat
```

This launches `WHEEL.EXE` via **otvdm** (WineVDM) with **Locale Emulator** for Hebrew locale support. Works on modern Windows 10/11.

## DB file format

The game has 13 `.DB` files:

| File | Category | Entries |
|------|----------|---------|
| `ANIMAL.DB` | Animals | 100 |
| `BANDS.DB` | Bands | 32 |
| `CHARACTR.DB` | Characters | 63 |
| `CITY.DB` | Cities | 83 |
| `COUNTRY.DB` | Countries | 71 |
| `FAME.DB` | Famous People | 209 |
| `GENERAL.DB` | General Knowledge | 104 |
| `ITEMS.DB` | Items | 100 |
| `MOVIES.DB` | Movies | 267 |
| `PHRASE.DB` | Phrases | 107 |
| `SONGS.DB` | Songs | 101 |
| `TV.DB` | TV Shows | 86 |
| `HSCORE.DB` | High Scores | 11 |

### Original structure (all categories except HSCORE)

```
Each entry = 384,256 bytes = 1501 × 256
├── First 256 bytes: Pascal string XOR'd with 0x41
│   ├── byte 0: string length (NOT XOR'd)
│   └── bytes 1..length: Hebrew chars XOR'd 0x41 (windows-1255)
└── Remaining 384,000 bytes: zero padding (99.9% waste!)
```

The game reads a random entry by:
1. `Reset(f, 256)` — open with 256-byte record size
2. `FileSize / 1501` — number of entries
3. `Random(n)` — pick random entry
4. `Seek(random × 1501)` — seek to entry in 256-byte units
5. `Read 256 bytes` — read Pascal string header
6. XOR bytes 1..len with `0x41` — decrypt

The constant `1501` (`0x5DD`) is hardcoded in the EXE at two locations.

**HSCORE.DB** is separate: 11 × 260-byte records, plain binary, no XOR.

### Packed format (this branch)

The EXE was patched: both `mov cx, 0x5DD` instructions changed to `mov cx, 1`.
Now each entry is exactly 256 bytes — no padding, same encryption.

| Format | Before | After |
|--------|--------|-------|
| Per entry | 384,256 bytes | 256 bytes |
| All 12 DBs | **508 MB** | **339 KB** |

Original backups are preserved as `*.orig` in the `master` branch.

## decryptor.py

A Python tool to read, write, and convert DB files.

```bash
python3 decryptor.py list                       # list categories
python3 decryptor.py dump CITY.DB               # dump all entries
python3 decryptor.py dump CITY.DB 5             # first 5 only
python3 decryptor.py set CITY.DB 0 לונדון       # modify entry
python3 decryptor.py add CITY.DB תל אביב        # add to first empty
python3 decryptor.py create NEW.DB 50            # new packed DB
python3 decryptor.py create NEW.DB 50 --old      # new slot-format DB
python3 decryptor.py pack src.DB dst.DB          # old → packed
python3 decryptor.py unpack src.DB dst.DB        # packed → old
```

Auto-detects packed (256 bytes/entry) vs old slot (384,256 bytes/entry) vs HSCORE (260 bytes).

## EXE patch details

Two bytes in `WHEEL.EXE` changed at file offsets:

| Offset | Before | After | Meaning |
|--------|--------|-------|---------|
| `0x81F7` | `B9 DD 05` | `B9 01 00` | `mov cx, 0x5DD` → `mov cx, 1` |
| `0x821F` | `B9 DD 05` | `B9 01 00` | `mov cx, 0x5DD` → `mov cx, 1` |

No relocation entries point to these bytes — safe to patch. The algorithm is unchanged; only the slot-size constant is different.

### Reverting

```
git checkout master -- WHEEL/WHEEL.EXE
```

Or restore from `WHEEL.EXE.orig` (in `master` branch).

## License

All game assets belong to their respective copyright holders. This repository is for preservation and educational purposes only.
