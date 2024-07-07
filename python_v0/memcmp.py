import enum
from enum import Enum
from itertools import zip_longest


@enum.unique
class MemCmpResult(int, Enum):
    LESS = -1
    EQUAL = 0
    GREATER = 1


def memcmp(mv1: memoryview, mv2: memoryview) -> MemCmpResult:
    # implementation of `memcmp`

    for b1, b2 in zip_longest(mv1, mv2, fillvalue=-1):
        if b1 > b2:
            return MemCmpResult.GREATER
        elif b1 < b2:
            return MemCmpResult.LESS

    return MemCmpResult.EQUAL


__all__ = (
    'MemCmpResult', 'memcmp'
)
