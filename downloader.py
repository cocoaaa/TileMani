import os
import argparse
import json
import urllib.request as ur
from urllib.error import URLError

from typing import Callable, Iterable, Union, List
from functools import partial
from pathlib import Path

import time
from decimal import Decimal
import tqdm
import pdb

from PIL import Image

from tileGeoTransfer import *  # getTileFromGeo & getGeoFromTile
import tile_sources as ts
from utils import makedir, snake2camel



def checkBlankImg_ggl(filename):
    '''
	input type: file path
	return type: Boolean
	'''
    im = Image.open(filename)  # Can be many different formats.
    pix = im.load()

    # print(im.size
    pixel_values = list(im.getdata())

    # RGB channel
    if min(pixel_values) == max(pixel_values):
        return True

    return False


def checkBlankImg_nls(filename):
    '''
	input type: file path
	return type: Boolean
	'''
    im = Image.open(filename)
    pix = im.load()

    # print(im.size
    pixel_values = list(im.getdata())
    zipped = zip(pixel_values)

    # RGB channel
    if min(zipped[0][0]) == max(zipped[0][0]) \
            and min(zipped[1][0]) == max(zipped[1][0]) \
            and min(zipped[2][0]) == max(zipped[2][0]):
        return True

    return False


def store_4Geo_Boundary(lnglat_path: str, x, y, z):
    f = open(lnglat_path, "w+")

    # bottom right
    lat, lng = getGeoFromTile(x, y, z)
    f.write("%f %f\n" % (lat, lng))

    # bottom left
    lat, lng = getGeoFromTile(x + 1, y, z)
    f.write("%f %f\n" % (lat, lng))

    # top right
    lat, lng = getGeoFromTile(x, y + 1, z)
    f.write("%f %f\n" % (lat, lng))

    # top left
    lat, lng = getGeoFromTile(x + 1, y + 1, z)
    f.write("%f %f\n" % (lat, lng))

    f.close()


def getImgFromUrl(out_dir: Union[str, Path], url: str, x, y, z):
    checkBlankImg_fn = checkBlankImg_nls if 'nls' in url else checkBlankImg_ggl
    lat, lng = getGeoFromTile(x, y, z)  # for error messages

    req = ur.Request(url)
    try:
        urlobj = ur.urlopen(req)
    except URLError as e:
        if hasattr(e, 'reason'):
            print(f'We failed to reach a server: {url}')
            print('Reason: ', e.reason)
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        print("Failed at lng, lat (x,y,z):  {lng, lat, (x, y, z)}")
        return

    out_dir = makedir(out_dir)
    if urlobj.getcode() == 200:
        out_fn = out_dir / f"{x}_{y}_{z}.png"

        try:
            ur.urlretrieve(url, str(out_fn))
        except URLError as e:
            if hasattr(e, 'reason'):
                print(f'We failed to reach a server: {url}')
                print('Reason: ', e.reason)
            elif hasattr(e, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)
            print("Failed at lng, lat (x,y,z):  {lng, lat, (x, y, z)}")
            return

        # Check if the image is blank, i.e: sea, plain grass
        if checkBlankImg_fn(out_fn):  # or checkBlankImg_ggl(out_fn):
            if out_fn.exists():
                out_fn.unlink()
                print("Deleted lng, lat (x,y,z):  {lng, lat, (x, y, z)}")
            else:
                print(out_fn, " does not exist. Nothing to do.")
        else:
            lnglat_dir = out_dir / "lnglat/"
            if not lnglat_dir.exists():
                lnglat_dir.mkdir()

            lnglat_path = lnglat_dir / f"{x}_{y}_{z}.txt"
            store_4Geo_Boundary(str(lnglat_path), x, y, z)

            print("Success: ", x, y, z, getGeoFromTile(x, y, z))
    else:
        print(f"Failed at lng, lat (x,y,z):  {lng, lat, (x, y, z)}")


