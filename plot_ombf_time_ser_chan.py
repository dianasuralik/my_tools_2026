#!/usr/bin/env python3
import os
import sys
import glob
from datetime import datetime, timezone

""" un tar files in place first"""

# Force non-interactive backend for HPC/cluster environments if needed
import matplotlib
#matplotlib.use('Agg')

import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt

# 1. Setup path exploration and target tracking
exp_dir = "/work/noaa/da/dsuralik/com/gdas_june2026_jedi"
script_name = os.path.basename(__file__)
target_channel = 14

# Find all matching files across cycle directories
search_pattern = os.path.join(exp_dir, "**", "diag_radiance_atms_n20_*.nc")
nc_files = sorted(glob.glob(search_pattern, recursive=True))
#search_pattern = os.path.join(exp_dir, "gdas.*", "*", "analysis", "atmos", "diag_radiance_atms_n20_*.nc")
#nc_files = sorted(glob.glob(search_pattern))

print("nc files: ")
print(nc_files)

if not nc_files:
    print(f"Error: No diagnostic files found matching path layout in {exp_dir}")
    sys.exit(1)

timeseries_cycles = []
timeseries_mu_raw = []
timeseries_mu_bc = []

# 2. Iterate over historical cycle directories
for nc_file in nc_files:
    # Parse out the cycle label for the X-axis tracking
    fname = os.path.basename(nc_file)
    time_str = fname.split('_')[-1].replace('.nc', '')
    cycle_label = f"{time_str[4:6]}/{time_str[6:8]} {time_str[8:10]}Z" # MM/DD HHZ

    with Dataset(nc_file, 'r') as nc:
        channels = list(nc.groups['MetaData'].variables['sensorChannelNumber'][:])
        if target_channel not in channels:
            continue
        chan_idx = channels.index(target_channel)

        # Extract Bias-Corrected Innovation (OMBG)
        bc_var = nc.groups['ombg'].variables['brightnessTemperature']
        bc_data = bc_var[:, chan_idx].astype(np.float64)
        fill_value = bc_var._FillValue

        # Extract Bias
        bias_data = nc.groups['ObsBias0'].variables['brightnessTemperature'][:, chan_idx].astype(np.float64)

        # Reconstruct Unadjusted
        raw_data = bc_data + bias_data

        # Masking missing flags
        for data in [bc_data, raw_data]:
            invalid_mask = np.isclose(data, fill_value, rtol=1e-02) | np.isnan(data)
            data[invalid_mask] = np.nan

    # Calculate average differences for this specific cycle instance
    with np.errstate(all='ignore'):
        mu_raw = np.nanmean(raw_data)
        mu_bc = np.nanmean(bc_data)

    # Only append if we successfully processed valid numbers
    if not np.isnan(mu_raw) and not np.isnan(mu_bc):
        timeseries_cycles.append(cycle_label)
        timeseries_mu_raw.append(mu_raw)
        timeseries_mu_bc.append(mu_bc)

# 3. Generate the Time Series Plot
plt.figure(figsize=(13, 7))

# Plot running trends across cycles
plt.plot(timeseries_cycles, timeseries_mu_raw, 'o--', color='darkorange', alpha=0.7, linewidth=1.8, label='Unadjusted (OMBG + ObsBias0)')
plt.plot(timeseries_cycles, timeseries_mu_bc, 'o-', color='teal', linewidth=2, label='Bias-Corrected (OMBG)')

# Add reference baseline
plt.axhline(0, color='crimson', linestyle='-', linewidth=1, alpha=0.8)

# Chart adjustments
plt.xlabel('Cycle Date & Time', fontsize=12)
plt.ylabel('Mean Observation - Forecast [K]', fontsize=12)
plt.xticks(rotation=30, ha='right')
plt.grid(True, linestyle=':', alpha=0.5)
plt.legend(loc='best', fontsize=11)

# Combined Header info string matching original template
gen_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
title_text = (
    f"Target Channel: ATMS Channel {target_channel} Timeseries Trend Tracking\n"
    f"Script: {script_name}   |   EXPDIR Files Source: {exp_dir}\n"
    f"Generated On: {gen_time_utc}"
)
plt.title(title_text, fontsize=11, pad=15, fontweight='bold', loc='left')
plt.tight_layout()

# Output save handle
output_plot = f"ombg_trend_channel_{target_channel}.png"
#plt.savefig(output_plot, dpi=200)
plt.show()
input("Enter to close plot...")
print(f"Successfully generated comparison trend plot: {os.getcwd()}/{output_plot}")
