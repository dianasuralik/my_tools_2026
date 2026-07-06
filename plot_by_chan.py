## plot_by_chan
"""
 * file plot_by_chan.py
 * Spatial visualization tool for satellite radiance data by channel index.
 * This script accepts an absolute path to a JEDI-style diagnostics netCDF file 
 * via command-line arguments. It extracts Latitude, Longitude, Channel_Index, 
 * and Observation variables, groups data points by unique channel IDs, and 
 * generates standalone spatial scatter plots saved as high-resolution PNGs.
 * * @usage python plot_by_chan.py /path/to/your/file.nc4 [--debug]
 * * @param filepath Absolute path to the target netCDF (.nc or .nc4) data file.
 * * @param --debug Optional flag to enable verbose debugging logs.
 * @return Generates PNG plot files in a local './plots/' directory.
 * * @requires xarray (xr)
 * @requires matplotlib.pyplot (plt)
 */
"""
import os
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
print(f"[INFO] Opening file: {nc_file}")
try:
    ds = xr.open_dataset(nc_file)
except Exception as e:
    print(f"[ERROR] Failed to open dataset: {e}")
    exit(1)

## Extract core coordinate arrays and variables of interest.
if args.debug:
    print("[DEBUG] Extracting coordinate arrays (Lat, Lon, Channel, Obs)...")

lat = ds["Latitude"].values
lon = ds["Longitude"].values
ch  = ds["Channel_Index"].values
obs = ds["Observation"].values

# Identify unique channels present in the dataset
channels = sorted(set(ch))

print(f"[INFO] Found {len(channels)} unique channels.")
if args.debug:
    print(f"[DEBUG] Channels list: {channels}")

# ==========================================
# 4. Visualization & Plotting Loop
# ==========================================
for c in channels:
    mask = (ch == c)
    
    # Skip processing if the specific channel contains no data slices
    if not any(mask):
        if args.debug:
            print(f"[DEBUG] Skipping Channel {c}: No data points match mask.")
        continue
    
    if args.debug:
        print(f"[DEBUG] Generating plot for Channel {c} with {sum(mask)} data points...")
    else:
        print(f"[INFO] Processing Channel {c}...")

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
    
    # Handle display logic based on debug preference
    if args.debug:
        plt.show(block=False)
    else:
        plt.close() # Keep memory clean if we aren't viewing them interactively

# Keep windows active only if debug mode is on and plots were shown
if args.debug:
    input("\n[DEBUG] Press Enter to close figures and finish...")

print(f"\n[INFO] Done! All plots successfully saved to the '{output_dir}/' directory.")
### end
