#!/usr/bin/env python3
import os
import sys

# Force non-interactive backend for HPC/cluster environments
import matplotlib
#matplotlib.use('Agg')

import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# 1. Setup file and metadata information
nc_file = "diag_radiance_atms_n20_2026061006.nc"
script_name = os.path.basename(__file__)

try:
    time_str = nc_file.split('_')[-1].replace('.nc', '')
    cycle_time = f"{time_str[0:4]}-{time_str[4:6]}-{time_str[6:8]} {time_str[8:10]}Z"
except Exception:
    cycle_time = "2026-06-10 06Z"

# 2. Read data from NetCDF
if not os.path.exists(nc_file):
    print(f"Error: File '{nc_file}' not found.")
    sys.exit(1)

with Dataset(nc_file, 'r') as nc:
    # Fetch channel numbers
    channels = nc.groups['MetaData'].variables['sensorChannelNumber'][:]

    # Extract Bias-Corrected Innovation (OMBG)
    bc_var = nc.groups['ombg'].variables['brightnessTemperature']
    bc_data = bc_var[:].astype(np.float64)
    fill_value = bc_var._FillValue

    # Extract the total bias calculated by GSI/JEDI Variational Bias Correction (VarBC)
    bias_data = nc.groups['ObsBias0'].variables['brightnessTemperature'][:].astype(np.float64)

    # Reconstruct the Unadjusted (Raw) Innovation
    # Unadjusted = (O - H(x)_bc) + Bias = O - H(x)_raw
    raw_data = bc_data + bias_data

    # Robust masking of fill values across arrays
    for data in [bc_data, raw_data]:
        invalid_mask = np.isclose(data, fill_value, rtol=1e-02) | np.isnan(data)
        data[invalid_mask] = np.nan

# 3. Calculate statistics per channel (ignoring missing values)
with np.errstate(all='ignore'):
    mu_raw = np.nanmean(raw_data, axis=0)
    std_raw = np.nanstd(raw_data, axis=0)

    mu_bc = np.nanmean(bc_data, axis=0)
    std_bc = np.nanstd(bc_data, axis=0)
"""
# Replace any lingering bad math calculations with zero to keep matplotlib happy
mu_raw = np.where(np.isnan(mu_raw) | np.isinf(mu_raw), 0.0, mu_raw)
std_raw = np.where(np.isnan(std_raw) | np.isinf(std_raw), 0.0, std_raw)
mu_bc = np.where(np.isnan(mu_bc) | np.isinf(mu_bc), 0.0, mu_bc)
std_bc = np.where(np.isnan(std_bc) | np.isinf(std_bc), 0.0, std_bc)
"""
# 4. Generate the plot
plt.figure(figsize=(12, 7))
# Plot Unadjusted
plt.errorbar(channels, mu_raw, yerr=std_raw, fmt='o--', color='darkorange',
             alpha=0.6, capsize=4, elinewidth=1.5, label='Unadjusted (OMBG + ObsBias0)')
# Plot Bias-Corrected
plt.errorbar(channels, mu_bc, yerr=std_bc, fmt='o-', color='teal',
             capsize=4, elinewidth=1.5, label='Bias-Corrected (OMBG)')


# Capture the exact current date and time of execution
#gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
gen_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# Combined Title format matching requested information layout
title_text = (
    f"File: {nc_file}\n"
    f"Script: {script_name}   |   Cycle: {cycle_time}\n"
    f"Generated On: {gen_time_utc}"
)

# Add a reference baseline at 0
plt.axhline(0, color='crimson', linestyle='-', linewidth=1, alpha=0.8)

# Chart labels and configurations
plt.xlabel('Channel Number', fontsize=12)
plt.ylabel('Observation - Forecast [K]', fontsize=12)
plt.xticks(channels)
plt.grid(True, linestyle=':', alpha=0.5)
plt.legend(loc='best', fontsize=11)

# Combined Title format matching requested information layout
#ititle_text = f"File: {nc_file}\nScript: {script_name}   |   Cycle: {cycle_time}"
plt.title(title_text, fontsize=11, pad=15, fontweight='bold', loc='left')
plt.tight_layout()
# Save out to active file-system
output_plot = "ombg_innovation_comparison.png"
#plt.savefig(output_plot, dpi=200)
plt.show()
input("Enter to close plot...")
print(f"Successfully generated comparison plot: {os.getcwd()}/{output_plot}")
