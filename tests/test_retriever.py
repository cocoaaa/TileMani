import osmnx as ox
from src.retrieve.retriever import get_road_graph_and_bbox
from src.rasterize.rasterizer import plot_figure_ground

def test_get_road_graph_and_bbox(tileXYZ):
    G_r, bbox = get_road_graph_and_bbox(tileXYZ)
    print("Manual bbox: ", bbox)
    f1, ax1 = ox.plot_graph(G_r)
    f1.show()
    f2, ax2 = ox.plot_figure_ground(G_r)
    f2.show()
    f3, ax3 = plot_figure_ground(G_r, bbox)
    f3.show()
    figs = [f1, f2, f3]
    for f in figs:
        f.suptitle(f"{tileXYZ}")


def test_get_road_graph_and_bbox_8301_5639_14():
    tileXYZ = (8301, 5639, 14)
    test_get_road_graph_and_bbox(tileXYZ)


def test_get_road_graph_and_bbox_8301_5637_14():
    tileXYZ = (8301, 5637, 14)
    test_get_road_graph_and_bbox(tileXYZ)



