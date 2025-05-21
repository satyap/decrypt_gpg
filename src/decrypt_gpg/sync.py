import argparse
import concurrent.futures
import hashlib
from os import walk, cpu_count, makedirs
from pathlib import Path
from shutil import copy

BUF_SIZE = 65536
DRYRUN_STR = "(dryrun) "


def get_cpu_count() -> int:
    cpus = cpu_count()
    if cpus:
        return cpus
    else:
        return 2


def filehash(path: Path) -> str:
    m = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            m.update(data)
    return m.hexdigest()


def copy_if_needed(src: Path, dest: Path) -> None:
    """
    If destination file exists, and is same size as source, and has the same hash, just return.
    Otherwise, copy source to target.
    :param src:
    :param dest:
    :return:
    """
    if dest.is_file() and dest.stat().st_size == src.stat().st_size and filehash(src) == filehash(dest):
        return
    log(f"{src} -> {dest}")
    if not args.dryrun:
        makedirs(dest.parent, exist_ok=True)
        copy(src, dest)


def delete_if_not_exists(dest: Path, src: Path) -> None:
    """
    If a file doesn't exist in the source, delete the file on destination.
    :param src:
    :param dest:
    :return:
    """
    if not src.exists():
        log(f"DELETE: {dest}")
        if not args.dryrun:
            dest.unlink()


def traverse_for_copy(src: Path, tgt: Path) -> None:
    execs = []
    cpus = get_cpu_count()
    with concurrent.futures.ThreadPoolExecutor(max_workers=cpus) as executor:
        for dirpath, _dirnames, filenames in walk(src):
            for fname in filenames:
                s = Path(dirpath) / fname
                r = (tgt / s.relative_to(src.parent)).resolve()
                execs.append(executor.submit(copy_if_needed, s, r))
                if len(execs) > cpus * 3:
                    for e in concurrent.futures.as_completed(execs):
                        e.result()
                    execs = []
        for e in concurrent.futures.as_completed(execs):
            e.result()


def get_filepath_in_source(src: Path, dest: Path, subdir: Path) -> Path:
    """
    Returns the path for the given dest directory that should be present in the given src directory.
    :param src: Root of the source tree that we're syncing.
    :param dest: root of the destination tree where we're syncing.
    :param subdir: Destination directory (a sub-dir of the destination root) where we're syncing.
    :return: The path up to the subdirectory in the source tree, which corresponds to the destination.
    """
    relative = subdir.relative_to(dest / src.stem)
    return src / relative


def traverse_for_delete(src: Path, dest: Path) -> None:
    execs = []
    cpus = get_cpu_count()
    with concurrent.futures.ThreadPoolExecutor(max_workers=cpus) as executor:
        for dirpath, _dirnames, filenames in walk(dest):
            for fname in filenames:
                r = Path(dirpath) / fname
                try:
                    s = get_filepath_in_source(src, dest, Path(dirpath)) / fname
                except ValueError as exc:
                    continue
                execs.append(executor.submit(delete_if_not_exists, src=s, dest=r))
                if len(execs) > cpus * 3:
                    for e in concurrent.futures.as_completed(execs):
                        e.result()
                    execs = []
        for e in concurrent.futures.as_completed(execs):
            e.result()


def log(msg: str) -> None:
    global args
    d = DRYRUN_STR if args.dryrun else ""
    print(f"{d}{msg}")


class MyArgs(argparse.Namespace):
    """CLI arguments class to make various type checkers happy."""

    start: Path = Path("")
    target: Path = Path("")
    copy: bool = False
    dryrun: bool = True
    force: bool = False
    delete: bool = False


def get_args() -> MyArgs:
    parser = argparse.ArgumentParser(
        description="Copy decrypted files to destination without deleting existing files that are identical"
    )
    parser.add_argument("start")
    parser.add_argument("target")
    parser.add_argument("-c", "--copy", help="Copy files", action="store_true")
    parser.add_argument("-f", "--force", help="Actually perform operations", action="store_true")
    parser.add_argument(
        "-D", "--delete", help="Delete files in target that are not in the start tree", action="store_true"
    )
    a = parser.parse_args()
    a.dryrun = not a.force
    return MyArgs(**vars(a))


def run() -> None:
    global args
    if not args.start or not args.target:
        print("Needs start and target locations")
        exit(1)
    start = Path(args.start).resolve()
    target = Path(args.target).resolve()
    if not start.is_dir() or (target.exists() and not target.is_dir()):
        print("start and target need to be directories")
        exit(1)
    log(f"{start} -> {target}")
    if args.copy:
        log("Copying...")
        traverse_for_copy(start, target)
    if args.delete:
        log("Deleting non-existing files...")
        traverse_for_delete(start, target)


def main() -> None:
    global args
    args = get_args()
    run()


args = MyArgs()
if __name__ == "__main__":
    main()
