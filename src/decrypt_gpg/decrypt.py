import argparse
import gzip
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from getpass import getpass
from pathlib import Path
from sys import exit
from typing import List

default_output_path = Path("decrypted")


def prompt_for_password() -> str:
    """Securely prompt for the GPG password."""
    try:
        return getpass("GPG password: ")
    except KeyboardInterrupt:
        print("\n")
        exit(1)


def decrypt_gpg_file(src: Path, dest: Path, password: str) -> None:
    """Decrypt a .gpg file to dest using GPG and the provided passphrase."""
    try:
        with open(dest, "wb") as out_file:
            subprocess.run(
                ["gpg", "--ignore-mdc-error", "--batch", "-qd", "--passphrase", password, str(src)],
                stdout=out_file,
                stderr=subprocess.PIPE,
                check=True,
            )
    except subprocess.CalledProcessError as e:
        print(f"\nError decrypting {src}:\n{e.stderr.decode()}")
        exit(1)


def extract_gz(file_path: Path) -> None:
    """Decompress a .gz file using Python's gzip module."""
    output_path = file_path.with_suffix("")  # Remove .gz
    try:
        with gzip.open(file_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        file_path.unlink()
    except OSError as e:
        print(f"\nFailed to decompress {file_path}: {e}")
        exit(1)


def handle_archive(file_path: Path, working_dir: Path) -> None:
    """Properly handle various archive types: .tgz, .tar.gz, .gz, .tar."""
    name = file_path.name
    suffix = file_path.suffix
    if suffix == ".tgz" or name.endswith(".tar.gz"):
        subprocess.run(["tar", "xzf", name], cwd=working_dir, check=True)
        file_path.unlink()
    elif suffix == ".tar":
        subprocess.run(["tar", "xf", name], cwd=working_dir, check=True)
        file_path.unlink()
    elif suffix == ".gz":
        extract_gz(file_path)


def process_file(entry: Path, password: str, target_dir: Path) -> None:
    filename = entry.name
    target_path = target_dir / filename
    if filename.endswith(".gpg"):
        decrypted_filename = filename[:-4]
        decrypted_path = target_dir / decrypted_filename
        decrypt_gpg_file(entry, decrypted_path, password)
        target_path = decrypted_path
    else:
        shutil.copy2(entry, target_path)

    handle_archive(target_path, target_dir)
    print(".", end="", flush=True)


def process_files(files: List[Path], target_dir: Path, password: str) -> None:
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_file, file_entry, password, target_dir) for file_entry in files]
        for future in as_completed(futures):
            future.result()  # will raise exception if one occurred


def recurse(src_dir: Path, dec_root: Path, password: str) -> None:
    """Recursively process and decrypt/copy/extract files from the directory."""
    print(src_dir, end="")
    if not src_dir.is_dir():
        print(f"\nSkipping non-directory: {src_dir}")
        return

    target_dir = dec_root / src_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    entries = sorted([entry for entry in src_dir.iterdir() if not entry.name.startswith(".")])
    subdirs: List[Path] = []
    files: List[Path] = []

    for entry in entries:
        if entry.is_dir():
            subdirs.append(entry)
        else:
            files.append(entry)

    process_files(files, target_dir, password)

    for subdir in subdirs:
        print()
        recurse(subdir, dec_root, password)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recursively decrypt and extract GPG-encrypted archives.")
    parser.add_argument("base_dir", type=Path, help="Base directory to process")
    parser.add_argument(
        "--output", type=Path, default=default_output_path, help="Output directory (default: decrypted)"
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    if not base_dir.is_dir():
        print(f"Error: '{base_dir}' is not a valid directory.")
        exit(1)

    password = prompt_for_password()

    args.output.mkdir(exist_ok=True)

    start_time = time.time()
    recurse(base_dir, args.output, password)
    elapsed = time.time() - start_time
    print(f"\ntook {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
