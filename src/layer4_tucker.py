"""Layer 4 — Non-negative Tucker decomposition of the Zone x Hour x DayType
demand tensor (RQ3)."""

import numpy as np
import tensorly as tl
from tensorly.decomposition import non_negative_tucker

from . import config

tl.set_backend("numpy")


def _reconstruction_error(tensor, core, factors):
    recon = tl.tucker_to_tensor((core, factors))
    return float(tl.norm(tensor - recon) / tl.norm(tensor))


def rank_sensitivity(tensor, ranks=config.TUCKER_CANDIDATE_RANKS, random_state=config.RANDOM_STATE):
    errors = {}
    for rank in ranks:
        core, factors = non_negative_tucker(
            tensor, rank=list(rank), init="random", random_state=random_state, n_iter_max=200
        )
        errors[str(rank)] = _reconstruction_error(tensor, core, factors)
    return errors


def run_layer4(tensor_counts: np.ndarray, primary_rank=config.TUCKER_PRIMARY_RANK):
    # drop the unused zone-index-0 row -> tensor of shape (263, 24, 2)
    # float64 + random init: the default 'svd' init causes multiplicative-update
    # overflow (NaNs) on this tensor's scale, so we use random non-negative init.
    tensor = tl.tensor(tensor_counts[1:, :, :], dtype=tl.float64)

    sensitivity = rank_sensitivity(tensor)

    core, factors = non_negative_tucker(
        tensor, rank=list(primary_rank), init="random",
        random_state=config.RANDOM_STATE, n_iter_max=500
    )
    zone_factors, hour_factors, daytype_factors = factors
    explained_variance = 1 - _reconstruction_error(tensor, core, factors) ** 2

    result = dict(
        primary_rank=list(primary_rank),
        reconstruction_error=_reconstruction_error(tensor, core, factors),
        explained_variance=explained_variance,
        rank_sensitivity=sensitivity,
    )
    return core, zone_factors, hour_factors, daytype_factors, result


if __name__ == "__main__":
    tc = np.load(config.PROCESSED_DIR / "tensor_counts.npy")
    core, zf, hf, df_, result = run_layer4(tc)
    np.save(config.PROCESSED_DIR / "layer4_core.npy", tl.to_numpy(core))
    np.save(config.PROCESSED_DIR / "layer4_zone_factors.npy", tl.to_numpy(zf))
    np.save(config.PROCESSED_DIR / "layer4_hour_factors.npy", tl.to_numpy(hf))
    np.save(config.PROCESSED_DIR / "layer4_daytype_factors.npy", tl.to_numpy(df_))
    print(result)
