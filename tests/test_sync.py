from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, create_autospec, call

import pytest
from pytest_mock import MockFixture

import decrypt_gpg.sync


@pytest.fixture()
def mock_copy(mocker: MockFixture) -> MagicMock:
    return mocker.patch("decrypt_gpg.sync.copy")


@pytest.fixture()
def mock_delete(mocker: MockFixture) -> MagicMock:
    return mocker.spy(decrypt_gpg.sync, "delete_if_not_exists")


@pytest.fixture(autouse=True)
def src_dir_tree(tmp_path: Path) -> None:
    base_dir = tmp_path / "foo"
    dir1 = base_dir / "dir1"
    dir2 = dir1 / "dir2"
    dir3 = base_dir / "dir3"
    dir4 = dir3 / "dir4"
    dir2.mkdir(parents=True)
    dir4.mkdir(parents=True)

    (dir1 / "file1").write_text("i am 1")
    (dir2 / "file2").write_text("i am 2")
    (dir3 / "file3").write_text("i am 3")
    (dir4 / "file4").write_text("i am 4")


@pytest.fixture(autouse=True)
def set_default_test_args(tmp_path: Path) -> Iterator[None]:
    saved_args = decrypt_gpg.sync.args
    decrypt_gpg.sync.args = decrypt_gpg.sync.MyArgs(start=tmp_path / "foo", target=tmp_path / "bar", dryrun=False)
    yield
    decrypt_gpg.sync.args = saved_args


@pytest.fixture()
def dest_dir_tree(tmp_path: Path) -> None:
    base_dir = tmp_path / "bar"

    dir5 = base_dir / "dir5"
    dir5.mkdir(parents=True)
    (dir5 / "file5").write_text("i am 5")

    dir6 = base_dir / "foo" / "dir6"
    dir6.mkdir(parents=True)

    (dir6 / "file6").write_text("i am 6")


def test_traverse_for_copy(tmp_path: Path, mock_copy: MagicMock, mock_delete: MagicMock) -> None:
    decrypt_gpg.sync.args.copy = True
    decrypt_gpg.sync.main()

    assert mock_copy.call_count == 4
    mock_copy.assert_has_calls(
        [
            call(tmp_path / "foo/dir3/file3", tmp_path / "bar/foo/dir3/file3"),
            call(tmp_path / "foo/dir3/dir4/file4", tmp_path / "bar/foo/dir3/dir4/file4"),
            call(tmp_path / "foo/dir1/file1", tmp_path / "bar/foo/dir1/file1"),
            call(tmp_path / "foo/dir1/dir2/file2", tmp_path / "bar/foo/dir1/dir2/file2"),
        ],
        any_order=True,
    )
    mock_delete.assert_not_called


def test_traverse_for_delete(tmp_path: Path, dest_dir_tree: None, mock_delete: MagicMock) -> None:
    decrypt_gpg.sync.args.copy = True  # copy the files from source to dest first
    decrypt_gpg.sync.args.delete = True
    decrypt_gpg.sync.main()

    assert mock_delete.call_count == 5
    mock_delete.assert_has_calls(
        [
            call(src=tmp_path / "foo/dir3/file3", dest=tmp_path / "bar/foo/dir3/file3"),
            call(src=tmp_path / "foo/dir3/dir4/file4", dest=tmp_path / "bar/foo/dir3/dir4/file4"),
            call(src=tmp_path / "foo/dir6/file6", dest=tmp_path / "bar/foo/dir6/file6"),
            call(src=tmp_path / "foo/dir1/file1", dest=tmp_path / "bar/foo/dir1/file1"),
            call(src=tmp_path / "foo/dir1/dir2/file2", dest=tmp_path / "bar/foo/dir1/dir2/file2"),
        ],
        any_order=True,
    )
    assert (tmp_path / "foo/dir1/file1").exists()
    assert (tmp_path / "foo/dir1/dir2/file2").exists()
    assert (tmp_path / "foo/dir3/file3").exists()
    assert (tmp_path / "foo/dir3/dir4/file4").exists()
    assert (tmp_path / "bar/foo/dir1/file1").exists()
    assert (tmp_path / "bar/foo/dir1/dir2/file2").exists()
    assert (tmp_path / "bar/foo/dir3/file3").exists()
    assert (tmp_path / "bar/foo/dir3/dir4/file4").exists()
    # Didn't touch file outside of the source path.
    assert (tmp_path / "bar/dir5/file5").exists()
    # Deleted extra file that should have been in source but wasn't.
    assert not (tmp_path / "bar/foo/dir6/file6").exists()


@pytest.mark.parametrize(
    "src,dest,subdir, expected",
    [
        [Path("/base/bar"), Path("/base2/exp/foo"), Path("/base2/exp/foo/bar/az"), Path("/base/bar/az")],
        [Path("/base/bar"), Path("/base/foo"), Path("/base/foo/bar/baz/quux"), Path("/base/bar/baz/quux")],
        [
            Path("/tmp/pytest/pytest-128/test_traverse_for_delete0/foo"),
            Path("/tmp/pytest/pytest-128/test_traverse_for_delete0/bar"),
            Path("/tmp/pytest/pytest-128/test_traverse_for_delete0/bar/foo/dir1/dir2"),
            Path("/tmp/pytest/pytest-128/test_traverse_for_delete0/foo/dir1/dir2"),
        ],
    ],
)
def test_get(src: Path, dest: Path, subdir: Path, expected: Path) -> None:
    assert decrypt_gpg.sync.get_filepath_in_source(src, dest, subdir) == expected
