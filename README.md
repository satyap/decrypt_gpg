# 🔐 Decrypt and Sync Utility

A Python CLI tool for:

1. **GPG Decryption** – Recursively decrypts and extracts archived files.
2. **USB Syncing** – Syncs a decrypted directory to another location (like a USB drive), with optional cleanup of outdated files.

---

## 📦 Installation

Install the CLI tools using `pip`:

```bash
pip install .
```

This installs two command-line tools:

- `decrypt-gpg`
- `sync-usb`

---

## 🔐 `decrypt-gpg`

Recursively decrypts a directory tree of GPG-encrypted files and extracts common archive formats.

### ✔ Features

- Decrypts `.gpg` files using GPG and a securely prompted passphrase.
- Automatically extracts:
  - `.tar.gz`, `.tgz`
  - `.tar`
  - `.gz`
- Copies other files as-is.
- Maintains the original folder structure.

### 🗂 Arguments

| Argument        | Description                                                |
|-----------------|------------------------------------------------------------|
| `base_dir`      | Path to the encrypted input directory.                     |
| `--output`      | Output directory for decrypted files (default: `decrypted/`) |

### 🚀 Example Usage

```bash
decrypt-gpg path/to/encrypted/files
decrypt-gpg path/to/encrypted/files --output path/to/decrypted/
```

---

## 🔄 `sync-usb`

Syncs files from a **source directory** (e.g. decrypted data) to a **destination** (e.g. USB drive).  
Files are only copied if they differ by size or SHA256 checksum.

### ✔ Features

- Skips identical files to speed up syncing.
- Optionally deletes files in the destination that no longer exist in the source.
- Can perform a dry run by default — use `--force` to actually apply changes.

### 🗂 Arguments

| Argument         | Description                                                       |
|------------------|-------------------------------------------------------------------|
| `start`          | Source directory to sync from                                     |
| `target`         | Destination directory to sync to                                  |
| `-c`, `--copy`   | Copy changed files                                                |
| `-f`, `--force`  | Actually perform the operations (default is dry run)              |
| `-D`, `--delete` | Delete files in the destination that aren't present in the source |

### 🚀 Example Usage

```bash
# Dry run (default): shows what would be done
sync-usb decrypted/ /media/usbdrive --copy # copy only
sync-usb decrypted/ /media/usbdrive --delete # delete only

# Copy updated files
sync-usb decrypted/ /media/usbdrive --copy --force

# Perform sync and delete stale files
sync-usb decrypted/ /media/usbdrive --copy --force --delete
```

---

## 🔐 Requirements

- Python 3.8+
- GPG must be installed and available in your system’s PATH

---

## 🧪 Testing

Run tests and check doctests + coverage:

```bash
make tests
```

