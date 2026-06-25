#-------------------------------------------------------
### start add_nc_symlinks_to_gsi.py

"""
Generic script extracts tar, creates .nc symlinks pointing to .gsi.nc files, rebuilds tar, and writes the result to a specified output directory. 
The original archive is not changed. v3
"""

#!/usr/bin/env python3

### imports
import os
import tarfile
import tempfile
import shutil
import argparse
from pathlib import Path

# debug (global)
DEBUG = False
#-------------------------------------------------------
# DPRINT
#-------------------------------------------------------
def dprint(msg):
    """iff debug == true, print info"""
    if DEBUG:
        print(f"[DEBUG] {msg}")
# end dprint
#-------------------------------------------------------


#-------------------------------------------------------
# PROCESS_TAR
#------------------------------------------------------
def process_tar(tar_path, output_dir):
    """
    Process a tar archive by creating symbolic links (*.nc -> *.gsi.nc)
    and writing a new archive to the output directory.
    """
    tar_path = Path(tar_path).resolve()
    output_dir = Path(output_dir).resolve()
    
    # file not found error
    if not tar_path.exists():
        raise FileNotFoundError(f"Tar file not found: {tar_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Processing: {tar_path}")
    dprint(f"Output directory: {output_dir}")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            extract_dir = tmpdir / "extract"
            extract_dir.mkdir()
            # ------------------------------------------------------------
            # 1: Extract archive
            # ------------------------------------------------------------
            print("Extracting archive...")
            dprint(f"Extract dir: {extract_dir}")
            try:
                with tarfile.open(tar_path, "r:*") as tar:
                    tar.extractall(extract_dir)
            except Exception as e:
                print(f"[ERROR] Failed to extract tar: {e}")
                return
            dprint("Extraction complete")
            # ------------------------------------------------------------
            # 2: Create symlinks (*.nc -> *.gsi.nc)
            # ------------------------------------------------------------
            print("Creating symbolic links...")
            link_count = 0
            for root, _, files in os.walk(extract_dir):
                root = Path(root)
                dprint(f"Scanning directory: {root}")
                for filename in files:
                    if filename.endswith(".gsi.nc"):
                        gsi_file = root / filename
                        nc_link = root / filename.replace(".gsi.nc", ".nc")
                        dprint(f"Found GSI file: {gsi_file}")
                        try:
                            if nc_link.exists() or nc_link.is_symlink():
                                nc_link.unlink()
                                dprint(f"Removed existing link: {nc_link}")
                            nc_link.symlink_to(gsi_file.name)
                            print(f"Link: {nc_link} -> {gsi_file.name}")
                            link_count += 1
                        except Exception as e:
                            print(f"[ERROR] Failed to create symlink for {gsi_file}: {e}")
                        ## end try
                    ## end if
                # end for loop
            # end for loop
            print(f"Created {link_count} symbolic link(s)")
            dprint("Symlink creation finished")
            # ------------------------------------------------------------
            # 3: Repack archive
            # ------------------------------------------------------------
            print("Rebuilding archive...")
            new_tar = tmpdir / tar_path.name
            dprint(f"New tar path: {new_tar}")
            try:
                with tarfile.open(new_tar, "w") as tar:
                    for item in extract_dir.rglob("*"):
                        dprint(f"Adding to tar: {item}")
                        tar.add(item, arcname=item.relative_to(extract_dir))
            except Exception as e:
                print(f"[ERROR] Failed to build tar: {e}")
                return
            # ------------------------------------------------------------
            # 4: Move to output directory
            # ------------------------------------------------------------
            final_tar = output_dir / new_tar.name
            dprint(f"Final tar target: {final_tar}")
            try:
                shutil.move(new_tar, final_tar)
            except Exception as e:
                print(f"[ERROR] Failed to move tar: {e}")
                return
        print(f"Done. Output written to: {final_tar}")
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
# end PROCESS_TAR
#------------------------------------------------------


#-------------------------------------------------------
# MAIN
#------------------------------------------------------
def main():
    """
    This function parses command-line arguments, enables optional debug mode, and invokes the main processing workflow.
    Command-line Arguments
        tar_file : (str) Path to the input tar archive to be processed.
        output_dir : (str) Directory where the processed tar archive will be written.
    Optional Arguments
        --debug : bool
            Enables verbose debug output for tracing execution steps,
            including directory scanning, file processing, and archive
            creation stages.
    Returns:  None
    Examples:
        Normal execution: python3 fix_gsi_filenames.py input.tar output_dir
        Debug mode: python3 fix_gsi_filenames.py input.tar output_dir --debug
    """
    global DEBUG

    # Create command-line argument parser to handle user inputs
    parser = argparse.ArgumentParser(
        description="Process tar files and create .nc symlinks for .gsi.nc files"
    )
    # Positional argument: input tar archive path
    # Positional argument: output directory where new tar will be written
    parser.add_argument("tar_file")
    parser.add_argument("output_dir")
    
    # debug flag
    # Optional flag:
    # If --debug is present → args.debug = True
    # If omitted → args.debug = False
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )

    args = parser.parse_args()
    DEBUG = args.debug
    # Print debug message ONLY if DEBUG == True
    dprint("Debug mode enabled")
    process_tar(args.tar_file, args.output_dir)
# end MAIN
#------------------------------------------------------

if __name__ == "__main__":
    main()

# end add_nc_symlinks_to_gsi.py
#-------------------------------------------------------
