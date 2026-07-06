### 
### 
### 
#plot bias atm 20 py

import xarray as xr
import numpy as np

import matplotlib
#matplotlib.use("Agg")
#matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# Read radiance diagnostic file
filename = "diag_atms_n20_ges.2021122018.nc4"
ds = xr.open_dataset(filename)

# Extract variables
chan = ds["Channel_Index"].values
omb_unadj = ds["Obs_Minus_Forecast_unadjusted"].values
omb_adj = ds["Obs_Minus_Forecast_adjusted"].values

# remove bad fill values
omb_unadj = np.where(np.abs(omb_unadj) > 1e5, np.nan, omb_unadj)
omb_adj   = np.where(np.abs(omb_adj) > 1e5, np.nan, omb_adj)

# Sensor channel numbers (ATMS channels 1-22)
sensor_chan = ds["sensor_chan"].values

# --------------------------------------------------
# Compute channel statistics
# --------------------------------------------------
channels = np.sort(np.unique(chan))

mean_unadj = []
mean_adj = []

std_unadj = []
std_adj = []

mean_bc = []

for ch in channels:
    print(str(ch))
    idx = chan == ch #create a Boolean mask- identifies which observations belong to a particular channel
    vals = omb_unadj[idx]
    print(
        ch,
        vals.min(),
        vals.max(),
        np.ma.count(vals)
    )
    unadj = omb_unadj[idx]
    adj = omb_adj[idx]

    mean_unadj.append(np.nanmean(unadj))
    mean_adj.append(np.nanmean(adj))

    std_unadj.append(np.nanstd(unadj))
    std_adj.append(np.nanstd(adj))

    mean_bc.append(np.nanmean(unadj - adj))

mean_unadj = np.array(mean_unadj)
mean_adj = np.array(mean_adj)

std_unadj = np.array(std_unadj)
std_adj = np.array(std_adj)

mean_bc = np.array(mean_bc)

# --------------------------------------------------
# Map Channel_Index to sensor channel number
# --------------------------------------------------
channel_map = dict(
    zip(np.arange(1, len(sensor_chan) + 1), sensor_chan)
)

channel_labels = [
    str(channel_map.get(ch, ch))
    for ch in channels
]

# --------------------------------------------------
# Figure 1: Mean O-F by channel
# --------------------------------------------------
plt.figure(figsize=(10, 5))

plt.plot(
    channels,
    mean_unadj,
    "o-",
    lw=2,
    label="Unadjusted"
)

plt.plot(
    channels,
    mean_adj,
    "s-",
    lw=2,
    label="Bias Corrected"
)

plt.axhline(0, color="k", lw=1)

plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean O-F (K)")
plt.title("Mean Observation Minus Forecast by Channel")
plt.grid(True, alpha=0.3)
plt.legend()

plt.tight_layout()
plt.show(block=False)
plt.savefig("mean_obs__forecast_by_chan.png", dpi=300, bbox_inches="tight")

# --------------------------------------------------
# Figure 2: Standard deviation by channel
# --------------------------------------------------
plt.figure(figsize=(10, 5))

plt.plot(
    channels,
    std_unadj,
    "o-",
    lw=2,
    label="Unadjusted"
)

plt.plot(
    channels,
    std_adj,
    "s-",
    lw=2,
    label="Bias Corrected"
)

plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Std Dev O-F (K)")
plt.title("O-F Standard Deviation by Channel")
plt.grid(True, alpha=0.3)
plt.legend()

plt.tight_layout()

plt.show(block=False)
plt.savefig("o_f_stddev_by_chan.png", dpi=300, bbox_inches="tight")


# --------------------------------------------------
# Figure 3: Mean applied bias correction
# --------------------------------------------------
plt.figure(figsize=(10, 5))

plt.bar(channels, mean_bc)

plt.axhline(0, color="k", lw=1)

plt.xticks(channels, channel_labels)
plt.xlabel("ATMS Channel")
plt.ylabel("Mean Bias Correction (K)")
plt.title("Mean Applied Bias Correction by Channel")

plt.tight_layout()

plt.show()
plt.savefig("mean_appl_bias_correction_by_ chan.png", dpi=300, bbox_inches="tight")


# --------------------------------------------------
# Figure 4: Boxplots of O-F distributions
# --------------------------------------------------
data_unadj = [
    omb_unadj[chan == ch]
    for ch in channels
]

data_adj = [
    omb_adj[chan == ch]
    for ch in channels
]

fig, ax = plt.subplots(
    2,
    1,
    figsize=(14, 8),
    sharex=True
)

ax[0].boxplot(
    data_unadj,
    showfliers=False
)
ax[0].set_title("Unadjusted O-F")
ax[0].set_ylabel("K")
ax[0].grid(True, alpha=0.3)

ax[1].boxplot(
    data_adj,
    showfliers=False
)
ax[1].set_title("Bias Corrected O-F")
ax[1].set_ylabel("K")
ax[1].set_xlabel("ATMS Channel")
ax[1].grid(True, alpha=0.3)

ax[1].set_xticks(np.arange(1, len(channels) + 1))
ax[1].set_xticklabels(channel_labels)

plt.tight_layout()

plt.show(block=False)
plt.savefig("boxplot_o_f.png", dpi=300, bbox_inches="tight")



# --------------------------------------------------
# Print summary table
# --------------------------------------------------
print(
    f"{'Chan':>6} "
    f"{'Mean_Unadj':>12} "
    f"{'Mean_Adj':>12} "
    f"{'Std_Unadj':>12} "
    f"{'Std_Adj':>12} "
    f"{'BiasCorr':>12}"
)

for i, ch in enumerate(channels):
    print(
        f"{channel_labels[i]:>6} "
        f"{mean_unadj[i]:12.4f} "
        f"{mean_adj[i]:12.4f} "
        f"{std_unadj[i]:12.4f} "
        f"{std_adj[i]:12.4f} "
        f"{mean_bc[i]:12.4f}"
    )

# --------------------------------------------------
# Show all plots
# --------------------------------------------------
input("Enter to close...")
#input("Press Enter to close figures...")
print("done plots")

