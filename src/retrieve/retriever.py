import sys

from typing import Tuple, List, Dict, Optional
from networkx.classes.graph import Graph
import osmnx as ox
from osmnx.plot import utils_graph, graph, simplification, utils_geo, plot_graph
from src.utils.geo import getGeoFromTile, getTileFromGeo, getTileExtent


def get_road_graph_and_bbox(
        tileXYZ: Tuple[int, int, int],
        network_type: str = "drive_service",
) -> Tuple[Graph, Tuple[float, float, float, float]]:
    """Given Tileset location (x,y,z), retrieve road network data from OSM
    for the area that is covered by the maptile.

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

    # Specify style parameters
    bgcolors = ['w']  # ['#ffffff']
    edge_colors = ['k']  # ['#111111']
    lw_factors = [0.5, 1.0]

    # Get OSM road network as a graph
    G_r, bbox = None, None
    try:
        G_r = ox.graph_from_point(center, dist=radius, dist_type='bbox', network_type=network_type)
        bbox = ox.utils_geo.bbox_from_point(center, dist=radius)
    except:
        print(f"{x, y, z} -- Road error:", sys.exc_info()[0])

    return G_r, bbox

