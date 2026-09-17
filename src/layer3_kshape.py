"""Layer 3 — K-Shape temporal rhythm clustering (RQ2).

Clusters zones by the *shape* of their 24-hour demand profile, independent of
absolute volume, by first normalising each zone's hourly counts to a
fractional share (sums to 1 across 24 hours) and then z-normalising that
shape (mean 0, unit variance) before shape-based clustering — this decouples
rhythm from both scale and offset.
"""

import numpy as np
import pandas as pd
from tslearn.clustering import KShape, silhouette_score as ts_silhouette_score
from tslearn.preprocessing import TimeSeriesScalerMeanVariance

from . import config


def build_hourly_profiles(zone_profile: pd.DataFrame, tensor_counts: np.ndarray):
    """Return (active_zone_ids, fractional_share_matrix[n_active, 24])."""
    hourly_counts = tensor_counts.sum(axis=2)  # (zone, hour), collapse daytype
    zone_ids = zone_profile["zone_id"].values
    total_trips = zone_profile.set_index("zone_id")["trip_count"]

    avg_daily = total_trips / config.N_DAYS_IN_STUDY
    active_ids = avg_daily[avg_daily >= config.MIN_TRIPS_PER_DAY_FOR_RHYTHM].index.values

    rows = []
    kept_ids = []
    for zid in active_ids:
        counts = hourly_counts[int(zid)]
        s = counts.sum()
        if s <= 0:
            continue
        rows.append(counts / s)
        kept_ids.append(zid)

    return np.array(kept_ids), np.vstack(rows)


def select_k(X_scaled, k_range=config.KSHAPE_K_RANGE, random_state=config.RANDOM_STATE):
    sils = {}
    models = {}
    for k in k_range:
        ks = KShape(n_clusters=k, random_state=random_state, n_init=5).fit(X_scaled)
        labels = ks.labels_
        if len(set(labels)) < 2:
            continue
        sil = ts_silhouette_score(X_scaled, labels, metric="euclidean")
        sils[k] = sil
        models[k] = ks
    best_k = max(sils, key=sils.get)
    return best_k, models[best_k], sils


def run_layer3(zone_profile: pd.DataFrame, tensor_counts: np.ndarray):
    zone_ids, shares = build_hourly_profiles(zone_profile, tensor_counts)
    X_scaled = TimeSeriesScalerMeanVariance().fit_transform(shares)

    best_k, model, sils = select_k(X_scaled)
    labels = model.labels_

    rhythm_df = pd.DataFrame({"zone_id": zone_ids, "rhythm_cluster": labels})
    rhythm_df = rhythm_df.merge(
        zone_profile[["zone_id", "Borough", "Zone", "trip_count"]], on="zone_id", how="left"
    )

    centroids = model.cluster_centers_.reshape(best_k, -1)

    result = dict(
        n_active_zones=len(zone_ids),
        best_k=best_k,
        silhouettes={str(k): v for k, v in sils.items()},
        borough_mix={
            str(c): rhythm_df.loc[rhythm_df.rhythm_cluster == c, "Borough"]
            .value_counts()
            .to_dict()
            for c in range(best_k)
        },
    )
    return rhythm_df, shares, centroids, result


if __name__ == "__main__":
    zp = pd.read_parquet(config.PROCESSED_DIR / "zone_profile.parquet")
    tc = np.load(config.PROCESSED_DIR / "tensor_counts.npy")
    rhythm_df, shares, centroids, result = run_layer3(zp, tc)
    rhythm_df.to_parquet(config.PROCESSED_DIR / "layer3_kshape_zones.parquet")
    np.save(config.PROCESSED_DIR / "layer3_centroids.npy", centroids)
    print(result)
