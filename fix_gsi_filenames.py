### fix_gsi_filenames.py
#!/usr/bin/env python3

"""
Updating tar archives containing GSI NetCDF files.  This script extracts a tar archive, creates symbolic links for`.nc` files 
pointing to corresponding `.gsi.nc` files, rebuilds the archive, and writes the result to a specified output directory.
The original archive is not changed. v1
"""
### imports
import os
import tarfile
import tempfile
import shutil
from pathlib import Path

#-------------------------------------------------------
# PROCESS_TAR
#------------------------------------------------------
def process_tar(tar_path, output_dir):
    """
    Processes a tar archive by creating symbolic links for NetCDF files and rebuilding the archive in a new output location.
    Workflow
    --------
    1. Validate input tar archive exists.
    2. Create a temporary working directory.
    3. Extract tar contents into the working directory.
    4. Create symbolic links: *.nc -> *.gsi.nc
    5. Rebuild the tar archive including symlinks.
    6. Move the final archive to the output directory.
    Parameters
    ----------
    tar_path : str or pathlib.Path
        Path to the input tar archive.
    output_dir : str or pathlib.Path
        Directory where the processed tar archive will be written.
    Raises
    ------
    FileNotFoundError
        If the input tar archive does not exist.
    Returns
    -------
      None
    """
    tar_path = Path(tar_path).resolve()
    output_dir = Path(output_dir).resolve()
  # file not found error
    if not tar_path.exists():
        raise FileNotFoundError(f"Tar file not found: {tar_path}")
      
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Processing: {tar_path}")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        extract_dir = tmpdir / "extract"
        extract_dir.mkdir()
        # ------------------------------------------------------------
        # 1: Extract archive
        # ------------------------------------------------------------
        print("Extracting archive...")
        with tarfile.open(tar_path, "r:*") as tar:
            tar.extractall(extract_dir)
