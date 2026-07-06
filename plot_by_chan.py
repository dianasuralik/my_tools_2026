## plot_by_chan
"""
/**
 * file plot_by_chan.py
 * Spatial visualization tool for satellite radiance data by channel index.
 * This script accepts an absolute path to a JEDI-style diagnostics netCDF file 
 * via command-line arguments. It extracts Latitude, Longitude, Channel_Index, 
 * and Observation variables, groups data points by unique channel IDs, and 
 * generates standalone spatial scatter plots saved as high-resolution PNGs.
 * * @usage python plot_by_chan.py <absolute_path_to_netcdf_file>
 * * @param sys.argv[1] Absolute path to the target netCDF (.nc or .nc4) data file.
 * @return Generates PNG plot files in a local './plots/' directory.
 * * @requires xarray (xr)
 * @requires matplotlib.pyplot (plt)
 */
"""

import os
import sys  
import argparse
import xarray as xr
import matplotlib.pyplot as plt

# ==========================================
# 1. Command-Line Argument Parsing
# ==========================================
parser = argparse.ArgumentParser(
    description="Spatial visualization tool for satellite radiance data by channel index."
)
parser.add_argument(
    "filepath", 
    type=str, 
    help="Absolute path to the target netCDF (.nc or .nc4) data file."
)
parser.add_argument(
    "-d", "--debug", 
    action="store_true", 
    help="Enable verbose debugging statements and show inline plots."
)

args = parser.parse_args()

nc_file = args.filepath
file_name_only = os.path.basename(nc_file)
# ==========================================
# 2. Environment & Directory Setup
# ==========================================
output_dir = "plots"
os.makedirs(output_dir, exist_ok=True)

# ==========================================
# 3. Data Extraction & Dataset Open
# ==========================================
print(f"Opening file: {nc_file}")
ds = xr.open_dataset(nc_file)

## Extract core coordinate arrays and variables of interest.
## Expected dimensions/coordinates: Latitude, Longitude, Channel_Index, Observation
lat = ds["Latitude"].values
lon = ds["Longitude"].values
ch  = ds["Channel_Index"].values
obs = ds["Observation"].values

# Identify unique channels present in the dataset
channels = sorted(set(ch))
print(f"Found channels: {channels}")

# ==========================================
# 4. Visualization & Plotting Loop
# ==========================================
for c in channels:
    mask = (ch == c)
    # Skip processing if the specific channel contains no data slices
    if not any(mask):
        continue
    print(f"Generating plot for Channel {c}...")
    plt.figure(figsize=(10, 5))
    # Generate geographic scatter distribution
    sc = plt.scatter(
        lon[mask],
        lat[mask],
        c=obs[mask],
        s=2,
        cmap="turbo"
    )
    
    # Configure plot elements and aesthetics
    plt.colorbar(sc, label="Observation")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(f"Channel {c} - {file_name_only}")
    
    # Commit plot export to disk
    out_png = os.path.join(output_dir, f"channel_{c}_obs.png")
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.show(block=False)

# Keep windows active until user terminates execution
input("Press Enter to close figures...")
print(f"\nDone! All plots saved to the '{output_dir}/' directory.")
print("done plots")
### end
