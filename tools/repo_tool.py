import os
import shutil
import difflib
from pathlib import Path

def create_work_dir(base: str, slug: str) -> str:
    target = os.path.abspath(os.path.join(base, slug))
    os.makedirs(target, exist_ok=True)
    return target

def copy_template(template_dir: str, dest_dir: str, overwrite: bool = True):
    """
    Copy template directory to destination, optionally overwriting existing files.
    Args:
        template_dir (str): Source template directory.
        dest_dir (str): Destination directory.
        overwrite (bool): If True, delete dest_dir before copying; if False, skip if dest_dir exists.
    """
    if not os.path.exists(template_dir):
        raise ValueError(f"Source template directory {template_dir} does not exist")
    if os.path.exists(dest_dir):
        if not overwrite:
            print(f"Destination {dest_dir} exists, skipping copy due to overwrite=False")
            return
        shutil.rmtree(dest_dir)
    shutil.copytree(template_dir, dest_dir)

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def make_unified_diff(original: str, new: str, filename: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, new_lines, fromfile=filename, tofile=filename, lineterm="")
    return "".join(diff)
