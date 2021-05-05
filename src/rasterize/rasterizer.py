import sys
from typing import Tuple, List, Dict, Optional
from pathlib import Path
import osmnx as ox
from osmnx.plot import utils_graph, graph, simplification, utils_geo, plot_graph
import geopandas as gpd
from networkx.classes.graph import Graph

from src.utils.geo import getGeoFromTile, getTileFromGeo, getTileExtent

def plot_figure_ground(
    G,
    bbox: Tuple[float,float,float,float],
    network_type="drive_service",
    street_widths=None,
    default_width=4,
    figsize=(8, 8),
    edge_color="w",
    smooth_joints=True,
    **pg_kwargs,
):
    """
    Plot a figure-ground diagram of a street network.
    Parameters
    ----------
    G : networkx.MultiDiGraph
        input graph, must be unprojected
    bbox : Tuple of numeric
        how many meters to extend north, south, east, west from center point
    network_type : string
        what type of street network to get
    street_widths : dict
        dict keys are street types and values are widths to plot in pixels
    default_width : numeric
        fallback width in pixels for any street type not in street_widths
    figsize : numeric
        (width, height) of figure, should be equal
    edge_color : string
        color of the edges' lines
    smooth_joints : bool
        if True, plot nodes same width as streets to smooth line joints and
        prevent cracks between them from showing
    pg_kwargs
        keyword arguments to pass to plot_graph
    Returns
    -------
    fig, ax : tuple
        matplotlib figure, axis
    """
    multiplier = 1.2

    # if user did not pass in custom street widths, create a dict of defaults
    if street_widths is None:
        street_widths = {
            "footway": 1.5,
            "steps": 1.5,
            "pedestrian": 1.5,
            "service": 1.5,
            "path": 1.5,
            "track": 1.5,
            "motorway": 6,
        }

    # if G was passed in, plot it centered on its node centroid
    if G is not None:
        gdf_nodes = utils_graph.graph_to_gdfs(G, edges=False, node_geometry=True)
        lnglat_point = gdf_nodes.unary_union.centroid.coords[0]
        point = tuple(reversed(lnglat_point))



    # we need an undirected graph to find every edge incident on a node
    Gu = utils_graph.get_undirected(G)

    # for each edge, get a linewidth according to street type
    edge_linewidths = []
    for _, _, d in Gu.edges(keys=False, data=True):
        street_type = d["highway"][0] if isinstance(d["highway"], list) else d["highway"]
        if street_type in street_widths:
            edge_linewidths.append(street_widths[street_type])
        else:
            edge_linewidths.append(default_width)

    if smooth_joints:
        # for each node, get a nodesize according to the narrowest incident edge
        node_widths = dict()
        for node in Gu.nodes:
            # first, identify all the highway types of this node's incident edges
            ie_data = [Gu.get_edge_data(node, nbr) for nbr in Gu.neighbors(node)]
            edge_types = [d[min(d)]["highway"] for d in ie_data]
            if not edge_types:
                # if node has no incident edges, make size zero
                node_widths[node] = 0
            else:
                # flatten the list of edge types
                et_flat = []
                for et in edge_types:
                    if isinstance(et, list):
                        et_flat.extend(et)
                    else:
                        et_flat.append(et)

                # lookup corresponding width for each edge type in flat list
                edge_widths = [
                    street_widths[et] if et in street_widths else default_width for et in et_flat
                ]

                # node diameter should equal largest edge width to make joints
                # perfectly smooth. alternatively use min(?) to prevent
                # anything larger from extending past smallest street's line.
                # circle marker sizes are in area, so use diameter squared.
                circle_diameter = max(edge_widths)
                circle_area = circle_diameter ** 2
                node_widths[node] = circle_area

        # assign the node size to each node in the graph
        node_sizes = [node_widths[node] for node in Gu.nodes]
    else:
        node_sizes = 0

    # define the view extents of the plotting figure
    # bbox = utils_geo.bbox_from_point(point, dist, project_utm=False)

    # plot the figure
    override = {"bbox", "node_size", "node_color", "edge_linewidth"}
    kwargs = {k: v for k, v in pg_kwargs.items() if k not in override}
    fig, ax = plot_graph(
        G=Gu,
        bbox=bbox,
        figsize=figsize,
        node_size=node_sizes,
        node_color=edge_color,
        edge_color=edge_color,
        edge_linewidth=edge_linewidths,
        **kwargs,
    )
    return fig, ax

