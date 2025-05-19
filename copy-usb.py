import argparse
import concurrent.futures
import hashlib
from os import listdir, walk, cpu_count, makedirs
from os.path import isfile, join, isdir, dirname, abspath, relpath, basename
from pathlib import Path
from shutil import copy
from sys import argv

BUF_SIZE = 65536
DRYRUN_STR = "(dryrun) "


def filehash(path):
    m = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            m.update(data)
    return m.hexdigest()


def copy_if_needed(src, dest):
    """
    If destination file exists, and is same size as source, and has the same hash, just return.
    Otherwise, copy source to target.
    :param src:
    :param dest:
    :return:
    """
    d = Path(dest)
    s = Path(src)
    if d.is_file() and d.stat().st_size == s.stat().st_size and filehash(src) == filehash(dest):
        return
    log(f"{src} -> {dest}")
    if not args.dryrun:
        makedirs(dirname(dest), exist_ok=True)
        copy(src, dest)


def delete_if_not_exists(dest, src):
    """
    If a file doesn't exist in the source, delete the file on destination.

    (The traverse call is flipped so files can be discovered,
    and the variables are flipped to match the meaning of the overall copy.)
    :param src:
    :param dest:
    :return:
    """
    s = Path(src)
    if not s.exists():
        log(f"DELETE: {dest}")
        if not args.dryrun:
            d = Path(dest)
            d.unlink()


def traverse(src, tgt, fn):
    execs = {}
    cpus = cpu_count()
    with concurrent.futures.ThreadPoolExecutor(max_workers=cpus) as executor:
        for (dirpath, _dirnames, filenames) in walk(src):
            for fname in filenames:
                s = abspath(join(dirpath, fname))
                r = relpath(s, abspath(src))
                execs[executor.submit(fn, s, abspath(join(tgt, r)))] = s
                if len(execs) > cpus * 3:
                    for e in concurrent.futures.as_completed(execs):
                        e.result()
                        del execs[e]
        for e in concurrent.futures.as_completed(execs):
            e.result()


def log(msg):
    d = DRYRUN_STR if args.dryrun else ''
    print(f"{d}{msg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy decrypted files to destination"
                                                 " without deleting existing files that are identical")

    parser.add_argument("start")
    parser.add_argument("target")
    parser.add_argument("-c", "--copy", action="store_true")
    parser.add_argument("-d", "--dryrun", action="store_true")
    parser.add_argument("-D", "--delete", action="store_true")
    args = parser.parse_args()

    log(f"{args.start} -> {args.target}")
    if args.copy:
        traverse(args.start, args.target, copy_if_needed)
    if args.delete:
        traverse(args.target, args.start, delete_if_not_exists)
