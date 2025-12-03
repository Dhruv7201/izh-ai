import math
import numpy as np
from typing import List, Dict, Any
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
import hdbscan



def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def cluster_with_hdbscan(coords):
    """Try HDBSCAN for natural clustering."""
    clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric='haversine')
    labels = clusterer.fit_predict(coords)
    return labels


def cluster_with_kmeans(coords, num_clusters):
    model = KMeans(n_clusters=num_clusters, n_init="auto")
    labels = model.fit_predict(coords)
    return labels


def cluster_with_knn(coords, num_groups):
    """Group POIs into nearest-neighbor routes."""
    nbrs = NearestNeighbors(n_neighbors=min(2, len(coords)), algorithm='ball_tree').fit(coords)
    distances, indices = nbrs.kneighbors(coords)

    # Assign cluster labels based on nearest neighbor chain
    labels = [-1] * len(coords)
    current_label = 0

    for i in range(len(coords)):
        if labels[i] == -1:
            labels[i] = current_label
            for j in indices[i]:
                labels[j] = current_label
            current_label += 1

    # Reduce to desired group count
    while current_label > num_groups:
        for i in range(len(labels)):
            labels[i] = labels[i] % num_groups
        current_label = num_groups

    return labels


def cluster_pois(pois: List[Dict[str, Any]], num_days: int):
    """Smart geographic clustering with fallback strategies."""

    if not pois:
        return []

    coords = np.array([[p['lat'], p['lon']] for p in pois])

    # Convert to radians for HDBSCAN haversine
    coords_rad = np.radians(coords)

    # Step 1: Try HDBSCAN (best natural clusters)
    if len(coords) >= 3:
        labels = cluster_with_hdbscan(coords_rad)
        if len(set(labels)) > 1:  # meaningful clusters found
            return build_cluster_output(labels, pois)

    # Step 2: Try adaptive k-means
    k = min(num_days, len(coords))
    if k > 1:
        labels = cluster_with_kmeans(coords, k)
        return build_cluster_output(labels, pois)

    # Step 3: Fallback to KNN grouping
    labels = cluster_with_knn(coords, num_groups=num_days)
    return build_cluster_output(labels, pois)


def build_cluster_output(labels, pois):
    clusters = {}
    for label, poi in zip(labels, pois):
        clusters.setdefault(int(label), []).append(poi)

    return [{"cluster_id": cid, "pois": pois} for cid, pois in clusters.items()]


if __name__ == "__main__":
    # Test clustering
    test_pois = [
        {"name": "POI 1", "lat": 40.7128, "lon": -74.0060},
        {"name": "POI 2", "lat": 40.7138, "lon": -74.0050},
        {"name": "POI 3", "lat": 34.0522, "lon": -118.2437},
        {"name": "POI 4", "lat": 34.0520, "lon": -118.2440},
        {"name": "POI 5", "lat": 51.5074, "lon": -0.1278},
    ]
    clustered = cluster_pois(test_pois, num_days=2)
    for cluster in clustered:
        print(f"Cluster {cluster['cluster_id']}: {[poi['name'] for poi in cluster['pois']]}")