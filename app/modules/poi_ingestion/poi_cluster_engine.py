import math
import numpy as np
from typing import List, Dict, Any
from sklearn.cluster import DBSCAN
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


def cluster_with_hdbscan(coords, min_cluster_size=3, min_samples=2):
    """Use HDBSCAN for natural density-based clustering based on distance."""
    # Adjust min_cluster_size based on total POIs
    if len(coords) < 10:
        min_cluster_size = 2
    elif len(coords) < 50:
        min_cluster_size = 3
    else:
        min_cluster_size = max(3, len(coords) // 50)  # Scale with data size
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='haversine',
        cluster_selection_epsilon=0.0  # Pure distance-based, no epsilon merging
    )
    labels = clusterer.fit_predict(coords)
    return labels


def cluster_with_dbscan_fallback(coords, eps_km=2.0):
    """Fallback DBSCAN-like clustering with distance threshold."""
    # Convert eps from km to approximate degrees (rough approximation)
    # 1 degree latitude ≈ 111 km
    eps_deg = eps_km / 111.0
    
    clusterer = DBSCAN(eps=eps_deg, min_samples=2, metric='haversine')
    labels = clusterer.fit_predict(coords)
    return labels


def cluster_with_knn_distance(coords, max_distance_km=2.0):
    """Group POIs using nearest neighbors with distance threshold."""
    nbrs = NearestNeighbors(
        n_neighbors=min(10, len(coords)), 
        algorithm='ball_tree',
        metric='haversine'
    ).fit(coords)
    
    distances, indices = nbrs.kneighbors(coords)
    
    # Convert max_distance to radians (haversine uses radians)
    max_distance_rad = max_distance_km / 6371.0
    
    # Assign cluster labels based on nearest neighbor chain within distance
    labels = [-1] * len(coords)
    current_label = 0
    visited = set()
    
    for i in range(len(coords)):
        if i in visited:
            continue
            
        # Start new cluster
        queue = [i]
        labels[i] = current_label
        visited.add(i)
        
        while queue:
            current = queue.pop(0)
            for j, dist in zip(indices[current], distances[current]):
                if j != current and dist <= max_distance_rad and j not in visited:
                    labels[j] = current_label
                    visited.add(j)
                    queue.append(j)
        
        current_label += 1
    
    return labels


def cluster_pois(pois: List[Dict[str, Any]]):
    """
    Cluster POIs purely based on geographic distance.
    Returns clusters with IDs like 'cluster_1', 'cluster_2', etc.
    """

    if not pois:
        return []

    if len(pois) == 1:
        # Single POI gets its own cluster
        return [{"cluster_id": "cluster_1", "pois": pois}]

    coords = np.array([[p['lat'], p['lng']] for p in pois])

    # Convert to radians for haversine distance calculations
    coords_rad = np.radians(coords)

    # Step 1: Try HDBSCAN (best for natural density-based clusters)
    if len(coords) >= 3:
        labels = cluster_with_hdbscan(coords_rad)
        unique_labels = set(labels)
        # Filter out noise points (label -1) for cluster count
        cluster_labels = [l for l in unique_labels if l != -1]
        
        if len(cluster_labels) > 0:
            return build_cluster_output(labels, pois, include_noise=True)

    # Step 2: Try DBSCAN fallback with distance threshold
    if len(coords) >= 2:
        labels = cluster_with_dbscan_fallback(coords_rad, eps_km=2.0)
        unique_labels = set(labels)
        cluster_labels = [l for l in unique_labels if l != -1]
        
        if len(cluster_labels) > 0:
            return build_cluster_output(labels, pois, include_noise=True)

    # Step 3: Fallback to KNN distance-based grouping
    labels = cluster_with_knn_distance(coords_rad, max_distance_km=2.0)
    return build_cluster_output(labels, pois, include_noise=False)


def build_cluster_output(labels, pois, include_noise=True):
    """Build cluster output with cluster IDs as 'cluster_1', 'cluster_2', etc."""
    clusters = {}
    noise_cluster = []
    
    for label, poi in zip(labels, pois):
        if label == -1 and include_noise:
            # Noise points (outliers) go into a separate cluster
            noise_cluster.append(poi)
        else:
            clusters.setdefault(int(label), []).append(poi)
    
    # Build output with named clusters
    result = []
    cluster_num = 1
    
    # Add regular clusters
    for label in sorted(clusters.keys()):
        result.append({
            "cluster_id": f"cluster_{cluster_num}",
            "pois": clusters[label]
        })
        cluster_num += 1
    
    # Add noise cluster if any
    if noise_cluster:
        result.append({
            "cluster_id": f"cluster_{cluster_num}",
            "pois": noise_cluster
        })
    
    return result


if __name__ == "__main__":
    # Test clustering
    test_pois = [
        {"name": "POI 1", "lat": 40.7128, "lng": -74.0060},
        {"name": "POI 2", "lat": 40.7138, "lng": -74.0050},
        {"name": "POI 3", "lat": 34.0522, "lng": -118.2437},
        {"name": "POI 4", "lat": 34.0520, "lng": -118.2440},
        {"name": "POI 5", "lat": 51.5074, "lng": -0.1278},
    ]
    clustered = cluster_pois(test_pois)