def rasterize_road_graph(
        G: Graph,
        tileXYZ: Tuple[int, int, int],
        bbox: Tuple[float],
        bgcolors: List,
        edge_colors: List,
        lw_factors: List[float],
        save: bool,
        out_dir_root: Path,
        suffix: str = '.png',  # Note: Do include a dot
        dpi=50,
        verbose=False,
        show: bool = True,
        show_only_once: bool = True,
        figsize: Tuple[int, int] = (7, 7),
        street_widths: Dict[str, float] = None,
):
    """Rasterize the given graph in all possible (distinct) combinations of style parameters,
    `bgcolor`, `edge_color`, `edge_weights*lw_factor`.

    Args:
    ------
    If save:
    - base = 'OSMnxR' or `OSMnxB`, or `OSMnxRB`
    - style_name = f'{base}-{bgcolor}-{edge_color}-{lw_factors}`
    - save to the `out_dir_root`/{style_name}/z/f'{x}_{y}_{z}{suffix}`

    - street_weigths: a dictionary of OSM tag (e.g. "motorway") and its edge weight (e.g. 4.5)
        Default is:
        {
          "footway": 1.5,
          "steps": 1.5,
          "pedestrian": 1.5,
          "service": 1.5,
          "path": 1.5,
          "track": 1.5,
          "motorway': 6,
        }

    """
    # if user did not pass in custom street widths, create a dict of defaults
    if street_widths is None:
        street_widths = {
            "footway": 1.5,
            "steps": 1.5,
            "pedestrian": 1.5,
            "service": 1.5,
            "path": 1.5,
            "track": 1.5,
            "motorway": 3,
        }
    x, y, z = tileXYZ
    filename = f'{x}_{y}_{z}{suffix}'

    for bgcolor in bgcolors:
        for edge_color in edge_colors:
            if bgcolor == edge_color: continue
            for lw_factor in lw_factors:
                # Scale the edge widths of each street type
                lw = {k: v * lw_factor for (k, v) in street_widths.items()}

                style_name = f'OSMnxR-{bgcolor}-{edge_color}-{lw_factor}'
                fp = out_dir_root / style_name / str(z)/ filename

                f, ax = plot_figure_ground(
                    G,
                    bbox=bbox,
                    street_widths=lw,
                    figsize=figsize,
                    bgcolor=bgcolor,
                    node_color=edge_color,
                    edge_color=edge_color,
                    show=show,
                    close=True,
                    save=save,  # false?
                    filepath=fp,
                    dpi=dpi,
                )
                if show and show_only_once:
                    show = False

                if verbose:
                    print('style: ', style_name)
                    print('x,y,z: ', x, y, z)
                    print('dpi: ', dpi)
                    print('-' * 10)
#                 breakpoint()


