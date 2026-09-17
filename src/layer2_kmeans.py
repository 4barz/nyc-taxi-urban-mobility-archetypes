"""Layer 2 — K-Means spatial clustering: zone-level demand archetypes (RQ1)."""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import config


def select_k(X, k_range=config.KMEANS_K_RANGE, random_state=config.RANDOM_STATE):
    inertias, sils = {}, {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit(X)
        inertias[k] = km.inertia_
        sils[k] = silhouette_score(X, km.labels_)
    best_k = max(sils, key=sils.get)
    return best_k, inertias, sils


def run_layer2(zone_profile: pd.DataFrame, exclude_airports=False, forced_k=None):
    df = zone_profile.dropna(subset=config.ZONE_FEATURES).copy()
    if exclude_airports:
        df = df[~df["Zone"].str.contains("Airport", case=False, na=False)]

    X = StandardScaler().fit_transform(df[config.ZONE_FEATURES].values)

    best_k, inertias, sils = select_k(X)
    k_used = forced_k if forced_k is not None else best_k
    km = KMeans(n_clusters=k_used, random_state=config.RANDOM_STATE, n_init=10).fit(X)
    df["kmeans_cluster"] = km.labels_

    profile_cols = ["trip_count", "mean_fare", "mean_distance", "pct_night", "pct_cash"]
    cluster_summary = (
        df.groupby("kmeans_cluster")[profile_cols]
        .mean()
        .join(df.groupby("kmeans_cluster").size().rename("n_zones"))
    )

    result = dict(
        best_k=best_k,
        k_used=k_used,
        inertias={str(k): v for k, v in inertias.items()},
        silhouettes={str(k): v for k, v in sils.items()},
        cluster_summary=cluster_summary.reset_index().to_dict(orient="records"),
        silhouette_k_used=silhouette_score(X, km.labels_),
    )
    return df, X, km, result


if __name__ == "__main__":
    zp = pd.read_parquet(config.PROCESSED_DIR / "zone_profile.parquet")
    df, X, km, result = run_layer2(zp)
    df.to_parquet(config.PROCESSED_DIR / "layer2_kmeans_zones.parquet")
    print(result)
