from random import Random
from typing import TypeVar

def bernoulli(prob: float, rng: Random) -> bool:
    if prob <= 0.0:
        return False
    if 1.0 <= prob:
        return True
    return rng.random() < prob

T = TypeVar('T')
def weighted_select(options: list[T], weight_map: dict[T, float], rng: Random) -> T:

    if len(options) == 0:
        raise ValueError("unable to select from empty options")

    weights: list[float] = []
    for option in options:
        if not option in weight_map:
            raise ValueError(f"unable to find weight for option '{option}'")
        weights.append(weight_map[option])

    elem, *_ = rng.choices(options, weights = weights, k = 1)

    return elem