def download_tiles_by_xyz(out_dir: Union[str, Path], url_base: str,
                          x_start, x_end, y_start, y_end, z):
    out_dir = makedir(out_dir)

    for x in range(x_start, x_end + 1):
        for y in range(y_start, y_end + 1):
            print(x, y)
            url_tile = url_base.format(X=x, Y=y, Z=z)
            getImgFromUrl(out_dir, url_tile, x, y, z)
            time.sleep(0.005)


def download_tiles_by_lnglat(out_dir: Union[str, Path], url_base: str,
                             start_long, end_long, start_lat, end_lat, zoom):
    x0, y0, z = getTileFromGeo(start_lat, start_long, zoom)
    x1, y1, z = getTileFromGeo(start_lat, end_long, zoom)
    x2, y2, z = getTileFromGeo(end_lat, start_long, zoom)
    x3, y3, z = getTileFromGeo(end_lat, end_long, zoom)

    start_x = min(x0, x1, x2, x3)
    end_x = max(x0, x1, x2, x3)
    start_y = min(y0, y1, y2, y3)
    end_y = max(y0, y1, y2, y3)

    print('Downloading...', start_x, end_x, start_y, end_y)
    download_tiles_by_xyz(out_dir, url_base, start_x, end_x, start_y, end_y, z)


def download_tiles_from_cities(locations_fn: str, tile_source_name: str, styles: Iterable[str],
                               out_dir_root: Union[str, Path], overwrites=None):
    out_dir_root = makedir(out_dir_root)

    with open(locations_fn) as f:
        city_geos = json.load(f)
    print(list(city_geos.keys()))

    for city, geo in tqdm.tqdm(city_geos.items(), desc='city-loop'):
        # if city in ['paris', 'khartoum']:
        #     continue
        xmin, xmax, ymin, ymax = geo['xmin'], geo['xmax'], geo['ymin'], geo['ymax']
        z = geo.get('z', 13)
        if overwrites is not None:
            print(f"Overwriting z {z} -> {overwrites['z']}")
            z = overwrites["z"]
        # pdb.set_trace()

        print('=' * 80)
        print('Started ', city)
        for style in tqdm.tqdm(styles, desc=f'style-loop'):
            print('Started style: ', city, style)
            ts_name = f'{tile_source_name}{snake2camel(style)}'
            url_base = ts.tile_sources[ts_name]
            print(f'style: {ts_name}, \nurl_base: {url_base}')

            out_dir = Path(out_dir_root) / city / ts_name / str(z)
            out_dir = makedir(out_dir)
            download_tiles_by_lnglat(out_dir, url_base, xmin, xmax, ymin, ymax, z)
            print(f'Done {style}\n')
        print(f'Done {city}\n\n')

def download_xyz_from(x: int, y: int, z: int,
                      url_base:str,
                      out_dir: Union[str, Path]):
    out_dir = makedir(out_dir)
    url_tile = url_base.format(X=x, Y=y, Z=z)
    print(f'Downloading maptile...: {url_tile}')
    getImgFromUrl(out_dir, url_tile, x, y, z)


def download_osm_xyz(x: int, y: int, z: int,
                    out_dir_root: Union[str, Path]):
    url_base= ts.OSMDefault
    out_dir_root = makedir(out_dir_root)
    out_dir = out_dir_root / 'OSM'
    download_xyz_from(x, y, z, url_base, out_dir)

def download_nls_xyz(x: int, y: int, z: int,
                    out_dir_root: Union[str, Path]):
    url_base= ts.NLSDefault
    out_dir_root = makedir(out_dir_root)
    out_dir = out_dir_root / 'NLS'
    download_xyz_from(x, y, z, url_base, out_dir)

def download_mtbmap_xyz(x: int, y: int, z: int,
                    out_dir_root: Union[str, Path]):
    url_base= ts.MtbMapDefault
    out_dir_root = makedir(out_dir_root)
    out_dir = out_dir_root / 'MtbMap'
    download_xyz_from(x, y, z, url_base, out_dir)

