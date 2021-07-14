import sys
from pathlib import Path
from typing import Tuple, Dict, List

import math
from geopy.geocoders import Nominatim


def deg2rad(x):
	"""Convert the unit of x from degree to radian"""
	return x * math.pi/180.0


def getTileFromGeo(lat_deg, lng_deg, zoom):
	'''
	get tile index from geo location
	:type : float, float, int
	:rtype: tuple(int, int, int)
	'''
	x = math.floor((lng_deg + 180) / 360.0 * (2.0 ** zoom))

	tan_y = math.tan(lat_deg * (math.pi / 180.0))
	cos_y = math.cos(lat_deg * (math.pi / 180.0))
	y = math.floor( (1 - math.log(tan_y + 1.0 / cos_y) / math.pi) / 2.0 * (2.0 ** zoom) )

	return int(x), int(y), int(zoom)


def getGeoFromTile(x, y, zoom):
	lon_deg = x / (2.0 ** zoom) * 360.0 - 180.0
	lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / (2.0 ** zoom))))
	lat_deg = lat_rad * (180.0 / math.pi)
	return lat_deg, lon_deg


def getTileExtent(x, y, zoom):
	"""Computes the horizontal and vertical distance covered by the tile of size 256x256 (in meters)

    Assumes tile size 256x256
    Returns
    -------
    - (extent_y, exent_x): extent of the region coverage in latitudal and longitudal distance (meter)
    Ref: "Distance per pixel math" in https://wiki.openstreetmap.org/wiki/Zoom_levels

    """
	lat_deg, lon_deg = getGeoFromTile(x,y,zoom)
	lat_rad, lon_rad = deg2rad(lat_deg), deg2rad(lon_deg)

	C_meters = 2*math.pi*6378137 # equatorial circumference of the Earth in meters
	size_y = C_meters * math.cos(lat_rad)/2**zoom
	size_x = C_meters * math.cos(lon_rad)/2**zoom
	return size_y, size_x


def get_latlng_and_radius(tileXYZ: Tuple[int, int, int]) -> Tuple[float, float, float]:
	"""Given tile index X,Y,Z, compute its lat,lng in degree
    and compute the radius (in meters) of the covered area
    Returns
    -------
    - (lat_deg, lng_deg, radius_meters)
    """
	# Center location of the OSM query
	x, y, z = tileXYZ
	lat_deg, lng_deg = getGeoFromTile(x, y, z)
	extent, _ = getTileExtent(x, y, z)
	radius = extent // 2  # meters
	return (lat_deg, lng_deg, radius)


def getAddrFromTile(x: int, y: int, z: int,
					language='en',
					detail_zoom:int=14) -> str:
	"""Given Tile (x,y,z), return the address of the location as a string.

	Args
	----

	detail_zoom : int
		Level of detail required for the address. Default: 18. This is a number that corresponds roughly to the zoom level used in XYZ tile sources in frameworks like Leaflet.js, Openlayers etc
		Eg: 3 --> country; 5 --> state, 8 --> county , 10 --> city
		See: https://nominatim.org/release-docs/latest/api/Reverse/#result-limitation
    Example
    -------
    addr = getAddrFromTile(8748, 6076, 14)
    country = addr[-1]
    print(addr, country)

    Examples of returned address (at zoom=14)
    -----------------------------------------
        'Jungsan-dong, Goyang-si, 10333, South Korea'
        'Silverthorne, Simi Valley, Ventura County, California, 93063, United States'
        'Clark County, Nevada, United States'
        'Saint-Janvier, Mirabel, Laurentides, Quebec, J7J1E3, Canada'
        'Vigna di Valle, Bracciano, Roma Capitale, Lazio, 00062, Italy'
    """
	lat_deg, lng_deg = getGeoFromTile(x, y, z)
	geolocator = Nominatim(user_agent="temp")

	addr = ''
	try:
		location = geolocator.reverse(f"{lat_deg}, {lng_deg}",
									  exactly_one=True,
									  zoom=detail_zoom,
									  language=language)
		addr = location[0]
	except:
		print(f"Nominatim reverse failed at {x, y, z}: ", sys.exc_info()[0])

	return addr


def getCountryFromTile(x,y,zoom, delimiter=',') -> str:
	"""Given x,y,z tile coords, return cityname"""
	lat_deg, lng_deg = getGeoFromTile(x,y,zoom)
	geolocator = Nominatim(user_agent="temp")
	location = geolocator.reverse(f"{lat_deg}, {lng_deg}")
	city = location.address.split(sep=delimiter)[-1]
	return city


def test_getCountryFromTile():
    print("shanghai: ", getCountryFromTile(13703, 6671, 14))
    print("paris: ", getCountryFromTile(8301, 5639, 14))


def coord2xyz(
	coord_str: str,
	delimiter:str = '-',
	z: int = 14) -> Tuple[int]:
    lat_deg, lng_deg = list(map(int, coord_str.split(delimiter)))
    return (lat_deg, lng_deg, z)

def coord2country(coord_str: str,
                 delimiter='-',
                 z: int = 14) -> str:
    tile_xyz = coord2xyz(coord_str, delimiter, z)
    return getCountryFromTile(*tile_xyz)


def parse_maptile_fp(fp: Path) -> Dict:
	"""Given a maptile image's filepath (e.g. /DATA_ROOT/paris/StamenTonerLines/14/8902_2134_14.png),
    returns a tile x,y,z, lat_deg, lng_deg and radius of the area covered in the maptile as a dict.
    """
	# Maptile's location
	x, y, z = map(int, fp.stem.split("_"))
	lat_deg, lng_deg = getGeoFromTile(x, y, z)
	extent, _ = getTileExtent(x, y, z)
	radius = extent // 2  # meters

	return {
		"x": x,
		"y": y,
		"z": z,
		"lat_deg": lat_deg,
		"lng_deg": lng_deg,
		"radius": radius
	}