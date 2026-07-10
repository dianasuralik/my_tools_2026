import os
import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

#matplotlib.use('Agg') # Enforces headless rendering without a GUI display

# ==========================================
# 1. Command-Line Argument Parsing
# ==========================================
parser = argparse.ArgumentParser(
    description="Diagnostic validation tool for IODA-v2 style JEDI/GSI radiance diagnostics."
)
parser.add_argument(
    "filepath", 
    type=str, 
    help="Path to the JEDI/GSI radiance diagnostics NetCDF file."
)
parser.add_argument(
    "-d", "--debug", 
    action="store_true", 
    help="Enable verbose debugging prints."
)
args = parser.parse_args()
filename = args.filepath

# ==========================================
# 2. Data Extraction & Group Handling
# ==========================================
# ==========================================
# 2. Data Extraction & Group Handling
# ==========================================
print(f"[INFO] Ingesting IODA-v2 file: {filename}")
try:
    # Open required groups separately
    ds_root = xr.open_dataset(filename)
    ds_meta = xr.open_dataset(filename, group="MetaData")
    ds_obs  = xr.open_dataset(filename, group="ObsValue")
    ds_ombg = xr.open_dataset(filename, group="ombg")
    ds_hofx = xr.open_dataset(filename, group="GsiHofXBcGes")
except Exception as e:
    print(f"[ERROR] Failed to open dataset groups: {e}")
    exit(1)

# Extract core dimensions/variables
channels = ds_root["Channel"].values
sensor_chan = ds_meta["sensorChannelNumber"].values

# 1. Extract raw values
omb_unadj = ds_ombg["brightnessTemperature"].values
obs_val   = ds_obs["brightnessTemperature"].values
hofx_bc   = ds_hofx["brightnessTemperature"].values

omb_adj = obs_val - hofx_bc

print(" omb_adj (Cleaned) :: ")
print(omb_adj)


# ==========================================
# 3. Compute Channel Statistics
# ==========================================
mean_unadj, mean_adj = [], []
std_unadj, std_adj = [], []
mean_bc = []

# Since variables are structured as (Location, Channel), we loop over channel indices
for idx, ch in enumerate(channels):
    unadj = omb_unadj[:, idx]
    adj = omb_adj[:, idx]
    
    # Calculate the applied bias correction across locations
    bc_applied = unadj - adj

    if args.debug:
        valid_cnt = np.sum(~np.isnan(unadj))
        print(f"[DEBUG] Chan {ch} counts: Valid={valid_cnt}, MinUnadj={np.nanmin(unadj):.2f}, MaxUnadj={np.nanmax(unadj):.2f}")

    mean_unadj.append(np.nanmean(unadj))
    mean_adj.append(np.nanmean(adj))
    std_unadj.append(np.nanstd(unadj))
    std_adj.append(np.nanstd(adj))
    mean_bc.append(np.nanmean(bc_applied))
    
# Convert to arrays for clean handling
print(mean_unadj)
mean_unadj = np.array(mean_unadj)
print("  :")
print(mean_unadj)
print("  ::")
mean_adj = np.array(mean_adj)
print(mean_adj)
std_unadj = np.array(std_unadj)
std_adj = np.array(std_adj)
mean_bc = np.array(mean_bc)

channel_labels = [str(int(ch)) for ch in sensor_chan]

# ==========================================
# 4. Visualization Routines
# ==========================================
print("[INFO] Generating diagnostic metric charts...")

# --- Figure 1: Mean O-F by channel ---
plt.figure(figsize=(10, 5))
plt.plot(channels, mean_unadj, "o-", lw=2, label="Unadjusted (OMBG)")
#plt.plot(channels, mean_adj, "s-", lw=2, label="Bias Corrected")
plt.axhline(0, color="k", lw=1)
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean O-F (K)")
plt.title("Mean Observation Minus Forecast by Channel")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
#plt.savefig("mean_obs__forecast_by_chan.png", dpi=300, bbox_inches="tight")
plt.show()
input("Enter to end plot 1...")

# --- Figure 2: Standard deviation by channel ---
plt.figure(figsize=(10, 5))
plt.plot(channels, std_unadj, "o-", lw=2, label="Unadjusted (OMBG)")
plt.plot(channels, std_adj, "s-", lw=2, label="Bias Corrected")
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Std Dev O-F (K)")
plt.title("O-F Standard Deviation by Channel")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
#plt.savefig("o_f_stddev_by_chan.png", dpi=300, bbox_inches="tight")
plt.show()
input("Enter to end plot 2...")

# --- Figure 3: Mean applied bias correction ---
plt.figure(figsize=(10, 5))
plt.bar(channels, mean_bc, color="purple", alpha=0.7, edgecolor="k")
plt.axhline(0, color="k", lw=1)
plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean Bias Correction (K)")
plt.title("Mean Applied Bias Correction by Channel")
plt.grid(True, alpha=0.3)
plt.tight_layout()
#plt.savefig("mean_appl_bias_correction_by_chan.png", dpi=300, bbox_inches="tight")
plt.show()
input("Enter to end plot 3...")

# --- Figure 4: Boxplots of O-F distributions ---
data_unadj = [omb_unadj[:, i][~np.isnan(omb_unadj[:, i])] for i in range(len(channels))]
data_adj = [omb_adj[:, i][~np.isnan(omb_adj[:, i])] for i in range(len(channels))]

fig, ax = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
ax[0].boxplot(data_unadj, showfliers=False)
ax[0].set_title("Unadjusted O-F (OMBG)")
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
#plt.savefig("boxplot_o_f.png", dpi=300, bbox_inches="tight")
plt.show()
input("Enter to end plot 4...")

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