def download_styles_xyz(x: int, y: int, z: int,
                        tile_source_name: str,
                        styles: Union[str, List],
                        out_dir_root: Union[str, Path]):
    """
    tile_source_name: (will be capitalized) must be one of:
        - TileSource class: Stamen, Esri, Carto, OSM, NLS, MtnMap,
    styles = must be one of the TileSouce (selected by the input name `tile_source_name`'s styles
        - eg. If `tile_source_name` is 'Stamen': styles must be a list with elements from
        ['toner', 'toner_background', 'toner_lines', 'terrain', 'terrain_lines', 'watercolor']
        - eg. If 'tile_source_name' is 'OSM': styles must be a list of a single string: ['default']
        This is applicable to any `tile_source` that has a single style, such as NLS, MtnMap


    :param x,y,z: map tile index x,y,z
    :param tile_source: name of the tile source, eg. Stamen, Carto, Esri, OSM
    :param styles:
    :param out_dir_root: Path to the directory root to save the downloaded images
    :return:
    """
    out_dir_root = makedir(out_dir_root)
    tile_source_name = tile_source_name.capitalize()
    tile_source = getattr(ts, tile_source_name)
    if isinstance(styles, str):
        styles = [styles]

    if len(styles) and styles[0].lower() == 'all':
        styles = tile_source.styles
    print("styles: ", styles)  # delete

    for style in styles:
        assert style.lower() in tile_source.styles, f'{style} is not a valid style name'
        ts_name = f'{tile_source_name}{snake2camel(style)}'
        url_base = getattr(ts, ts_name)
        out_dir = out_dir_root / ts_name
        download_xyz_from(x, y, z, url_base, out_dir)


def download_stamen_styles(locations_fn: str, styles: Iterable[str], out_dir_root: Union[str, Path]):
    """
	styles = ['toner', 'toner_background', 'toner_lines', 'terrain', 'terrain_lines', 'watercolor']

	:param locations_fn: path to the json file with city_name:bbox_dictionary
	:param styles:
	:param out_dir_root:
	:return:
	"""
    for style in styles:
        assert style.lower() in ts.Stamen.styles, f'{style} is not a valid style name'

    tile_source_name = ts.Stamen.name
    download_tiles_from_cities(locations_fn, tile_source_name, styles, out_dir_root)


def download_esri_styles(locations_fn: str, styles: Iterable[str], out_dir_root: Union[str, Path]):
    for style in styles:
        assert style.lower() in ts.Esri.styles, f'{style} is not a valid style name'
    tile_source_name = ts.Esri.name
    download_tiles_from_cities(locations_fn, tile_source_name, styles, out_dir_root)


def download_carto_styles(locations_fn: str, styles: Iterable[str], out_dir_root: Union[str, Path]):
    for style in styles:
        assert style.lower() in ts.Carto.styles, f'{style} is not a valid style name'
    tile_source_name = ts.Carto.name
    download_tiles_from_cities(locations_fn, tile_source_name, styles, out_dir_root)

def download_osm_styles(locations_fn: str, styles: Iterable[str], out_dir_root: Union[str, Path]):
    for style in styles:
        assert style.lower() in ts.OSM.styles, f'{style} is not a valid style name'
    tile_source_name = ts.OSM.name
    download_tiles_from_cities(locations_fn, tile_source_name, styles, out_dir_root)


# def download_osm(locations_fn: str, out_dir_root: str):
#     out_dir_root = makedir(out_dir_root)
#
#     with open(locations_fn) as f:
#         city_geos = json.load(f)
#     print(list(city_geos.keys()))
#
#     for city, geo in tqdm.tqdm(city_geos.items(), desc='city-loop'):
#         if city in ['paris', 'khartoum']:
#             continue
#         xmin, xmax, ymin, ymax = geo['xmin'], geo['xmax'], geo['ymin'], geo['ymax']
#         z = geo.get('z', 15)
#
#         print('=' * 80)
#         print('Started ', city)
#         out_dir = Path(out_dir_root) / city
#         out_dir = makedir(out_dir)
#
#         url_base = ts.tile_sources[ts.OSM.name]
#         download_tiles_by_lnglat(out_dir, url_base, xmin, xmax, ymin, ymax, z)
#         print(f'Done {city}\n\n')


