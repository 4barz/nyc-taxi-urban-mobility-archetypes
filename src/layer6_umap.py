"""Layer 6 — UMAP unified zone fingerprint embedding (RQ5)."""

import numpy as np
import pandas as pd
import umap
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from . import config


def build_fingerprint(zone_profile, zone_factors, zone_anomaly_rate):
    """17-D fingerprint = 10 K-Means features + 6 Tucker zone factors + 1 anomaly rate."""
    df = zone_profile[["zone_id", "Borough", "Zone"] + config.ZONE_FEATURES].dropna().copy()

    n_tucker_dims = zone_factors.shape[1]
    tucker_cols = [f"tucker_zf_{i}" for i in range(n_tucker_dims)]
    tucker_df = pd.DataFrame(zone_factors, columns=tucker_cols)
    tucker_df["zone_id"] = np.arange(1, len(zone_factors) + 1)

    df = df.merge(tucker_df, on="zone_id", how="left")
    df = df.merge(
        zone_anomaly_rate[["zone_id", "anomaly_rate"]], on="zone_id", how="left"
    )
    df["anomaly_rate"] = df["anomaly_rate"].fillna(0.0)

    feature_cols = config.ZONE_FEATURES + tucker_cols + ["anomaly_rate"]
    X = StandardScaler().fit_transform(df[feature_cols].values)
    return df, X, feature_cols


def run_layer6(zone_profile, zone_factors, zone_anomaly_rate):
    df, X, feature_cols = build_fingerprint(zone_profile, zone_factors, zone_anomaly_rate)

    reducer = umap.UMAP(
        n_neighbors=config.UMAP_N_NEIGHBORS,
        min_dist=config.UMAP_MIN_DIST,
        n_components=2,
        random_state=config.RANDOM_STATE,
    )
    embedding = reducer.fit_transform(X)
    df["umap_x"], df["umap_y"] = embedding[:, 0], embedding[:, 1]

    # PCA baseline for the validation comparison (Section 5 of proposal)
    pca = PCA(n_components=2, random_state=config.RANDOM_STATE)
    pca_embedding = pca.fit_transform(X)
    df["pca_x"], df["pca_y"] = pca_embedding[:, 0], pca_embedding[:, 1]

    result = dict(
        n_zones=len(df),
        n_fingerprint_dims=len(feature_cols),
        fingerprint_features=feature_cols,
        pca_explained_variance_ratio=pca.explained_variance_ratio_.tolist(),
    )
    return df, result


if __name__ == "__main__":
    zp = pd.read_parquet(config.PROCESSED_DIR / "zone_profile.parquet")
    zf = np.load(config.PROCESSED_DIR / "layer4_zone_factors.npy")
    zar = pd.read_parquet(config.PROCESSED_DIR / "layer5_zone_anomaly_rate.parquet")
    df, result = run_layer6(zp, zf, zar)
    df.to_parquet(config.PROCESSED_DIR / "layer6_umap_zones.parquet")
    print(result)
