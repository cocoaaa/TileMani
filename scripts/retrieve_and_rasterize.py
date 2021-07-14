#!/usr/bin/env python
"""
# Problem Description:
  Given a tile index of (x,y,z) of size 256x256,
    1. Find out (lat_deg, lng_deg) and the extent covered by the maptile (ie. the radius in meters)
    2. Grab the road network (and other entities, like building boundaries or types) from OSM -- use OSMnx -- in the area covered by the map tile
    3. Compute the traditional geospatial features (ie. measures of spatail complexity from Boeing 2016)
    4. Concatenate the features into a vector -- which will be used as 'geospatial feature vector', the counterpart of BiVAE's content code.


# Usage:

# Examples:
python retrieve_and_rasterize.py -c la --out_dir_root='.' --records_dir_root='.'
nohup python retrieve_and_rasterize.py -c la  &>  la.out &
nohup python retrieve_and_rasterize.py -c shanghai  &>  shanghai.out &
nohup python retrieve_and_rasterize.py -c seoul  &>  seoul.out &
nohup python retrieve_and_rasterize.py -c rome  &>  rome.out &
nohup python retrieve_and_rasterize.py -c paris  &>  paris.out &
nohup python retrieve_and_rasterize.py -c montreal  &>  montreal.out &
nohup python retrieve_and_rasterize.py -c manhattan  &>  manhattan.out &
nohup python retrieve_and_rasterize.py -c chicago  &>  chicago.out &
nohup python retrieve_and_rasterize.py -c charlotte  &>  charlotte.out &
nohup python retrieve_and_rasterize.py -c boston  &>  boston.out &
nohup python retrieve_and_rasterize.py -c berlin  &>  berlin.out &
nohup python retrieve_and_rasterize.py -c amsterdam  &>  amsterdam.out &
nohup python retrieve_and_rasterize.py -c vegas  &>  vegas.out &


# nohup python retrieve_and_rasterize.py -c london  &>  london.out &


# styles =['StamenTonerBackground','OSMDefault', 'CartoVoyagerNoLabels']#'StamenWatercolor']#, 'StamenTonerLines']
nohup python retrieve_and_rasterize.py -c la -s StamenTonerBackground &>  la.out &
nohup python retrieve_and_rasterize.py -c shanghai -s StamenTonerBackground &>  shanghai.out &
nohup python retrieve_and_rasterize.py -c seoul -s StamenTonerBackground &>  seoul.out &
nohup python retrieve_and_rasterize.py -c rome  -s StamenTonerBackground&>  rome.out &
nohup python retrieve_and_rasterize.py -c paris -s StamenTonerBackground &>  paris.out &
nohup python retrieve_and_rasterize.py -c montreal -s StamenTonerBackground &>  montreal.out &
nohup python retrieve_and_rasterize.py -c manhattan -s StamenTonerBackground &>  manhattan.out &
nohup python retrieve_and_rasterize.py -c chicago -s StamenTonerBackground &>  chicago.out &
nohup python retrieve_and_rasterize.py -c charlotte -s StamenTonerBackground &>  charlotte.out &
nohup python retrieve_and_rasterize.py -c boston -s StamenTonerBackground &>  boston.out &
nohup python retrieve_and_rasterize.py -c berlin -s StamenTonerBackground &>  berlin.out &
nohup python retrieve_and_rasterize.py -c amsterdam -s StamenTonerBackground &>  amsterdam.out &
nohup python retrieve_and_rasterize.py -c vegas -s StamenTonerBackground &>  vegas.out &



"""

# ## Load libraries
import argparse
import os, sys
import re
import math
from datetime import datetime
from collections import OrderedDict, defaultdict
import time
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional, Iterable, Mapping, Union, Callable, TypeVar
from networkx.classes.graph import Graph

sys.dont_write_bytecode = True

import pandas as pd
import geopandas as gpd
import joblib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.gridspec import GridSpec
import matplotlib

matplotlib.use('Agg')

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import matplotlib.pyplot as plt

# %matplotlib inline
ox.config(log_console=False, use_cache=True)
# ox.__version__


