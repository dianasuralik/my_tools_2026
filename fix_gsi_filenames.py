#-------------------------------------------------------
### start fix_gsi_filenames.py

#!/usr/bin/env python3

"""
Generic script extracts tar, creates .nc symlinks pointing to .gsi.nc files, rebuilds tar, and writes the result to a specified output directory. 
The original archive is not changed. v1
"""

### imports
import os
import tarfile
import tempfile
import shutil
import argparse
from pathlib import Path

#-------------------------------------------------------
# PROCESS_TAR
#------------------------------------------------------
def process_tar(tar_path, output_dir):
    """
    Process a tar archive by creating symbolic links (*.nc -> *.gsi.nc)
    and writing a new archive to the output directory.

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
        # ------------------------------------------------------------
        # 2: Create symlinks (*.nc -> *.gsi.nc)
        # ------------------------------------------------------------
        print("Creating symbolic links...")
        link_count = 0
        for root, _, files in os.walk(extract_dir):
            root = Path(root)
            for filename in files:
                if filename.endswith(".gsi.nc"):
                    gsi_file = root / filename
                    nc_link = root / filename.replace(".gsi.nc", ".nc")
                    # Remove existing link if present
                    if nc_link.exists() or nc_link.is_symlink():
                        nc_link.unlink()
                    # Create relative symbolic link
                    nc_link.symlink_to(gsi_file.name)
                    print(f"Link: {nc_link} -> {gsi_file.name}")
                    link_count += 1  # end for loop
            # end for loop
        print(f"Created {link_count} symbolic link(s)")
        # ------------------------------------------------------------
        # 3: Repack archive
        # ------------------------------------------------------------
        print("Rebuilding archive...")
        new_tar = tmpdir / tar_path.name
        with tarfile.open(new_tar, "w") as tar:
            for item in extract_dir.rglob("*"):
                tar.add(item, arcname=item.relative_to(extract_dir))
        # ------------------------------------------------------------
        # 4: Move to output directory
        # ------------------------------------------------------------
        final_tar = output_dir / new_tar.name
        print(f"Moving archive to: {final_tar}")
        shutil.move(new_tar, final_tar)
    print(f"Done. Output written to: {final_tar}")
# end PROCESS_TAR
#------------------------------------------------------
