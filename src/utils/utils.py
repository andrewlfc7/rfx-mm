from numba.types import Array
import numpy as np
from numba import njit
from numba.types import float64
from typing import Optional


@njit(error_model="numpy", fastmath=True)
def geometric_weights(num: int, r: Optional[float] = None) -> np.ndarray[float]:
    """
    Generates a list of `num` weights that follow a geometric distribution and sum to 1.

    Parameters
    ----------
    num : int
        The number of weights to generate.

    r : float, optional
        The common ratio of the geometric sequence. Must be strictly between 0 and 1. The default value is 0.75.

    Returns
    -------
    np.ndarray
        An array of normalized geometric weights from lowest -> highest.
    """
    assert num > 1, "Number of weights generated cannot be <1."
    r = r if r is not None else 0.75
    weights = np.array([r**i for i in range(num)], dtype=float64)
    normalized = weights / weights.sum()
    return normalized



@njit(["float64[:](float64[:])"], error_model="numpy", fastmath=True)
def nbdiff_1d(arr: Array) -> Array:
    """
    Compute the differences between consecutive elements of a 1D array.
    Numba-optimized version of numpy.diff.

    Parameters
    ----------
    arr : Array
        Input array

    Returns
    -------
    Array
        Array of differences between consecutive elements
    """
    diff = np.empty(arr.size - 1, dtype=np.float64)
    for i in range(arr.size - 1):
        diff[i] = arr[i + 1] - arr[i]
    return diff



def generate_geometric_weights(num: int, r: float = 0.5, reverse: bool = False) -> np.ndarray:
    """Generate geometric weights for order sizes"""
    weights = np.array([r ** i for i in range(num)])
    weights = weights / weights.sum()  # Normalize
    return weights[::-1] if reverse else weights

def geomspace(start: float, end: float, n: int) -> np.ndarray:
    """Generate geometric sequence of prices"""
    return np.geomspace(start, end, n)