# ## Set Path
# 1. Add project root and src folders to `sys.path`
# 2. Set DATA_ROOT to `maptile_v2` folder
this_nb_path = Path(os.getcwd())
# ROOT = this_nb_path.parent.parent
ROOT = Path('/data/hayley-old/TileGenerator/')
SRC = ROOT / 'src'

DATA_ROOT = Path("/data/hayley-old/maptiles_v2/")
paths2add = [this_nb_path, ROOT]

print("Project root: ", str(ROOT))
print('Src folder: ', str(SRC))
print("This nb path: ", str(this_nb_path))
for p in paths2add:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
        print(f"\n{str(p)} added to the path.")

# Import helper functions
from src.utils.np import info, get_fig, show_npimgs
from src.utils.geo import getTileFromGeo, getGeoFromTile, getTileExtent, parse_maptile_fp
from src.utils.misc import mkdir, write_record

from src.retrieve.retriever import get_road_graph_and_bbox, get_geoms

from src.rasterize.rasterizer import plot_figure_ground, rasterize_road_graph, rasterize_road_and_bldg
from src.rasterize.rasterizer import single_rasterize_road_graph, single_rasterize_road_and_bldg

from src.compute.features import get_total_area, get_road_area, compute_road_network_stats, \
    get_road_figure_and_nway_proportion


# ### Process each cities' maptiles
# - Rasterize G_r (road networks)
# - Rasterize bldg geoms
# - Rasterize both road and bldg to the same image
#
# - Save road network graph
# - Save bldg geometry info as geojson
#
# - while collecting: {x,y,z,lat,lng,radius, road_retreival_status} and road network stats
#

# Parameters for the script
# city = 'paris'
# style = 'StamenTonerLines'
# zoom = '14'
# network_type = 'drive_service'

# bgcolors = ['k', 'r', 'g', 'b', 'y']
# edge_colors = ['cyan']
# bldg_colors = ['silver']
# lw_factors = [0.5]
# save = True
# dpi = 50
# figsize = (7,7)
# show = False #True
# show_only_once = False
# verbose = False #True


