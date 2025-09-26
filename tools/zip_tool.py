import shutil

def zip_dir(src_dir: str, dest_path_without_ext: str) -> str:
    archive = shutil.make_archive(dest_path_without_ext, 'zip', root_dir=src_dir)
    return archive
