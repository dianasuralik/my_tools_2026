## input_path =
## output_path = 

#!/usr/bin/env python3
"""
Generic script extracts tar, creates zeroed-out companion .nc files for 
satbias and satbias_cov .gsi.nc files, rebuilds tar, and writes the result 
to a specified output directory. Original archive not changed. v4
"""

import os
import tarfile
import tempfile
import shutil
import argparse
from pathlib import Path

# Try to import netCDF4 for accurate data structural cloning
try:
    import netCDF4 as nc
    HAS_NETCDF4 = True
except ImportError:
    HAS_NETCDF4 = False

# debug (global)
DEBUG = False

def dprint(msg):
    """iff debug == true, print info"""
    if DEBUG:
        print(f"[DEBUG] {msg}")


def zero_out_netcdf(source_path, target_path):
    """
    Reads a source NetCDF file, replicates its exact schema (dimensions, 
    variables, and attributes) into a target file, and zeroes out all data fields.
    """
    if not HAS_NETCDF4:
        raise ImportError(
            "The 'netCDF4' library is required to create structurally valid zeroed NetCDF files. "
            "Please install it via: pip install netCDF4"
        )
        
    with nc.Dataset(source_path, "r") as src, nc.Dataset(target_path, "w", format=src.file_format) as dst:
        # 1. Copy global attributes
        dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})
        
        # 2. Copy dimensions
        for name, dimension in src.dimensions.items():
            dst.createDimension(
                name, 
                (len(dimension) if not dimension.isunlimited() else None)
            )
            
        # 3. Copy variables and fill with zeros
        for name, src_var in src.variables.items():
            # Create variable with matching metadata
            dst_var = dst.createVariable(
                varname=name,
                datatype=src_var.datatype,
                dimensions=src_var.dimensions,
                fill_value=src_var._FillValue if hasattr(src_var, '_FillValue') else None
            )
            # Copy variable attributes
            dst_var.setncatts({k: src_var.getncattr(k) for k in src_var.ncattrs() if k != '_FillValue'})
            
            # Fill with zeros matching the original shape
            if src_var.shape:
                dst_var[...] = 0
            else:
                dst_var.assignValue(0)


def process_tar(tar_path, output_dir):
    """
    Process a tar archive by generating zeroed-out companion files (*.nc)
    for satbias/satbias_cov data and writing a new archive to the output directory.
    """
    tar_path = Path(tar_path).resolve()
    output_dir = Path(output_dir).resolve()
    
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
            try:
                with tarfile.open(tar_path, "r:*") as tar:
                    tar.extractall(extract_dir)
            except Exception as e:
                print(f"[ERROR] Failed to extract tar: {e}")
                return
            dprint("Extraction complete")
            
            # ------------------------------------------------------------
            # 2: Create Zeroed Companion Files
            # ------------------------------------------------------------
            print("Processing GSI files and creating zeroed companions...")
            file_count = 0
            
            for root, _, files in os.walk(extract_dir):
                root = Path(root)
                for filename in files:
                    if filename.endswith(".gsi.nc"):
                        # Skip explicit tlapse files completely
                        if "tlapse" in filename:
                            dprint(f"Skipping tlapse file: {filename}")
                            continue
                            
                        # Check if file targets satbias or satbias_cov
                        if "satbias" in filename or "satbias_cov" in filename:
                            gsi_file = root / filename
                            nc_file = root / filename.replace(".gsi.nc", ".nc")
                            
                            dprint(f"Found target file: {gsi_file}")
                            try:
                                if nc_file.exists() or nc_file.is_symlink():
                                    nc_file.unlink()
                                    dprint(f"Removed existing target file/link: {nc_file}")
                                
                                # Generate the structurally identical, empty file
                                zero_out_netcdf(gsi_file, nc_file)
                                print(f"Created zeroed file: {nc_file.name} (sourced from {gsi_file.name})")
                                file_count += 1
                                
                            except Exception as e:
                                print(f"[ERROR] Failed to process {gsi_file.name}: {e}")
            
            print(f"Successfully generated {file_count} zeroed file(s)")
            
            # ------------------------------------------------------------
            # 3: Repack archive
            # ------------------------------------------------------------
            print("Rebuilding archive...")
            new_tar = tmpdir / tar_path.name
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


def main():
    global DEBUG

    parser = argparse.ArgumentParser(
        description="Extract tar, create zeroed out satbias companion datasets, and repack."
    )
    parser.add_argument("tar_file")
    parser.add_argument("output_dir")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )

    args = parser.parse_args()
    DEBUG = args.debug
    dprint("Debug mode enabled")
    
    if not HAS_NETCDF4:
        print("[FATAL] Python 'netCDF4' library is missing. Run: pip install netCDF4")
        return

    process_tar(args.tar_file, args.output_dir)

if __name__ == "__main__":
    main()
