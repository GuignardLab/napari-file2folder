import tifffile
import zarr
from time import sleep

path_to_data = '/home/jvanaret/data/project_egg/raw/3_file.tif'

with tifffile.TiffFile(path_to_data) as tif:
    print(len(tif.series))
    print(len(tif.series[0].pages))

    zarr_store = zarr.open(tif.series[0].aszarr())

    print(zarr_store.shape)

    for i in range(zarr_store.shape[0]):
        elem = zarr_store[i]



#     print('hey')

# with tifffile.TiffFile(path_to_data, is_ome=True) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

# with tifffile.TiffFile(path_to_data, is_ome=False) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

# # with tifffile.TiffFile(path_to_data, is_lsm=True) as tif:
# #     print(len(tif.series))
# #     print(len(tif.series[0].pages))

# with tifffile.TiffFile(path_to_data, is_lsm=False) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

# with tifffile.TiffFile(path_to_data, is_ndpi=True) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

# with tifffile.TiffFile(path_to_data, is_ndpi=False) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

# with tifffile.TiffFile(path_to_data, is_scanimage=True) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

# with tifffile.TiffFile(path_to_data, is_scanimage=False) as tif:
#     print(len(tif.series))
#     print(len(tif.series[0].pages))

