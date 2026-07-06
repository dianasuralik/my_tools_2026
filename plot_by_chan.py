


## plot by chan

import xarray as xr
import matplotlib.pyplot as plt

ds = xr.open_dataset("diag_abi_g16_anl.2021122018.nc4")

lat = ds["Latitude"].values
lon = ds["Longitude"].values
ch  = ds["Channel_Index"].values

# variable to plot
obs = ds["Observation"].values

# unique channels
channels = sorted(set(ch))

for c in channels:
    mask = (ch == c)
    print(str(c)+" / ")

    plt.figure(figsize=(10,5))
    plt.scatter(
        lon[mask],
        lat[mask],
        c=obs[mask],
        s=2,
        cmap="turbo"
    )
    plt.colorbar(label="Observation")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(f"Channel {c}")
   # plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.show(block=False)
input("Press Enter to close figures...")
print("done plots")

### end

