from pathlib import Path
import shutil
import os

def collect_files_in_dir(dir_path: Path) -> list[Path]:
    if dir_path.is_dir():
        return [f for f in dir_path.iterdir() if f.is_file()]
    return []

def create_dir_if_not_exists(dir_path: Path):
    if not dir_path.exists():
        os.makedirs(dir_path)

def remove_dir_if_exists(dir_path: Path):
    if dir_path.exists():
        shutil.rmtree(dir_path)

def remove_file_if_exists(file_path: Path):
    if file_path.is_file():
        file_path.unlink()

def remove_files_if_exists(files: list[Path]):
    for file in files:
        remove_file_if_exists(file)

def clean_or_create_dir(dir_path: Path):
    if dir_path.exists():
        shutil.rmtree(dir_path)
    os.makedirs(dir_path)

def copy_file_to_dir(file_path: Path, dir_path: Path) -> Path:
    assert file_path.is_file(), \
        "'copy_file_to_dir' expects a valid path to a file as 1st argument"
    assert dir_path.is_dir(), \
        "'copy_file_to_dir' expects a valid path to an existing directory as 2nd argument"
    return shutil.copy(file_path, dir_path)

def copy_files_to_dir(file_paths: list[Path], dir_path: Path):
    for file_path in file_paths:
        copy_file_to_dir(file_path, dir_path)

def get_files_in_dir(dir_path: Path) -> list[Path]:
    assert dir_path.is_dir(), \
        "'get_files_in_dir' expects a valid path to an existing directory as argument"
    return [f for f in dir_path.iterdir()]

def move_dir(dir_path: Path, dir_target: Path) -> Path:
    assert dir_path.is_dir(), \
        "'move_dir' expects a valid path to an existing directory as argument"
    assert not dir_target.exists(), \
        "'move_dir' expects a non existing target directory location"
    return shutil.move(dir_path, dir_target)

def copy_or_overwrite_file(file_path: Path, target_file: Path) -> Path:
    assert file_path.is_file(), \
        "'copy_or_overwrite_file' expects a valid path to an existing directory as argument"
    return shutil.copy(file_path, target_file)