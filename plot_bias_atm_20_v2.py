"""
 * file plot_bias_atm20.py
 * Diagnostic tool for monitoring and evaluating satellite radiance VarBC.
 * This version handles the GSI-converted IODA observation diagnostics file structure.
 *
 * @usage python plot_bias_atm20.py ./diag_radiance_atms_n20_2026061112.nc [--debug]
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
    # 1. Grab coordinates (Channel) from the root
    ds_root = xr.open_dataset(filename)
    
    # 2. Grab unadjusted OMF (ombg)
    ds_ombg = xr.open_dataset(filename, group="ombg")
    
    # 3. Grab HofX components to determine the adjusted bias residual
    ds_hofx_bc = xr.open_dataset(filename, group="GsiHofXBcGes")  # Background with Bias Correction
    ds_hofx_raw = xr.open_dataset(filename, group="hofx0")        # Raw background forecast
    
except Exception as e:
    print(f"[ERROR] Failed to open dataset subgroups: {e}")
    exit(1)

if args.debug:
    print("[DEBUG] Unpacking JEDI observation metrics...")

# Extract Channels (Coordinates are float/int 1 to 22)
channels = ds_root["Channel"].values

# Dynamically find the data variable name inside the groups (typically 'brightness_temperature')
var_name = list(ds_ombg.data_vars)[0]
if args.debug:
    print(f"[DEBUG] Target data variable identified as: '{var_name}'")

# Load data matrices (Shape: Location x Channel)
omb_unadj_raw = ds_ombg[var_name].values

# Calculate Adjusted OMF: Unadjusted OMF - Total Bias Correction applied
# Total Bias Correction = HofX_BC - HofX_Raw
bias_correction = ds_hofx_bc[var_name].values - ds_hofx_raw[var_name].values
omb_adj_raw = omb_unadj_raw - bias_correction

# Clean out bad fill values (> 1e5) safely using NaNs
if args.debug:
    print("[DEBUG] Dropping missing entries and extreme fill values (> 1e5)...")
omb_unadj_raw = np.where(np.abs(omb_unadj_raw) > 1e5, np.nan, omb_unadj_raw)
omb_adj_raw   = np.where(np.abs(omb_adj_raw) > 1e5, np.nan, omb_adj_raw)
bias_correction = np.where(np.abs(bias_correction) > 1e5, np.nan, bias_correction)

# ==========================================
# 3. Compute Channel Statistics
# ==========================================
mean_unadj, mean_adj = [], []
std_unadj, std_adj = [], []
mean_bc = []

# Data structured as (Location, Channel) -> Loop directly through indices of channels
for i, ch in enumerate(channels):
    # Slice the matrix along the current channel column
    unadj = omb_unadj_raw[:, i]
    adj = omb_adj_raw[:, i]
    bc = bias_correction[:, i]

    valid_count = np.count_nonzero(~np.isnan(unadj))
    if args.debug:
        print(f"[DEBUG] Chan {int(ch)} counts: Valid={valid_count}, Min={np.nanmin(unadj):.2f}, Max={np.nanmax(unadj):.2f}")

    mean_unadj.append(np.nanmean(unadj))
    mean_adj.append(np.nanmean(adj))
    std_unadj.append(np.nanstd(unadj))
    std_adj.append(np.nanstd(adj))
    mean_bc.append(np.nanmean(bc))

# Convert to tracking arrays
mean_unadj = np.array(mean_unadj)
mean_adj = np.array(mean_adj)
std_unadj = np.array(std_unadj)
std_adj = np.array(std_adj)
mean_bc = np.array(mean_bc)

channel_labels = [str(int(ch)) for ch in channels]

# ==========================================
# 4. Visualization Routines
# ==========================================
print("[INFO] Generating diagnostic metric charts...")

# --- Figure 1: Mean O-F by channel ---
plt.figure(figsize=(10, 5))
plt.plot(channels, mean_unadj, "o-", lw=2, label="Unadjusted (OMF)")
plt.plot(channels, mean_adj, "s-", lw=2, label="Bias Corrected")
plt.axhline(0, color="k", lw=1)
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean Residual (K)")
plt.title("JEDI Mean Observation Minus Forecast by Channel")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("mean_obs__forecast_by_chan.png", dpi=300, bbox_inches="tight")

# --- Figure 2: Standard deviation by channel ---
plt.figure(figsize=(10, 5))
plt.plot(channels, std_unadj, "o-", lw=2, label="Unadjusted")
plt.plot(channels, std_adj, "s-", lw=2, label="Bias Corrected")
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Std Dev O-F (K)")
plt.title("JEDI O-F Standard Deviation by Channel")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("o_f_stddev_by_chan.png", dpi=300, bbox_inches="tight")

# --- Figure 3: Mean applied bias correction ---
plt.figure(figsize=(10, 5))
plt.bar(channels, mean_bc, color='teal', alpha=0.7)
plt.axhline(0, color="k", lw=1)
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean Bias Correction (K)")
plt.title("JEDI Mean Applied Bias Correction by Channel")
plt.tight_layout()
input("Enter to save figure")
plt.savefig("mean_appl_bias_correction_by_chan.png", dpi=300, bbox_inches="tight")

# --- Figure 4: Boxplots of O-F distributions ---
data_unadj = [omb_unadj_raw[:, i][~np.isnan(omb_unadj_raw[:, i])] for i in range(len(channels))]
data_adj = [omb_adj_raw[:, i][~np.isnan(omb_adj_raw[:, i])] for i in range(len(channels))]

fig, ax = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
ax[0].boxplot(data_unadj, showfliers=False)
ax[0].set_title("Unadjusted O-F")
ax[0].set_ylabel("K")
ax[0].grid(True, alpha=0.3)

ax[1].boxplot(data_adj, showfliers=False)
ax[1].set_title("JEDI Bias Corrected O-F")
ax[1].set_ylabel("K")
ax[1].set_xlabel("ATMS Channel")
ax[1].grid(True, alpha=0.3)

ax[1].set_xticks(np.arange(1, len(channels) + 1))
ax[1].set_xticklabels(channel_labels)
plt.tight_layout()
plt.savefig("boxplot_o_f.png", dpi=300, bbox_inches="tight")

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

print("done plots")
