#!/usr/bin/env python3
import os
import sys
import glob
from datetime import datetime, timezone

# Force non-interactive backend for HPC/cluster environments
import matplotlib
#matplotlib.use('Agg')

import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt

# 1. Setup path exploration
exp_dir = "/work/noaa/da/dsuralik/com/gdas_june2026_jedi"
script_name = os.path.basename(__file__)

# Find all extracted ATMS NetCDF diagnostic files using recursive search
search_pattern = os.path.join(exp_dir, "**", "diag_radiance_atms_n20_*.nc")
nc_files = sorted(glob.glob(search_pattern, recursive=True))

if not nc_files:
    print(f"Error: No extracted NetCDF files found in {exp_dir}")
    sys.exit(1)

print(f"Found {len(nc_files)} files to process for all channels.")

# Dictionary to hold timeline data per channel
# Structure: { channel_number: { 'cycles': [], 'mu_raw': [], 'mu_bc': [] } }
channel_data_store = {}

# 2. Iterate over historical cycle files to gather data
for nc_file in nc_files:
    fname = os.path.basename(nc_file)
    time_str = fname.split('_')[-1].replace('.nc', '')
    cycle_label = f"{time_str[4:6]}/{time_str[6:8]} {time_str[8:10]}Z"  # MM/DD HHZ

    with Dataset(nc_file, 'r') as nc:
        channels = nc.groups['MetaData'].variables['sensorChannelNumber'][:]
        
        # Load the full dataset matrices (Location, Channel)
        bc_var = nc.groups['ombg'].variables['brightnessTemperature']
        bc_full = bc_var[:].astype(np.float64)
        fill_value = bc_var._FillValue
        
        bias_full = nc.groups['ObsBias0'].variables['brightnessTemperature'][:].astype(np.float64)
        raw_full = bc_full + bias_full

        # Apply robust masking across entire matrices
        for matrix in [bc_full, raw_full]:
            invalid_mask = np.isclose(matrix, fill_value, rtol=1e-02) | np.isnan(matrix)
            matrix[invalid_mask] = np.nan

        # Calculate averages for each channel in this file
        with np.errstate(all='ignore'):
            mu_raw_all = np.nanmean(raw_full, axis=0)
            mu_bc_all = np.nanmean(bc_full, axis=0)

        # Map channel indexes back to their actual channel numbers
        for idx, chan in enumerate(channels):
            chan = int(chan)
            if chan not in channel_data_store:
                channel_data_store[chan] = {'cycles': [], 'mu_raw': [], 'mu_bc': []}
            
            # Save stats if they are valid numbers
            if not np.isnan(mu_raw_all[idx]) and not np.isnan(mu_bc_all[idx]):
                channel_data_store[chan]['cycles'].append(cycle_label)
                channel_data_store[chan]['mu_raw'].append(mu_raw_all[idx])
                channel_data_store[chan]['mu_bc'].append(mu_bc_all[idx])

# 3. Generate a comprehensive Multi-Panel Grid Plot
# 22 channels look best mapped onto a 6x4 grid matrix (24 slots total)
sorted_channels = sorted(channel_data_store.keys())
fig, axes = plt.subplots(6, 4, figsize=(20, 24), sharex=True)
axes = axes.flatten()  # Flatten matrix to 1D to easily iterate

for idx, chan in enumerate(sorted_channels):
    ax = axes[idx]
    c_data = channel_data_store[chan]
    
    if not c_data['cycles']:
        ax.text(0.5, 0.5, 'No Valid Data', transform=ax.transAxes, ha='center')
        ax.set_title(f"Channel {chan}")
        continue

    # Plot trends inside sub-panel
    ax.plot(c_data['cycles'], c_data['mu_raw'], 'o--', color='darkorange', alpha=0.7, label='Unadjusted' if idx == 0 else "")
    ax.plot(c_data['cycles'], c_data['mu_bc'], 'o-', color='teal', label='Bias-Corrected' if idx == 0 else "")
    ax.axhline(0, color='crimson', linestyle='-', linewidth=0.8, alpha=0.7)
    
    # Subplot formatting
    ax.set_title(f"Channel {chan}", fontsize=11, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.tick_params(axis='x', rotation=45)

# Hide the last 2 empty subplots in the 6x4 layout since ATMS has 22 channels
for empty_idx in range(len(sorted_channels), len(axes)):
    fig.delaxes(axes[empty_idx])

# Universal Figure adjustments
fig.text(0.5, 0.01, 'Cycle Date & Time', ha='center', fontsize=14)
fig.text(0.01, 0.5, 'Mean Observation - Forecast [K]', va='center', rotation='vertical', fontsize=14)

# Global configuration header layout
gen_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
title_text = (
    f"All Channels Time-Series Innovation Trends Tracking\n"
    f"Script: {script_name}   |   Source Directory: {exp_dir}\n"
    f"Generated On: {gen_time_utc}"
)
plt.suptitle(title_text, fontsize=16, fontweight='bold', x=0.02, ha='left', y=0.98)

# Place unified legend on the first subplot
axes[0].legend(loc='best', fontsize=9)

plt.tight_layout(rect=[0.02, 0.02, 1, 0.95])

plt.show()
input("Enter to close plots...")
# Save out matrix summary graphic
output_plot = "ombg_trends_all_channels.png"
#plt.savefig(output_plot, dpi=150)
print(f"Successfully generated matrix trend plot for all channels: {os.getcwd()}/{output_plot}")
### end