def rasterize_road_and_bldg(
        G: Graph,
        gdf_b: gpd.GeoDataFrame,
        tileXYZ: Tuple[int, int, int],
        bbox: Tuple[float],
        bgcolors: List,
        edge_colors: List,
        bldg_colors: List,
        lw_factors: List[float],
        save: bool,
        out_dir_root: Path,
        suffix: str = '.png',  # Note: Do include a dot
        dpi=50,
        verbose=True,
        show: bool = True,
        show_only_once: bool = True,
        figsize: Tuple[int, int] = (7, 7),
        street_widths: Dict[str, float] = None,
):
    """Rasterize the given graph of road networks (G_r) and (if save) save to
    `out_dir_root`/f'OSMnxR-{bgcolor}-{edge_color}-{lw_factor}' directory.
    Do this for all possible (distinct) combinations of style parameters,
    `bgcolor`, `edge_color`, `lw_factor*each street_width in street_widths dictionary`.

    Also, rasterize the retrieved (from OSM) bldg geometries (gdf_b) in each style setting.
    If save, save the bldg footprint overlayed on the road networks (if road networks were
    successfully retrieved; otherwise, just bldg geometries will be rasterized)
    to the directory `out_dir_root`/f'OSMnxRB-{bgcolor}-{edge_color}-{bldg_color}-{lw_factor}'.

    Args:
    ------
    If save:
    - base = 'OSMnxR' or `OSMnxB`, or `OSMnxRB`
    - style_name = f'{base}-{bgcolor}-{edge_color}-{lw_factors}`
    - save to the `out_dir_root`/{style_name}/z/f'{x}_{y}_{z}{suffix}`

    - street_weigths: a dictionary of OSM tag (e.g. "motorway") and its edge weight (e.g. 4.5)
        Default is:
        {
          "footway": 1.5,
          "steps": 1.5,
          "pedestrian": 1.5,
          "service": 1.5,
          "path": 1.5,
          "track": 1.5,
          "motorway': 6,
        }

    """
    # if user did not pass in custom street widths, create a dict of defaults
    if street_widths is None:
        street_widths = {
            "footway": 1.5,
            "steps": 1.5,
            "pedestrian": 1.5,
            "service": 1.5,
            "path": 1.5,
            "track": 1.5,
            "motorway": 3,
        }

    x, y, z = tileXYZ
    filename = f'{x}_{y}_{z}{suffix}'
    if verbose:
        print('rasterize_road_and_blgd -- x,y,z: ', x, y, z)
        # print('dpi: ', dpi)

    for bgcolor in bgcolors:
        for edge_color in edge_colors:
            if bgcolor == edge_color: continue
            for bldg_color in bldg_colors:
                for lw_factor in lw_factors:
                    # Scale the edge widths of each street type
                    lw = {k: v * lw_factor for (k, v) in street_widths.items()}

                    style_name = f'OSMnxR-{bgcolor}-{edge_color}-{lw_factor}'
                    fp = out_dir_root / style_name / str(z)/ filename

                    # Plot road network
                    if G is not None:
                        f, ax = plot_figure_ground(
                            G,
                            bbox=bbox,
                            street_widths=lw,
                            figsize=figsize,
                            bgcolor=bgcolor,
                            node_color=edge_color,
                            edge_color=edge_color,
                            show=show,
                            close=True,
                            save=save,  # false?
                            filepath=fp,
                            dpi=dpi,
                        )
                    else:
                        ax = None
                        print('\tNo road network is plotted/saved: ', x, y, z)

                    # Plot bldg footprints
                    if gdf_b is not None:
                        style_name = f'OSMnxRB-{bgcolor}-{edge_color}-{bldg_color}-{lw_factor}'
                        fp = out_dir_root / style_name / str(z)/ filename
                        f, ax = ox.plot_footprints(
                            gdf_b,
                            ax=ax,
                            figsize=figsize,
                            color=bldg_color,
                            bgcolor=bgcolor,
                            bbox=bbox,
                            show=show,
                            close=True,
                            save=save,
                            filepath=fp,
                            dpi=dpi,
                        )
                    else:
                        print('\tNo bldg footprint is plotted/saved: ', x, y, z)

                    if show and show_only_once:
                        show = False

    #                 breakpoint()


