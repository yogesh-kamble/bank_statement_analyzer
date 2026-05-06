from typing import Callable
from . import icici

_REGISTRY = {
    "icici": icici.normalize,
}

def get_normalizer(bank: str) -> Callable[[str], list]:
    """
    Return the normalizer function for the given bank key.
    Raises KeyError if not found.
    """
    key = (bank or "").strip().lower()
    if key in _REGISTRY:
        return _REGISTRY[key]
    raise KeyError(f"No normalizer registered for bank '{bank}'")
