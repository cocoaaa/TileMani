import sys

from typing import Tuple, List, Dict, Optional
from networkx.classes.graph import Graph
from geopandas import GeoDataFrame
import osmnx as ox
from osmnx.plot import utils_graph, graph, simplification, utils_geo, plot_graph
from src.tilemani.utils import getGeoFromTile, getTileFromGeo, getTileExtent, get_latlng_and_radius


def get_road_graph_and_bbox(
        tileXYZ: Tuple[int, int, int],
        network_type: str = "drive_service",
) -> Tuple[Optional[Graph], Tuple[float, float, float, float]]:
    """Given a maptile (x,y,z) of size 256x256,
    retrieve the road network data from OSM for the area that is covered by the maptile.
    Also, returns the bbox of the area covered in the maptile as lat-lng coordinate (degree)

    Returns
    -------
    - G_r: graph of the retrieved road network
    - bbox: bounding box of the area covered in lat,lng degree
    """
    # Center location of the OSM query
    x, y, z = tileXYZ
    center = getGeoFromTile(x, y, z)
    extent, _ = getTileExtent(x, y, z)
    radius = extent // 2  # meters

    # Get OSM road network as a graph
    G_r, bbox = None, None
    try:
        G_r = ox.graph_from_point(center, dist=radius, dist_type='bbox', network_type=network_type)
        bbox = ox.utils_geo.bbox_from_point(center, dist=radius)
    except:
        print(f"{x, y, z} -- Road error:", sys.exc_info()[0])

    return G_r, bbox


def get_geoms(
        tileXYZ: Tuple[int, int, int],
        tag: Dict={'building': True},
) -> Optional[GeoDataFrame]:
    lat_deg, lng_deg, radius = get_latlng_and_radius(tileXYZ)

    gdf = None
    try:
        gdf = ox.geometries_from_point((lat_deg, lng_deg),
                                       tags=tag,
                                       dist=radius)
    except:
        print(f"Bldg retrieval error at {tileXYZ}: ", sys.exc_info()[0]) #todo: make it a logger

    return gdf