def single_rasterize_road_graph(
        center: Optional[Tuple[float, float]]=None, #(lat_deg, lng_deg)
        zoom: int=14,
        tileXYZ: Optional[Tuple[int, int, int]]=None,
        bgcolor='w',
        edge_color='k',
        save: bool=True,
        out_dir_root=Path('./temp'),
        **kwargs,
)-> Graph:
    # Query location
    lat_deg, lng_deg = center
    x, y, z = getTileFromGeo(lat_deg, lng_deg, zoom)
    extent, _ = getTileExtent(x, y, z)
    radius = extent // 2  # meters
    network_type = "drive_service"

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


    if G_r is not None:
        rasterize_road_graph(G_r,
                             tileXYZ=(x, y, z),
                             bbox=bbox,
                             bgcolors=bgcolors,
                             edge_colors=edge_colors,
                             lw_factors=lw_factors,
                             save=save,
                             out_dir_root=out_dir_root,
                             **kwargs
                             )

    return G_r


def single_rasterize_road_and_bldg(
        center: Optional[Tuple[float, float]]=None, #(lat_deg, lng_deg)
        zoom: int=14,
        tileXYZ: Optional[Tuple[int, int, int]]=None,
        bgcolor='w',
        edge_color='k',
        bldg_color='silver',
        save: bool=True,
        out_dir_root=Path('./temp'),
        **kwargs,
)-> Tuple[Graph, gpd.GeoDataFrame]:
    """Given the center location (either as (lat_deg, lng_deg) or as tileXYZ),
    retrieve and rasterize the OSM road networks and the building footprints using a single style config:
    - bgcolor (Default: black)
    - edge_color (Default: white)
    - bldg_color (Default: silver)

    If both (lat,lng) and tileXYZ are given, we use tileXYZ to extract the center location
    in (lat,lng), and ignore the inputted (lat,lng)

    Args
    -----
    - kwargs will be passed to `rasterize_road_and_bldg`
        - suffix: str
        - dpi: int
        - verbose: bool
        - show
        - figsize: default  (7,7)
        - street_widths: Dict[str,float[ = None
    """
    # Query location
    if (center is not None) and (tileXYZ is None):
        lat_deg, lng_deg = center
        x, y, z = getTileFromGeo(lat_deg, lng_deg, zoom)
    elif (center is None) and (tileXYZ is not None):
        x, y, z = tileXYZ
        lat_deg, lng_deg = getGeoFromTile(x, y, z)
        center = (lat_deg, lng_deg)
    elif center is not None and tileXYZ is not None:
        x, y, z = tileXYZ
        lat_deg, lng_deg = getGeoFromTile(x, y, z)
        center = (lat_deg, lng_deg)
    else:
        raise ValueError('One of center or tileXYZ must be given')
    extent, _ = getTileExtent(x, y, z)
    radius = extent // 2  # meters
    network_type = "drive_service"

    # debug
    print('single_rasterize_road_bldg -- x,y,z: ', x,y,z)
    print('single_rasterize_road_bldg -- lat, lng: ', lat_deg, lng_deg)
    print()

    # Specify style parameters
    bgcolors = [bgcolor]
    edge_colors = [edge_color]
    bldg_colors = [bldg_color]
    lw_factors = [0.5, 1.0]

    # Get OSM road network as a graph
    G_r = None
    try:
        G_r = ox.graph_from_point(center, dist=radius, dist_type='bbox', network_type=network_type)
    except:
        print(f"{x, y, z} -- Road retrieval error:", sys.exc_info()[0])
    # Get OSM bldg geometris as GeoDataFrame
    gdf_b, bbox = None, None
    try:
        gdf_b = ox.geometries_from_point(center, tags={'building': True}, dist=radius)
        bbox = ox.utils_geo.bbox_from_point(center, dist=radius)
        print("single_rasterize_road_bldg -- bbox: ", bbox)
    except:
        print(f"{x, y, z} -- Bldg retrieval error:", sys.exc_info()[0])

    rasterize_road_and_bldg(
        G_r,
        gdf_b,
        (x, y, z),
        bbox,
        bgcolors=bgcolors,
        edge_colors=edge_colors,
        bldg_colors=bldg_colors,
        lw_factors=lw_factors,
        save=save,
        out_dir_root=out_dir_root,
        **kwargs
    )

    return G_r, gdf_b


