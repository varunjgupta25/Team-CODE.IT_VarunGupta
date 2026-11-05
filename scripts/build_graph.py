"""
scripts/build_graph.py

One-time script to download and cache the OSM road network for the
Mira-Bhayandar area as a GraphML file.

Usage:
    python scripts/build_graph.py

The file is saved to data/mira_bhayandar.graphml and is loaded at
startup by services/routing.py.

Retries across multiple public Overpass API mirrors if the primary
server is at capacity.
"""

import os
import sys
import time

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

# Public Overpass API mirrors to try in order (each ending WITHOUT trailing slash)
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
    "https://overpass.openstreetmap.fr/api",
]

MAX_RETRIES = 3
RETRY_DELAY = 15   # seconds between attempts per mirror


def download_graph() -> object:
    """
    Attempt to download the OSM drive network, cycling through mirrors with
    exponential back-off on HTTP 429/502/503 responses.
    Raises RuntimeError if all mirrors fail.
    """
    last_exc = None
    for mirror in OVERPASS_MIRRORS:
        ox.settings.overpass_url = mirror
        print(f"\n  Trying mirror: {mirror}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                G = ox.graph_from_point(
                    (CENTRE_LAT, CENTRE_LNG),
                    dist=RADIUS_M,
                    network_type="drive",
                    simplify=True,
                )
                print(f"  Success on attempt {attempt}.")
                return G
            except Exception as exc:
                last_exc = exc
                wait = RETRY_DELAY * attempt
                print(f"  Attempt {attempt}/{MAX_RETRIES} failed: {exc!s:.120}")
                if attempt < MAX_RETRIES:
                    print(f"  Waiting {wait}s before retry …")
                    time.sleep(wait)
        print(f"  All {MAX_RETRIES} attempts failed for {mirror}.")

    raise RuntimeError(
        f"All Overpass mirrors failed. Last error: {last_exc}"
    ) from last_exc


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

    if os.path.exists(OUTPUT_FILE):
        print(f"Graph already cached at {OUTPUT_FILE}")
        print("Delete the file and re-run to refresh.")
        return

    print(f"Downloading OSM drive network for Mira-Bhayandar "
          f"(centre={CENTRE_LAT},{CENTRE_LNG}, radius={RADIUS_M} m) …")
    print("This may take several minutes depending on server load.")

    try:
        G = download_graph()
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        print(
            "\nAll public Overpass servers are busy or unreachable.\n"
            "Please try again in a few minutes, or use a VPN / different\n"
            "network connection. The routing service will automatically use\n"
            "Haversine straight-line fallback until this file exists."
        )
        sys.exit(1)

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