def retrieve_and_rasterize_locs_in_a_folder(
        city: str,
        style: str,
        zoom: str,
        network_type='drive_service',
        bgcolors=['k', 'r', 'g', 'b', 'y'],
        edge_colors=['cyan'],
        bldg_colors=['silver'],
        lw_factors=[0.5],
        save=True,
        dpi=50,
        figsize=(7, 7),
        show=False,  # True,
        show_only_once=False,
        verbose=False,  # True,
        out_dir_root=Path('./temp/images'),
        records_dir_root=Path('./temp/records'),
) -> List[Dict]:
    mkdir(out_dir_root)
    mkdir(records_dir_root)

    img_dir = DATA_ROOT / city / style / zoom
    if not img_dir.exists():
        raise ValueError(f"{img_dir} doesn't exist. Check the spelling and upper/lower case of city, style, zoom")
    if verbose:
        print(f"Image_dir: ", img_dir)
    #     breakpoint() #debug

    # list of each record of location (which is a dict)
    records = []
    for i, img_fp in enumerate(img_dir.iterdir()):
        if not img_fp.is_file(): continue
        record = parse_maptile_fp(img_fp)
        record['city'] = city
        record['style'] = style

        tileXYZ = (record['x'], record['y'], record['z'])
        if verbose:
            print("=" * 10)
            print(f"Processing {city} -- {tileXYZ}")

        # Retrieve road graph and bldg geoms
        G_r, bbox = get_road_graph_and_bbox(tileXYZ, network_type)
        gdf_b = get_geoms(tileXYZ, tag={'building': True})

        # Rasterize road graph with *my* plot_figure_ground (not ox.plot_figure_ground)
        rasterize_road_and_bldg(
            G_r,
            gdf_b,
            tileXYZ,
            bbox,
            bgcolors,
            edge_colors,
            bldg_colors,
            lw_factors=lw_factors,
            save=save,
            out_dir_root=out_dir_root / city,
            verbose=verbose,
            show=show,
            show_only_once=show_only_once,
            figsize=figsize,
            dpi=dpi)
        # Raster in grayscale (bgcolor='w','edge_color='k', bldg_color='silver')
        single_rasterize_road_and_bldg(
            G_r,
            gdf_b,
            tileXYZ,
            bbox=bbox,
            lw_factor=lw_factors[0],
            save=save,
            out_dir_root=out_dir_root / city,
            verbose=verbose,
            show=show,
            figsize=figsize,
            dpi=dpi
        )
        # Save retrieval results
        record['retrieved_road'] = G_r is not None
        record['retrieved_bldg'] = gdf_b is not None

        filename = f"{record['x']}_{record['y']}_{record['z']}"
        if save:
            # Save the graph (of roads) as Graphml file
            filename = f"{record['x']}_{record['y']}_{record['z']}"
            fp = out_dir_root / city / 'RoadGraph' / f'{tileXYZ[-1]}' / f'{filename}.graphml'
            if G_r is not None:
                ox.save_graphml(G_r,
                                filepath=fp)
                if verbose:
                    print('\tSaved road graph as graphml: ', fp)

            # Save the GeoDataFrame (for bldg data) as Geojson
            fp = out_dir_root / city / 'BldgGeom' / f'{tileXYZ[-1]}' / f'{filename}.geojson'
            if not fp.parent.exists():
                fp.mkdir(parents=True)
                print(f'Created {fp.parent}')

            if gdf_b is not None and not gdf_b.empty:
                try:
                    _gdf = gdf_b.apply(lambda c: c.astype(str) if c.name != "geometry" else c, axis=0)
                    _gdf.to_file(fp, driver='GeoJSON')
                    if verbose:
                        print('\tSaved BLDG Geopandas as geopackage: ', fp)
                except:
                    print(f"\tFailed to save BLDG Geopandas as gpkg: ", sys.exc_info()[0])

        # Compute states from G_r, gdf_b and save to record dict
        if G_r is not None:
            road_stats = compute_road_network_stats(G_r)
            record.update(road_stats)

        # Write this location's record to a json file
        # todo: test this part -- see if each record is written as individual csv file
        if save:
            record_dir = out_dir_root / city / 'RoadStat'
            mkdir(record_dir)
            write_record(record, record_dir / f'{filename}.csv', verbose=verbose)

        # Append the record to records
        records.append(record)
        print(len(records), end="...")

    # Write the final `records` to a file
    vidx = 0
    # filename to store
    records_fn = f'{city}-{style}-{tileXYZ[-1]}-ver{vidx}.pkl'
    while (records_dir_root / records_fn).exists():
        vidx += 1
        records_fn = f'{city}-{style}-{tileXYZ[-1]}-ver{vidx}.pkl'
        print(f'records file already exists --> Increased the version idx to {vidx}...')
    joblib.dump(records, records_dir_root / records_fn)
    print(f'\tSaved the final records for {city} to: {records_dir_root / records_fn}')

    return records


if __name__ == "__main__":
    # Argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', "--city", type=str, required=True,
                        help="<Required> Name of the city folder")
    parser.add_argument('-s', "--style", type=str, default='StamenTonerLines',
                        help="<Optional> Name of the style folder. Default: StamenTonerLines")
    parser.add_argument("-z", "--zoom", type=str, default='14',
                        help="<Optional> Zoom level")
    parser.add_argument("-nw", "--network_type", type=str, default='drive_service',
                        help="<Optional> Network type to query from OSM. Default: drive_service")
    parser.add_argument("--out_dir_root", type=str, default='./temp/images',
                        help="<Optional> Name of the output folder root. Default: ./temp/images")
    parser.add_argument("--records_dir_root", type=str, default='./temp/records',
                        help="<Optional> Name of the root folder to store 'records'. Default: ./temp/records")

    args = parser.parse_args()
    city = args.city
    style = args.style
    zoom = args.zoom
    network_type = args.network_type

    out_dir_root = Path(args.out_dir_root)
    records_dir_root = Path(args.records_dir_root)

    print("Args: ", args)
    start = time.time()
    retrieve_and_rasterize_locs_in_a_folder(
        city,
        style,
        zoom,
        network_type,
        save=True,
        verbose=False,
        out_dir_root=out_dir_root,
        records_dir_root=records_dir_root)

    print(f"Done: {city}, {style}, {zoom}. Took: {time.time() - start}")

