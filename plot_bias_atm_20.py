### 
### 
### 
#plot bias atm 20 py
"""
 * file plot_bias_atm20.py
 * Diagnostic tool for monitoring and evaluating satellite radiance VarBC.
 * This script ingests a JEDI-style observation diagnostics NetCDF file, extracts 
 * unadjusted and bias-corrected Obs-Minus-Forecast (OmF) statistics, and generates 
 * a suite of engineering metrics including mean offsets, standard deviations, 
 * total applied bias correction bars, and boxplot distribution spectrums.
 *
 * @usage python plot_bias_atm20.py /path/to/diag_file.nc [--debug]
 * @param filepath Absolute or relative path to the JEDI radiance diagnostics NetCDF file.
 * @param --debug Optional flag to enable verbose printing and display interactive plots.
 * @return Generates high-resolution PNG diagnostic charts locally.
 *
 * @requires xarray (xr)
 * @requires numpy (np) 
 * @requires matplotlib.pyplot (plt)
"""

import os
import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. Command-Line Argument Parsing
# ==========================================
parser = argparse.ArgumentParser(
    description="Diagnostic validation and statistical profiling tool for radiance VarBC data."
)
parser.add_argument(
    "filepath", 
    type=str, 
    help="Path to the JEDI radiance diagnostics NetCDF file."
)
parser.add_argument(
    "-d", "--debug", 
    action="store_true", 
    help="Enable verbose debugging prints and render interactive plot frames."
)

args = parser.parse_args()
filename = args.filepath
file_name_base = os.path.basename(filename)

# ==========================================
# 2. Data Extraction & Dataset Handling
# ==========================================
print(f"[INFO] Ingesting file: {filename}")
try:
    ds = xr.open_dataset(filename)
except Exception as e:
    print(f"[ERROR] Failed to open dataset: {e}")
    exit(1)

if args.debug:
    print("[DEBUG] Unpacking JEDI observation metrics...")

# Extract variables
chan = ds["Channel_Index"].values
omb_unadj = ds["Obs_Minus_Forecast_unadjusted"].values
omb_adj = ds["Obs_Minus_Forecast_adjusted"].values
sensor_chan = ds["sensor_chan"].values

# Clean out bad fill values
if args.debug:
    print("[DEBUG] Dropping missing entries and extreme fill values (> 1e5)...")
omb_unadj = np.where(np.abs(omb_unadj) > 1e5, np.nan, omb_unadj)
omb_adj   = np.where(np.abs(omb_adj) > 1e5, np.nan, omb_adj)

# ==========================================
# 3. Compute Channel Statistics
# ==========================================
channels = np.sort(np.unique(chan))
if args.debug:
    print(f"[DEBUG] Found unique sorting sequence for channels: {channels}")

mean_unadj, mean_adj = [], []
std_unadj, std_adj = [], []
mean_bc = []

for ch in channels:
    idx = (chan == ch)
    unadj = omb_unadj[idx]
    adj = omb_adj[idx]

    if args.debug:
        print(f"[DEBUG] Chan {ch} counts: Valid={np.ma.count(unadj)}, Min={np.nanmin(unadj):.2f}, Max={np.nanmax(unadj):.2f}")

    mean_unadj.append(np.nanmean(unadj))
    mean_adj.append(np.nanmean(adj))
    std_unadj.append(np.nanstd(unadj))
    std_adj.append(np.nanstd(adj))
    mean_bc.append(np.nanmean(unadj - adj))

# Convert to arrays for clean handling
mean_unadj = np.array(mean_unadj)
mean_adj = np.array(mean_adj)
std_unadj = np.array(std_unadj)
std_adj = np.array(std_adj)
mean_bc = np.array(mean_bc)

# Map Channel_Index to physical sensor channel labels
channel_map = dict(zip(np.arange(1, len(sensor_chan) + 1), sensor_chan))
channel_labels = [str(channel_map.get(ch, ch)) for ch in channels]

# ==========================================
# 4. Visualization Routines
# ==========================================
print("[INFO] Generating diagnostic metric charts...")

# --- Figure 1: Mean O-F by channel ---
plt.figure(figsize=(10, 5))
plt.plot(channels, mean_unadj, "o-", lw=2, label="Unadjusted")
plt.plot(channels, mean_adj, "s-", lw=2, label="Bias Corrected")
plt.axhline(0, color="k", lw=1)
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean O-F (K)")
plt.title("Mean Observation Minus Forecast by Channel")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("mean_obs__forecast_by_chan.png", dpi=300, bbox_inches="tight")
if args.debug: 
    plt.show(block=False)
else: 
    plt.close()

# --- Figure 2: Standard deviation by channel ---
plt.figure(figsize=(10, 5))
plt.plot(channels, std_unadj, "o-", lw=2, label="Unadjusted")
plt.plot(channels, std_adj, "s-", lw=2, label="Bias Corrected")
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Std Dev O-F (K)")
plt.title("O-F Standard Deviation by Channel")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("o_f_stddev_by_chan.png", dpi=300, bbox_inches="tight")
if args.debug: 
    plt.show(block=False)
else: 
    plt.close()

# --- Figure 3: Mean applied bias correction ---
plt.figure(figsize=(10, 5))
plt.bar(channels, mean_bc)
plt.axhline(0, color="k", lw=1)
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean Bias Correction (K)")
plt.title("Mean Applied Bias Correction by Channel")
plt.tight_layout()
plt.savefig("mean_appl_bias_correction_by_chan.png", dpi=300, bbox_inches="tight")
if args.debug: 
    plt.show(block=False)
else: 
    plt.close()

# --- Figure 4: Boxplots of O-F distributions ---
data_unadj = [omb_unadj[chan == ch] for ch in channels]
data_adj = [omb_adj[chan == ch] for ch in channels]

fig, ax = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
ax[0].boxplot(data_unadj, showfliers=False)
ax[0].set_title("Unadjusted O-F")
ax[0].set_ylabel("K")
ax[0].grid(True, alpha=0.3)

ax[1].boxplot(data_adj, showfliers=False)
ax[1].set_title("Bias Corrected O-F")
ax[1].set_ylabel("K")
ax[1].set_xlabel("ATMS Channel")
ax[1].grid(True, alpha=0.3)

ax[1].set_xticks(np.arange(1, len(channels) + 1))
ax[1].set_xticklabels(channel_labels)
plt.tight_layout()
plt.savefig("boxplot_o_f.png", dpi=300, bbox_inches="tight")
if args.debug: 
    plt.show(block=False)
else: 
    plt.close()

# ==========================================
# 5. Output Reporting
# ==========================================
print("\n" + "="*63)
print(
    f"{'Chan':>6} "
    f"{'Mean_Unadj':>12} "
    f"{'Mean_Adj':>12} "
    f"{'Std_Unadj':>12} "
    f"{'Std_Adj':>12} "
    f"{'BiasCorr':>12}"
)
print("-"*63)
for i, ch in enumerate(channels):
    print(
        f"{channel_labels[i]:>6} "
        f"{mean_unadj[i]:12.4f} "
        f"{mean_adj[i]:12.4f} "
        f"{std_unadj[i]:12.4f} "
        f"{std_adj[i]:12.4f} "
        f"{mean_bc[i]:12.4f}"
    )
print("="*63)

if args.debug:
    input("\n[DEBUG] Press Enter to terminate windows and complete script execution...")

print("done plots")
### end
