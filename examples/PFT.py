
from data_loader import Coord, Time
from data_loader.netcdf import DataNetCDF
import data_loader.constructor as dlc
import data_loader.scan_library as scanlib


root = "/home/clement/Documents/Stage/Data/Data_SOM/Data/8days/"


# Coordinates
time = Time("time", None,
            unit="hours since 1970-01-01 00:00:00",
            name_alt="",
            fullname="")
lat = Coord("lat", None,
            unit="",
            name_alt="latitude",
            fullname="Latitude")
lon = Coord("lon", None,
            unit="",
            name_alt="longitude",
            fullname="Longitude")
coords = [time, lat, lon]


# Variables
vic = dlc.VIConstructor()

name = "Chla_OC5"
infos = {"fullname": "Chlorophyll-a OC5",
         "unit": "mg.m-3",
         "ncname": "CHL-OC5_mean",
         "vmin": 0.,
         "vmax": 3.}
vic.add_var(name, infos)

name = "SST"
infos = {"fullname": "Sea Surface Temperature",
         "unit": "",
         "ncname": "sst",
         "vmin": -2.,
         "vmax": 30.}
vic.add_var(name, infos)

name = "dtom"
infos = {"fullname": "Diatoms",
         "unit": "",
         "vmin": 0.,
         "vmax": 3.}
vic.add_var(name, infos)

vi = vic.make_vi()


# Filegroups
fgc = dlc.FGConstructor(root, coords, vi)

contains = ["SST"]
coords_fg = [[lat, "in"], [lon, "in"], [time, "out"]]
pregex = r"%(dir)/A%(time:Y)%(time:doy)%(time:Y:dummy)%(time:doy:dummy)%(suffix)"
replacements = {"dir": "SST",
                "suffix": r"\.L3m_8D_SST_sst_4km\.nc"}

fgc.add_fg(contains, coords_fg)
fgc.set_fg_regex(pregex, replacements)
fgc.set_scan_filename(scanlib.get_date_from_matches)
fgc.set_scan_in_file(scanlib.scan_in_file_nc)

contains = ["dtom"]
coords_fg = [[lat, "null"], [lon, "null"], [time, "out"]]
pregex = r"%(dir)/%(prefix)_%(time:Y)%(time:mm)%(time:dd)\.nc"
replacements = {"dir": "PFT/dtom",
                "prefix": "dtom"}

fgc.add_fg(contains, coords_fg)
fgc.set_fg_regex(pregex, replacements)
fgc.set_scan_filename(scanlib.get_date_from_matches)

filegroups = fgc.make_filegroups()

dt = DataNetCDF(root, filegroups, vi, *coords)
