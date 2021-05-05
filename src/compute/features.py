import osmnx as ox


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