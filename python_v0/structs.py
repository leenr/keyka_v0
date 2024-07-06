import struct


# little-endian uint16
KEY_SIZE_STRUCT = struct.Struct('<' + 'H')

# little-endian int32 (negative is "leaf", positive is "branch")
OFFSET_STRUCT = struct.Struct('<' + 'i')

# little-endian uint64 (value)
LEAF_NODE_HEADER_STRUCT = struct.Struct('<' + 'Q')

# little-endian uint64 (value)
# 2 x little-endian int32 (left + right offset)
BRANCH_NODE_HEADER_STRUCT = struct.Struct(
    '<' + 'Q' + f'2{OFFSET_STRUCT.format[-1]}'
)

# `\x08` = 8 bit value
# `\x00` in the middle = v0
MAGIC_BYTES = b'\x00Key\x00Ka\x08'


__all__ = (
    'BRANCH_NODE_HEADER_STRUCT',
    'KEY_SIZE_STRUCT',
    'LEAF_NODE_HEADER_STRUCT',
    'MAGIC_BYTES',
    'OFFSET_STRUCT'
)