def download_nls(locations_fn: str, out_dir_root: str, z=16):
    out_dir_root = makedir(out_dir_root)

    with open(locations_fn) as f:
        city_geos = json.load(f)
    print(list(city_geos.keys()))

    for city, geo in tqdm.tqdm(city_geos.items(), desc='city-loop'):
        xmin, xmax, ymin, ymax = geo['xmin'], geo['xmax'], geo['ymin'], geo['ymax']
        z = geo.get('z', z)

        print('=' * 80)
        print('Started ', city)
        out_dir = Path(out_dir_root) / city
        out_dir = makedir(out_dir)

        url_base = ts.tile_sources[ts.NLS.name]
        download_tiles_by_lnglat(out_dir, url_base, xmin, xmax, ymin, ymax, z)
        print(f'Done {city}\n\n')

def download_mtbmap_styles(locations_fn: str, styles: Iterable[str], out_dir_root: Union[str, Path]):
    for style in styles:
        assert style.lower() in ts.Mtbmap.styles, f'{style} is not a valid style name'
    tile_source_name = ts.Mtbmap.name
    download_tiles_from_cities(locations_fn, tile_source_name, styles, out_dir_root)

# def download_locations_styles(locations_fn: str, ts_name: str, styles: Iterable[str], out_dir_root: Union[str, Path]):
#     for style in styles:
#         assert style.lower() in ts.Mtbmap.styles, f'{style} is not a valid style name'
#     tile_source_name = ts.Mtbmap.name
#     download_tiles_from_cities(locations_fn, tile_source_name, styles, out_dir_root)


def download_selected_styles(locations_fn: str, selection_fn: str, out_dir_root: Union[str, Path],
                             overwrites=None):

    with open(selection_fn) as f:
        selection = json.load(f)
    for ts_class_name, styles in selection.items():
        ts_name = getattr(getattr(ts, ts_class_name), 'name')
        download_tiles_from_cities(locations_fn, ts_name, styles, out_dir_root, overwrites=overwrites)


if __name__ == "__main__":
    # Argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("bbox_json", type=str,
                        help="<Required> Path to a json file with cityname:bbox in lat,lng")
    parser.add_argument("-ts", "--tile-server", required=True, type=str,
                        help="<Required> Name of the tile server. Options: stamen, esri, carto, osm, nls")
    parser.add_argument("-s", "--styles", nargs='+', type=str,
                        help='<Required> Name of the styles to fetch from the tile server')
    parser.add_argument("-o", "--out", help="<Optional> Path to the output root folder. Default: ./tmp",
                        type=str, default='./tmp')

    args = parser.parse_args()
    bbox_json = args.bbox_json
    tile_server = args.tile_server
    styles = args.styles
    out_dir = args.out

    print('styles: ', styles)
    # Handle downloading from the specified tile server
    if tile_server == 'stamen':
        styles = styles or ['toner_background', 'terrain_background', 'watercolor']
        download_stamen_styles(bbox_json, styles, out_dir)

    elif tile_server == 'esri':
        styles = styles or ['imagery']  # , 'nat_geo', 'terrain']
        download_esri_styles(bbox_json, styles, out_dir)

    elif tile_server == 'carto':
        styles = styles or ['light_no_labels']  # ['dark', 'light']
        download_carto_styles(bbox_json, styles, out_dir)

    elif tile_server == 'osm':
        download_osm(bbox_json, out_dir)

    elif tile_server == 'nls':
        download_nls(bbox_json, out_dir)

# xmin, xmax, ymin, ymax = 52.0100, 52.0500, -1.0000, -0.9500
