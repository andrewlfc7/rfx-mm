
import numpy as np
from numba import njit
from numba.types import float64, Array
from utils.utils import geometric_weights


@njit(["float64(float64[:, :], float64[:, :], float64[:])"], error_model="numpy", fastmath=True)
def orderbook_imbalance(bids: Array, asks: Array, depths: Array) -> float:
    """
    Calculates the geometrically weighted order book imbalance across different price depths.

    This function computes the logarithm of the ratio of total bid size to total ask size within
    specified depths, applying a geometric weighted scheme for aggregation.

    Depths are expected in basis points and converted internally to decimal form. The function
    assumes the first entry in both bids and asks arrays represents the best (highest) bid and
    the best (lowest) ask, respectively.

    Parameters
    ----------
    bids : Array
        An array of bid prices and quantities.

    asks : Array
        An array of ask prices and quantities.

    depths : Array
        An array of price depths (in basis points) at which to calculate imbalance.

    Returns
    -------
    float
        The geometrically weighted imbalance across specified price depths.

    Notes
    -----
    - Depths are converted from basis points (BPS) to decimals within the function.

    """
    num_depths = depths.size
    depths = depths / 1e-4  # NOTE: BPS -> Decimals
    weights = geometric_weights(num_depths)
    imbalances = np.empty(num_depths, dtype=np.float64)

    bid_p, bid_q = bids.T
    ask_p, ask_q = asks.T
    best_bid_p, best_ask_p = bid_p[0], ask_p[0]

    for i in range(num_depths):
        min_bid = best_bid_p * (1.0 - depths[i])
        max_ask = best_ask_p * (1.0 + depths[i])

        num_bids_within_depth = bid_p[bid_p >= min_bid].size
        num_asks_within_depth = ask_p[ask_p <= max_ask].size
        total_bid_size_within_depth = np.sum(bid_q[:num_bids_within_depth])
        total_ask_size_within_depth = np.sum(ask_q[:num_asks_within_depth])

        imbalances[i] = np.log(
            total_bid_size_within_depth / total_ask_size_within_depth
        )

    weighted_imbalance = np.sum(imbalances * weights)

    return weighted_imbalance
