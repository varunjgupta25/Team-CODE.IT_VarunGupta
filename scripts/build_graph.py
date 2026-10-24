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
RADIUS_M   = 12_000          # 12 km around centre

OUTPUT_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "mira_bhayandar.graphml")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(OUTPUT_FILE):
        print(f"Graph already cached at {OUTPUT_FILE}")
        print("Delete the file and re-run to refresh.")
        return

    print(f"Downloading OSM drive network for Mira-Bhayandar "
          f"(centre={CENTRE_LAT},{CENTRE_LNG}, radius={RADIUS_M} m) …")
    print("This may take 1–3 minutes depending on your internet connection.")

    G = ox.graph_from_point(
        (CENTRE_LAT, CENTRE_LNG),
        dist=RADIUS_M,
        network_type="drive",
        simplify=True,
    )

    print("Adding edge speeds and travel times …")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    print(f"Saving graph to {OUTPUT_FILE} …")
    ox.save_graphml(G, OUTPUT_FILE)

    nodes = G.number_of_nodes()
    edges = G.number_of_edges()
    print(f"Done. Graph has {nodes} nodes and {edges} edges.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
