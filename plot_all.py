
# plot all

list_sat_nc_files = [
    "diag_avhrr_metop-b_ges.2021122018.nc4",
    "diag_iasi_metop-c_anl.2021122018.nc4",
    "diag_ssmis_f17_ges.2021122018.nc4",
    "diag_abi_g16_anl.2021122018.nc4",
    "diag_amsua_metop-c_ges.2021122018.nc4",
    "diag_avhrr_n18_anl.2021122018.nc4",
    "diag_iasi_metop-c_ges.2021122018.nc4",
    "diag_ssmis_f18_anl.2021122018.nc4",
    "diag_amsua_n15_anl.2021122018.nc4",
    "diag_avhrr_n18_ges.2021122018.nc4",
    "diag_mhs_metop-b_anl.2021122018.nc4",
    "diag_ssmis_f18_ges.2021122018.nc4",
    "diag_abi_g16_ges.2021122018.nc4",
    "diag_amsua_n15_ges.2021122018.nc4",
    "diag_avhrr_n19_anl.2021122018.nc4",
    "diag_mhs_metop-b_ges.2021122018.nc4",
    "diag_abi_g17_anl.2021122018.nc4",
    "diag_amsua_n18_anl.2021122018.nc4",
    "diag_avhrr_n19_ges.2021122018.nc4",
    "diag_mhs_metop-c_anl.2021122018.nc4",
    "diag_amsua_n18_ges.2021122018.nc4",
    "diag_cris-fsr_n20_anl.2021122018.nc4",
    "diag_mhs_metop-c_ges.2021122018.nc4",
    "diag_abi_g17_ges.2021122018.nc4",
    "diag_amsua_n19_anl.2021122018.nc4",
    "diag_cris-fsr_n20_ges.2021122018.nc4",
    "diag_mhs_n19_anl.2021122018.nc4",
    "diag_ahi_himawari8_anl.2021122018.nc4",
    "diag_amsua_n19_ges.2021122018.nc4",
    "diag_cris-fsr_npp_anl.2021122018.nc4",
    "diag_mhs_n19_ges.2021122018.nc4",
    "diag_seviri_m08_anl.2021122018.nc4",
    "diag_ahi_himawari8_ges.2021122018.nc4",
    "diag_atms_n20_anl.2021122018.nc4",
    "diag_seviri_m08_ges.2021122018.nc4",
    "diag_atms_n20_ges.2021122018.nc4",
    "diag_seviri_m11_anl.2021122018.nc4",
    "diag_amsua_metop-b_anl.2021122018.nc4",
    "diag_atms_npp_anl.2021122018.nc4",
    "diag_seviri_m11_ges.2021122018.nc4",
    "diag_amsua_metop-b_ges.2021122018.nc4",
    "diag_atms_npp_ges.2021122018.nc4",
    "diag_ssmis_f17_anl.2021122018.nc4",
    "diag_amsua_metop-c_anl.2021122018.nc4",
    "diag_avhrr_metop-b_anl.2021122018.nc4",
    "diag_iasi_metop-b_anl.2021122018.nc4",
    "diag_iasi_metop-b_ges.2021122018.nc4",
] 


amsua_avhrr_list = ["diag_amsua_n15_ges.2021122018.nc4",
        "diag_amsua_metop-b_anl.2021122018.nc4",
        "diag_amsua_n15_anl.2021122018.nc4",
        "diag_amsua_metop-b_ges.2021122018.nc4",
        "diag_avhrr_metop-b_anl.2021122018.nc4",
        "diag_avhrr_metop-b_ges.2021122018.nc4"]

import sys
import os
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np


#for file in amsua_avhrr_list:
#    ds = xr.open_dataset(file)
#    obs = ds["Observation"].values
#    print(obs)
#    values, counts = np.unique(obs, return_counts=True)
#    mode = values[np.argmax(counts)]
#    print(obs.min(), obs.max(), mode, obs.mean())

for index, nc_file in enumerate(list_sat_nc_files[::12]):    #open file
    ds = xr.open_dataset(nc_file)

    # creare base for graph title and png title
    base = os.path.splitext(os.path.basename(nc_file))[0]
    out_png = base + ".png"

    # lats & lons
    lat = ds["Latitude"].values
    lon = ds["Longitude"].values
    obs = ds["Observation"].values
    # replace with NAN
    obs = np.where(obs == 1e11, np.nan, obs)

    ch  = ds["Channel_Index"].values
    channels = sorted(set(ch))

    for c in channels[:5]:
        mask = (ch == c)
        print(str(c)+" / "+str(len(channels))+" channels")

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
        plt.title(f"{base} Channel {c}")
   # plt.savefig(out_png, dpi=300, bbox_inches="tight")
        plt.show(block=False)
        plt.savefig(str(c)+"c_"+out_png, dpi=300, bbox_inches="tight")
        print(str(index)+"chan "+str(c)+"/"+str(len(list_sat_nc_files))+" "+out_png)
input("Press Enter to close figures...")
print("done plots")
#
# 
# 
# 
#
