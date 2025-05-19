import gzip
import sys
from pathlib import Path
from unittest import mock

import pytest

import decrypt_gpg.decrypt
from decrypt_gpg.decrypt import extract_gz, handle_archive, Decryptor, main


@pytest.fixture
def dummy_gz_file(tmp_path: Path) -> Path:
    gz_path = tmp_path / "test.txt.gz"
    with gzip.open(gz_path, "wb") as f:
        f.write(b"hello world")
    return gz_path


def test_recurse_calls_process_files(tmp_path: Path) -> None:
    # Setup test directory structure:
    # tmp_path/
    # ├── file1.txt
    # └── subdir/
    #     └── file2.txt
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "file1.txt").write_text("data")

    subdir = base_dir / "subdir"
    subdir.mkdir()
    (subdir / "file2.txt").write_text("more data")

    output_dir = tmp_path / "out"

    # Patch process_files to check call behavior
    decrypt = Decryptor("fake pass")
    with mock.patch.object(decrypt, "process_files") as mock_process:
        decrypt.recurse(base_dir, output_dir)

        # Check that process_files was called twice:
        # once for base, once for subdir
        assert mock_process.call_count == 2


def test_process_files_calls_process_file(tmp_path: Path) -> None:
    # Create dummy files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("data1")
    file2.write_text("data2")
    files = [file1, file2]

    # Create target directory
    target_dir = tmp_path / "out"
    target_dir.mkdir()

    # Mock process_file
    decrypt = Decryptor("fake pass")
    with mock.patch.object(decrypt, "process_file") as mock_process:
        decrypt.process_files(files, target_dir)

        # Verify process_file called for each file
        assert mock_process.call_count == len(files)

        # Check calls individually (optional)
        expected_calls = [
            mock.call(file1, target_dir),
            mock.call(file2, target_dir),
        ]
        mock_process.assert_has_calls(expected_calls, any_order=True)


def test_process_file_copies_file(tmp_path: Path) -> None:
    # Set up source file
    source_file = tmp_path / "original.txt"
    source_content = "This is a test file."
    source_file.write_text(source_content)

    # Set up target directory
    target_dir = tmp_path / "out"
    target_dir.mkdir()

    # Run the function
    decrypt = Decryptor("fake pass")
    decrypt.process_file(source_file, target_dir=target_dir)

    # Check that the file was copied
    copied_file = target_dir / "original.txt"
    assert copied_file.exists()
    assert copied_file.read_text() == source_content


def test_extract_gz(dummy_gz_file: Path) -> None:
    extract_gz(dummy_gz_file)
    output_file = dummy_gz_file.with_suffix("")
    assert output_file.exists()
    assert output_file.read_bytes() == b"hello world"
    assert not dummy_gz_file.exists()


@pytest.mark.parametrize("filename", ["archive.tgz", "archive.tar.gz", "archive.tar"])
def test_handle_archive_tar_variants(tmp_path: Path, filename: str) -> None:
    file_path = tmp_path / filename
    file_path.touch()
    with mock.patch("subprocess.run") as mock_run:
        handle_archive(file_path, tmp_path)
        assert not file_path.exists()
        mock_run.assert_called_once()


def test_handle_archive_gz(tmp_path: Path) -> None:
    file_path = tmp_path / "file.gz"
    with gzip.open(file_path, "wb") as f:
        f.write(b"data")
    handle_archive(file_path, tmp_path)
    assert (tmp_path / "file").exists()


def test_decrypt_gpg_file_runs(tmp_path: Path) -> None:
    input_file = tmp_path / "file.gpg"
    input_file.write_text("fake gpg data")
    output_file = tmp_path / "file"

    decrypt = Decryptor("fake pass")
    with mock.patch("subprocess.run") as mock_run:
        decrypt.decrypt_gpg_file(input_file, output_file)
        assert mock_run.called
        assert output_file.exists()  # File is opened before subprocess


def test_process_file_decrypt_and_handle(tmp_path: Path) -> None:
    gpg_file = tmp_path / "data.txt.gpg"
    gpg_file.write_text("secret")

    decrypt = Decryptor("fake pass")
    with (
        mock.patch.object(decrypt, "decrypt_gpg_file") as mock_decrypt,
        mock.patch("decrypt_gpg.decrypt.handle_archive") as mock_archive,
    ):
        decrypt.process_file(gpg_file, tmp_path)
        mock_decrypt.assert_called_once()
        mock_archive.assert_called_once()


def test_main_success(tmp_path: Path) -> None:
    base_dir = tmp_path / "input"
    base_dir.mkdir()
    output_dir = tmp_path / "decrypted"

    test_args = ["script.py", str(base_dir), "--output", str(output_dir)]

    with (
        mock.patch.object(sys, "argv", test_args),
        mock.patch("decrypt_gpg.decrypt.Decryptor") as mock_decryptor,
    ):
        main()
        assert output_dir.exists()
        mock_decryptor.return_value.recurse.assert_called_once_with(base_dir, output_dir)


def test_main_invalid_input_does_not_call_recurse(tmp_path: Path) -> None:
    invalid_path = tmp_path / "does_not_exist"

    test_args = ["script.py", str(invalid_path)]

    with (
        mock.patch.object(sys, "argv", test_args),
        mock.patch("decrypt_gpg.decrypt.Decryptor") as mock_decryptor,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        mock_decryptor.assert_not_called()
        mock_decryptor.return_value.recurse.assert_not_called()
