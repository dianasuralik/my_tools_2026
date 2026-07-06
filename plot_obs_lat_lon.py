#
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

plt.figure(figsize=(10,6))
# scatterplot
sc = plt.scatter(lon, lat, c=obs, s=1, cmap="turbo")

plt.colorbar(sc, label="Observation")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title(base)
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.show()

## end
