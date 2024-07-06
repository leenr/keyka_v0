import enum
from enum import Enum


@enum.unique
class MemCmpResult(int, Enum):
    LESS = -1
    EQUAL = 0
    GREATER = 1


def memcmp(mv1: memoryview, mv2: memoryview) -> MemCmpResult:
    # implementation of `memcmp`
    it1 = iter(mv1)
    it2 = iter(mv2)
    while True:
        b1 = next(it1, -1)
        b2 = next(it2, -1)
        if b1 == -1 and b2 == -1:
            # both iterators are exhausted
            return MemCmpResult.EQUAL
        elif b1 > b2:
            return MemCmpResult.GREATER
        elif b1 < b2:
            return MemCmpResult.LESS


__all__ = (
    'MemCmpResult', 'memcmp'
)
