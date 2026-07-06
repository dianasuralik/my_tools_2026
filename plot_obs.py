
## plot_obs.py

import sys
import os
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

nc_file = sys.argv[1]   # input from command line

# open file
ds = xr.open_dataset(nc_file)  #("diag_abi_g16_anl.2021122018.nc4")

# creare base for graph title and png title
base = os.path.splitext(os.path.basename(nc_file))[0]
out_png = base + ".png"

# lats & lons
lat = ds["Latitude"].values
lon = ds["Longitude"].values
obs = ds["Observation"].values

obs = np.where(obs == 1e11, np.nan, obs)
#remove NAN
valid_obs = obs[~np.isnan(obs)]



#bs_scan_ang = BC_Scan_Angle
#bs_cloud_liq_wat = BC_Cloud_Liquid_Water
#bc_lapse_rt_sq = BC_Lapse_Rate_Squared
#bc_lapse_rt = BC_Lapse_Rate

bc_cos_lat_node = ds["BC_Cosine_Latitude_times_Node"]

bc_sin_lat = ds["BC_Sine_Latitude"].values

bc_emiss = ds["BC_Emissivity"].values
bc_fix_scan_pos = ds["BC_Fixed_Scan_Position"].values
print(bc_emiss)



plt.figure(figsize=(10,6))
# scatterplot
sc = plt.scatter(lon, lat, c=bc_emiss, s=1, cmap="turbo")

plt.colorbar(sc, label="BC_Emissivity")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title(base)
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.show()

## end

