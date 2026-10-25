"""
scripts/build_graph.py

One-time script to download and cache the OSM road network for the
Mira-Bhayandar area as a GraphML file.

Usage:
    python scripts/build_graph.py

The file is saved to data/mira_bhayandar.graphml and is loaded at
startup by services/routing.py.
"""

import os
import sys

# Make sure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import osmnx as ox
except ImportError:
    print("ERROR: osmnx is not installed. Run:  pip install osmnx")
    sys.exit(1)

CENTRE_LAT = 19.2813
CENTRE_LNG = 72.8688
RADIUS_M   = 6_000          # 6 km around centre (optimized for memory <350MB and file size <40MB)

OUTPUT_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "mira_bhayandar.graphml")


def prune_graph_attributes(G):
    """
    Remove unnecessary metadata tags from nodes and edges to keep GraphML
    compact, load fast, and stay well under 40 MB / 350 MB RAM limits.
    """
    essential_node_attrs = {"x", "y"}
    for _, data in G.nodes(data=True):
        keys_to_remove = [k for k in data if k not in essential_node_attrs]
        for k in keys_to_remove:
            del data[k]

    essential_edge_attrs = {"length", "travel_time", "speed_kph", "oneway"}
    for _, _, _, data in G.edges(keys=True, data=True):
        keys_to_remove = [k for k in data if k not in essential_edge_attrs]
        for k in keys_to_remove:
            del data[k]
    return G


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Downloading OSM drive network for Mira-Bhayandar "
          f"(centre={CENTRE_LAT},{CENTRE_LNG}, radius={RADIUS_M} m) …")

    G = ox.graph_from_point(
        (CENTRE_LAT, CENTRE_LNG),
        dist=RADIUS_M,
        network_type="drive",
        simplify=True,
    )

    print("Adding edge speeds and travel times …")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    print("Pruning unneeded metadata attributes for compact size …")
    G = prune_graph_attributes(G)

    print(f"Saving graph to {OUTPUT_FILE} …")
    ox.save_graphml(G, OUTPUT_FILE)

    nodes = G.number_of_nodes()
    edges = G.number_of_edges()
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Done. Graph has {nodes} nodes and {edges} edges.")
    print(f"Saved to: {OUTPUT_FILE} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
