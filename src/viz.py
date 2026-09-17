"""Figure generation for all six pipeline layers. Saves PNGs to reports/figures/."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config

sns.set_theme(style="whitegrid", context="talk", font_scale=0.7)
PALETTE = sns.color_palette("tab10")


def _save(fig, name):
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES_DIR / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Layer 2 — K-Means
# ---------------------------------------------------------------------------
def plot_kmeans_selection(inertias, sils, best_k):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ks = sorted(inertias.keys(), key=int)
    axes[0].plot([int(k) for k in ks], [inertias[k] for k in ks], "o-", color=PALETTE[0])
    axes[0].set_title("Elbow method (inertia)")
    axes[0].set_xlabel("k")
    axes[0].set_ylabel("Inertia")
    axes[0].axvline(best_k, ls="--", color="grey")

    axes[1].plot([int(k) for k in ks], [sils[k] for k in ks], "o-", color=PALETTE[1])
    axes[1].set_title("Silhouette score")
    axes[1].set_xlabel("k")
    axes[1].axvline(best_k, ls="--", color="grey")
    fig.suptitle("Layer 2 — K-Means model selection (zone demand archetypes)")
    return _save(fig, "layer2_kmeans_selection.png")


def plot_kmeans_violins(df, cluster_col="kmeans_cluster"):
    features = ["trip_count", "mean_fare", "mean_distance", "pct_night", "pct_cash"]
    fig, axes = plt.subplots(1, len(features), figsize=(4 * len(features), 4.2))
    plot_df = df.copy()
    plot_df["trip_count"] = np.log10(plot_df["trip_count"] + 1)
    for ax, feat in zip(axes, features):
        sns.violinplot(
            data=plot_df, x=cluster_col, y=feat, hue=cluster_col,
            ax=ax, palette=PALETTE, legend=False, cut=0,
        )
        label = "log10(trip_count)" if feat == "trip_count" else feat
        ax.set_title(label)
        ax.set_xlabel("Cluster")
        ax.set_ylabel("")
    fig.suptitle("Layer 2 — Zone-level cluster portraits (K-Means)")
    fig.tight_layout()
    return _save(fig, "layer2_kmeans_violins.png")


# ---------------------------------------------------------------------------
# Layer 3 — K-Shape
# ---------------------------------------------------------------------------
def plot_kshape_selection(sils, best_k):
    fig, ax = plt.subplots(figsize=(6, 4))
    ks = sorted(sils.keys(), key=int)
    ax.plot([int(k) for k in ks], [sils[k] for k in ks], "o-", color=PALETTE[2])
    ax.axvline(best_k, ls="--", color="grey")
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette score")
    ax.set_title("Layer 3 — K-Shape model selection (rhythm archetypes)")
    return _save(fig, "layer3_kshape_selection.png")


def plot_kshape_centroids(centroids):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, c in enumerate(centroids):
        ax.plot(range(24), c.ravel(), marker="o", label=f"Rhythm {i}", color=PALETTE[i])
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Z-normalised demand shape")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    ax.set_title("Layer 3 — K-Shape rhythm centroids")
    return _save(fig, "layer3_kshape_centroids.png")


# ---------------------------------------------------------------------------
# Layer 4 — Tucker
# ---------------------------------------------------------------------------
def plot_tucker_rank_sensitivity(sensitivity, primary_rank):
    fig, ax = plt.subplots(figsize=(7, 4))
    ranks = list(sensitivity.keys())
    errs = [sensitivity[r] for r in ranks]
    colors = [PALETTE[3] if r == str(list(primary_rank)) else PALETTE[7] for r in ranks]
    ax.bar(ranks, errs, color=colors)
    ax.set_ylabel("Relative reconstruction error")
    ax.set_xlabel("Tucker core rank (zone, hour, daytype)")
    ax.set_title("Layer 4 — Tucker rank sensitivity")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    return _save(fig, "layer4_tucker_rank_sensitivity.png")


def plot_tucker_hour_factors(hour_factors):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i in range(hour_factors.shape[1]):
        ax.plot(range(24), hour_factors[:, i], marker="o", label=f"Temporal component {i}", color=PALETTE[i])
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Component loading")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    ax.set_title("Layer 4 — Tucker temporal (hour-mode) component loadings")
    return _save(fig, "layer4_tucker_hour_factors.png")


def plot_tucker_zone_scatter(zone_factors, zone_profile):
    df = zone_profile[["zone_id", "Borough"]].dropna().copy()
    df = df[df.zone_id <= zone_factors.shape[0]]
    df["zf0"] = zone_factors[df.zone_id.values - 1, 0]
    df["zf1"] = zone_factors[df.zone_id.values - 1, 1]

    fig, ax = plt.subplots(figsize=(7, 6))
    sns.scatterplot(data=df, x="zf0", y="zf1", hue="Borough", palette=PALETTE, ax=ax, s=45)
    ax.set_xlabel("Zone factor component 0")
    ax.set_ylabel("Zone factor component 1")
    ax.set_title("Layer 4 — Tucker zone-mode factors (first two components)")
    return _save(fig, "layer4_tucker_zone_scatter.png")


# ---------------------------------------------------------------------------
# Layer 5 — Isolation Forest
# ---------------------------------------------------------------------------
def plot_isoforest_scatter(df):
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.scatterplot(
        data=df.sample(min(40_000, len(df)), random_state=config.RANDOM_STATE),
        x="fare_amount", y="speed_mph", hue="is_anomaly",
        palette={False: PALETTE[0], True: PALETTE[3]}, alpha=0.5, s=12, ax=ax,
    )
    ax.set_xlabel("Fare amount ($)")
    ax.set_ylabel("Speed (mph)")
    ax.set_title("Layer 5 — Isolation Forest anomaly flags (trip-level sample)")
    return _save(fig, "layer5_isoforest_scatter.png")


def plot_isoforest_zone_heatmap(zone_rate, zone_profile, min_sampled=30, top_n=15):
    df = zone_rate.merge(zone_profile[["zone_id", "Zone", "Borough"]], on="zone_id", how="left")
    df = df[df.n_sampled >= min_sampled].sort_values("anomaly_rate", ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(data=df, y="Zone", x="anomaly_rate", hue="Borough", dodge=False, palette=PALETTE, ax=ax)
    ax.set_xlabel("Anomaly rate")
    ax.set_ylabel("")
    ax.set_title(f"Layer 5 — Highest anomaly-rate zones (n_sampled ≥ {min_sampled})")
    return _save(fig, "layer5_isoforest_zone_heatmap.png")


# ---------------------------------------------------------------------------
# Layer 6 — UMAP
# ---------------------------------------------------------------------------
def plot_umap(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(data=df, x="umap_x", y="umap_y", hue="Borough", palette=PALETTE, s=55, ax=axes[0])
    axes[0].set_title("UMAP zone fingerprint — coloured by Borough")

    sns.scatterplot(
        data=df, x="umap_x", y="umap_y", hue="kmeans_cluster", palette=PALETTE, s=55, ax=axes[1]
    )
    axes[1].set_title("UMAP zone fingerprint — coloured by K-Means cluster (Layer 2)")
    fig.suptitle("Layer 6 — UMAP unified zone fingerprint (RQ5)")
    fig.tight_layout()
    return _save(fig, "layer6_umap.png")


def plot_umap_vs_pca(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(data=df, x="umap_x", y="umap_y", hue="Borough", palette=PALETTE, s=45, ax=axes[0], legend=False)
    axes[0].set_title("UMAP embedding")
    sns.scatterplot(data=df, x="pca_x", y="pca_y", hue="Borough", palette=PALETTE, s=45, ax=axes[1])
    axes[1].set_title("PCA baseline (2 components)")
    fig.suptitle("Layer 6 — UMAP vs. PCA validation comparison")
    fig.tight_layout()
    return _save(fig, "layer6_umap_vs_pca.png")
