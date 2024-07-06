import code
import inspect
import io
import mmap
import sys
from collections.abc import Buffer
from pathlib import Path
from typing import Final, NamedTuple

from .memcmp import MemCmpResult, memcmp
from .structs import (
    BRANCH_NODE_HEADER_STRUCT, KEY_SIZE_STRUCT, LEAF_NODE_HEADER_STRUCT,
    MAGIC_BYTES, OFFSET_STRUCT
)


NULL: Final = 0


class _Node(NamedTuple):
    key_mv: memoryview
    value: int
    right_offset: int = NULL
    left_offset: int = NULL


class KeyKaReader:
    __slots__ = (
        '_mv',
        '_root_node'
    )

    def __init__(self, mv: memoryview) -> None:
        assert mv[:len(MAGIC_BYTES)] == MAGIC_BYTES
        self._mv = mv[len(MAGIC_BYTES):].toreadonly()
        self._root_node = self._read_node(
            OFFSET_STRUCT.unpack_from(self._mv, offset=0)[0]
        )
        # print('root =', self._root_node)

    def _read_key(self, offset: int) -> memoryview:
        size, = KEY_SIZE_STRUCT.unpack_from(self._mv, offset=offset)
        offset += KEY_SIZE_STRUCT.size
        return self._mv[offset:offset + size]

    def _read_node(self, offset: int) -> _Node | None:
        # print(f'read {offset:+#011x}: ', end='')
        if offset == NULL:
            # print('null')
            return None  # "null" offset (no node)
        elif offset > 0:
            # "branch" node
            # print(f'branch')
            value, left_offset, right_offset = (
                BRANCH_NODE_HEADER_STRUCT.unpack_from(self._mv, offset=offset)
            )
            key_mv = self._read_key(
                offset=offset + BRANCH_NODE_HEADER_STRUCT.size
            )
            return _Node(
                key_mv=key_mv,
                value=value,
                left_offset=left_offset,
                right_offset=right_offset
            )
        else:
            # "leaf" node
            # print(f'leaf')
            offset = -offset  # reset "leaf node" flag in offset
            value, = (
                LEAF_NODE_HEADER_STRUCT.unpack_from(self._mv, offset=offset)
            )
            key_mv = self._read_key(offset + LEAF_NODE_HEADER_STRUCT.size)
            return _Node(key_mv=key_mv, value=value)

    def find_exact(self, key: Buffer) -> int | None:
        with memoryview(key.__buffer__(inspect.BufferFlags.FULL_RO)) as key_mv:
            node = self._root_node
            while node is not None:
                match memcmp(key_mv, node.key_mv):
                    case MemCmpResult.LESS:
                        node = self._read_node(node.left_offset)
                    case MemCmpResult.GREATER:
                        node = self._read_node(node.right_offset)
                    case MemCmpResult.EQUAL:
                        return node.value
        return None


def main() -> None:
    with Path(sys.argv[1]).open('rb') as f:
        f.seek(0, io.SEEK_END)
        file_size = f.tell()

        with (
            mmap.mmap(
                f.fileno(), file_size,
                prot=mmap.PROT_READ,
                flags=mmap.MAP_SHARED
            ) as mmaped,
            memoryview(mmaped) as mv
        ):
            reader = KeyKaReader(mv)
            for i in range(48):
                key = f'key{i:03d}_a'.encode('utf-8')
                print(key, reader.find_exact(key))
            code.interact(local={**locals(), **globals()})


if __name__ == '__main__':
    main()


__all__ = (
    'KeyKaReader',
)
