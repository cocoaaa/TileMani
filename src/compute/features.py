import osmnx as ox
from typing import Tuple, Dict
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


def get_total_area(G) -> float:
    """Computes the total area (in square meters) of the square maptile of the graph (when it's rasterized)
    G: unprojected (ie.e in lat,lng degree crs)

    """
    gdf_n, gdf_e = ox.utils_graph.graph_to_gdfs(G)
    gdfproj_n, gdfproj_e = ox.project_gdf(gdf_n), ox.project_gdf(gdf_e)
    node_bounds, edge_bounds = gdfproj_n.total_bounds, gdfproj_e.total_bounds
    total_bounds = (
        min(node_bounds[0], edge_bounds[0]),
        min(node_bounds[1], edge_bounds[1]),
        max(node_bounds[2], edge_bounds[2]),
        max(node_bounds[3], edge_bounds[3])
    )

    minx, miny, maxx, maxy = total_bounds
    dx = maxx - minx
    dy = maxy - miny
    total_area = dx * dy
    return total_area


def get_road_area(G, avg_road_radius=3.0):
    """
    G: unprojected (ie. in lat,lng degree)
    avg_road_radis: radius of the roads on average, in meters
    """
    gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
    road_geom = ox.project_gdf(gdf_edges).unary_union  # Multistring obj in UTM
    buffered_road_geom = road_geom.buffer(avg_road_radius)
    road_area = buffered_road_geom.area
    print('Area of the roads: ', road_area)

    return road_area


def compute_road_network_stats(G) -> Dict:
    # compute total area of the area covered by the rastered image of this graph/network
    total_area = get_total_area(G)

    # unpack dicts into individiual keys:values
    stats = ox.basic_stats(G, area=total_area)
    for k, count in stats["streets_per_node_counts"].items():
        stats["int_{}_count".format(k)] = count
    for k, proportion in stats["streets_per_node_proportion"].items():
        stats["int_{}_prop".format(k)] = proportion

    # delete the no longer needed dict elements
    del stats["streets_per_node_counts"]
    del stats["streets_per_node_proportion"]

    # change key named 'n' to 'n_nodes', and 'm' to 'n_edges'
    stats['n_nodes'] = stats.pop('n', None)
    stats['n_edges'] = stats.pop('m', None)

    return stats


def get_road_figure_and_nway_proportion(G,
                                        figsize=(8, 8),
                                        bgcolor='k',
                                        **pg_kwargs) -> Tuple[plt.Figure, Dict[int, float]]:
    """Given an unprojected graph of road networks,
    show a figure of (i) network graph and (ii) distribution of the streets_per_node_proportions

    Other args:
    ----------
    - pg_kwargs:
        -
    """
    f = plt.figure(figsize=figsize)
    gs = GridSpec(2, 1, height_ratios=[4, 1])
    ax0 = f.add_subplot(gs[0])
    ax1 = f.add_subplot(gs[1])

    # Plot the graph of road network
    ax0.set_facecolor(bgcolor)
    _ = ox.plot_graph(G, ax0, **pg_kwargs)

    # Plot bar chart of the distribution of nways
    # todo: add other stats we want to extract

    stats = ox.basic_stats(G)
    dist_n_ways = stats['streets_per_node_proportion']
    ax1.bar(dist_n_ways.keys(), dist_n_ways.values(), width=0.2, color='grey')
    ax1.set_xlabel('N ways')
    ax1.set_ylim([0, 1])
    return f, dist_n_ways


## todo
# def show_ntw_ori(lat_deg: float,
#                  lng_deg: float,
#                  radius_y: float = 804.,
#                  radius_x: float = 1222.,
#                  network_type: str = 'drive_service',
#                  use_extended_stats: bool = False,
#                  avg_road_radius=3.0,
#                  weight_by_length=True,
#                  verbose=False,
#                  ) -> plt.Figure:  # Tuple[plf.Figure, plt.Axes]:
#     """
#     Args
#     ----
#     - lat_deg, lng_deg: center point's lat,lng in degree
#     - radius_y, radius_x: radius in latitudal(y) and longigtudal(x) direction, in meters
#         Use half of y_extent (of the maptile's coverage) for `radius_y`
#         Use half of x_extent for `radius_x`
#     - network_type (str): what kind of network to query from OSM
#     - avg_road_radius (float):
# 
#     """
#     center = (lat_deg, lng_deg)
#     radius = max(radius_y, radius_x)  # todo: min?
#
#     # create network from point, inside bounding box of N, S, E, W each `radius` (meter) from point
#     G = ox.graph_from_point(center, dist=radius, dist_type='bbox', network_type=network_type)
#     G_proj = ox.project_graph(G)
#
#     # Compute the area of roads
#     road_area = get_road_area(G, avg_road_radius=avg_road_radius)  # square meters
#
#     # Compute basic stats
#     stats = ox.basic_stats(G, area=road_area, circuity_dist='gc')
#
#     # -- Optionally, compute extra, extended network stats, merge them together, and display
#     if use_extended_stats:
#         extended_stats = ox.extended_stats(G, ecc=True, bc=True, cc=True)
#         for key, value in extended_stats.items():
#             stats[key] = value
#     # -- unpack dicts into individiual keys:values
#     for k, count in stats['streets_per_node_counts'].items():
#         stats['int_{}_count'.format(k)] = count
#     for k, proportion in stats['streets_per_node_proportion'].items():
#         stats['int_{}_prop'.format(k)] = proportion
#
#     # -- delete the no longer needed dict elements
#     del stats['streets_per_node_counts']
#     del stats['streets_per_node_proportion']
#
#     # load as a pandas dataframe
#     df_stats = pd.DataFrame(pd.Series(stats, name='value'))
#
#     if verbose:
#         display(df_stats)
#
#     # calculate edge bearings
#     #     weight_by_length = True
#     Gu = ox.add_edge_bearings(ox.get_undirected(G))
#
#     bearings = {}
#     if weight_by_length:
#         # weight bearings by length (meters)
#         city_bearings = []
#         for u, v, k, d in Gu.edges(keys=True, data=True):
#             city_bearings.extend([d['bearing']] * int(d['length']))
#         b = pd.Series(city_bearings)
#         bearings[(lat_deg, lng_deg)] = pd.concat([b, b.map(reverse_bearing)]).reset_index(drop='True')
#     else:
#         # don't weight bearings, just take one value per street segment
#         b = pd.Series([d['bearing'] for u, v, k, d in Gu.edges(keys=True, data=True)])
#         bearings[(lat_deg, lng_deg)] = pd.concat([b, b.map(reverse_bearing)]).reset_index(drop='True')
#
#     #     breakpoint()
#     # Plot the queries network graph G_proj and polar historgram of bearings in this area
#     f = plt.Figure()
#     ax_g = f.add_subplot(121)
#     ax_g.axis('equal')
#     ox.plot_graph(G_proj, ax=ax_g, node_size=10, node_color='#66cc66')
#
#     # plot polar histogram
#     ax_polar = f.add_subplot(122, projection="polar")
#     title = f'{lat_deg:.2f}-{lng_deg:.2f}'
#     polar_plot(ax_polar, bearings[(lat_deg, lng_deg)].dropna(), title=title)
#
#     # add super title and save full image
#     # fig.savefig('images/street-orientations.png', dpi=120, bbox_inches='tight')
#     #     plt.show()
#     return f
#
#     # todo: put two figures side-by-side for each (lat,lng)
