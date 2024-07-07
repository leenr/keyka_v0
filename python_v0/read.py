from __future__ import annotations

import code
import io
import mmap
import sys
from inspect import BufferFlags
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

from .memcmp import MemCmpResult, memcmp
from .structs import (
    BRANCH_NODE_HEADER_STRUCT, KEY_LENGTH_STRUCT, LEAF_NODE_HEADER_STRUCT,
    MAGIC_BYTES, OFFSET_STRUCT
)

if TYPE_CHECKING:
    from collections.abc import Buffer, Generator


NULL: Final = 0


class _Node(NamedTuple):
    offset: int
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
        length, = KEY_LENGTH_STRUCT.unpack_from(self._mv, offset=offset)
        offset += KEY_LENGTH_STRUCT.size
        return self._mv[offset:offset + length]

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
                offset=offset,
                key_mv=key_mv,
                value=value,
                left_offset=left_offset,
                right_offset=right_offset
            )
        else:
            # "leaf" node
            # print(f'leaf')
            real_offset = -offset  # reset "leaf node" flag in offset
            value, = LEAF_NODE_HEADER_STRUCT.unpack_from(
                self._mv, offset=real_offset
            )
            key_mv = self._read_key(real_offset + LEAF_NODE_HEADER_STRUCT.size)
            return _Node(offset=offset, key_mv=key_mv, value=value)

    def find_exact(self, key: Buffer) -> int | None:
        with key.__buffer__(BufferFlags.FULL_RO) as key_mv:
            node = self._root_node
            while node is not None:
                match memcmp(key_mv, node.key_mv):
                    case MemCmpResult.LESS:
                        node = self._read_node(node.left_offset)
                    case MemCmpResult.GREATER:
                        node = self._read_node(node.right_offset)
                    case MemCmpResult.EQUAL:
                        return node.value
            else:
                return None

    def _get_next_node(self, node: _Node) -> _Node | None:
        if node.offset < 0:  # leaf -> branch
            next_node_offset = (
                -node.offset
                + LEAF_NODE_HEADER_STRUCT.size
                + KEY_LENGTH_STRUCT.size
                + len(node.key_mv)
            )
            if next_node_offset >= len(self._mv):
                return None
        else:  # branch -> leaf
            # next node's offset is
            next_node_offset = (
                -node.offset
                - len(node.key_mv)
                - KEY_LENGTH_STRUCT.size
                - BRANCH_NODE_HEADER_STRUCT.size
            )
            if -next_node_offset >= len(self._mv):
                return None
        return self._read_node(next_node_offset)

    def _find_matching_node(
            self,
            key_mv: memoryview, *,
            allow_strict_equality: bool
    ) -> _Node | None:

        node = self._root_node
        last_left_node = node
        while node is not None:
            match memcmp(key_mv, node.key_mv):
                case MemCmpResult.LESS:
                    # go left
                    if deeper_node := self._read_node(node.left_offset):
                        last_left_node = node
                        node = deeper_node
                    else:
                        return node
                case MemCmpResult.GREATER:
                    # go right
                    if deeper_node := self._read_node(node.right_offset):
                        node = deeper_node
                    else:
                        return last_left_node
                case MemCmpResult.EQUAL:
                    if not allow_strict_equality:
                        node = self._get_next_node(node)
                    return node

    def find_range(
            self,
            key1: Buffer,
            key2: Buffer | None = None,
            key1_allow_strict_equality: bool = True,
            key2_allow_strict_equality: bool = False
    ) -> Generator[tuple[bytes, int], None, None]:

        with key1.__buffer__(BufferFlags.FULL_RO) as key1_mv:
            node = self._find_matching_node(
                key1_mv,
                allow_strict_equality=key1_allow_strict_equality
            )

        if key2 is not None:
            with key2.__buffer__(BufferFlags.FULL_RO) as key2_mv:
                while node is not None:
                    match memcmp(node.key_mv, key2_mv):
                        case MemCmpResult.LESS:
                            yield node.key_mv.tobytes(), node.value
                        case MemCmpResult.EQUAL if key2_allow_strict_equality:
                            yield node.key_mv.tobytes(), node.value
                        case _:
                            break
                    node = self._get_next_node(node)
        elif node is not None:
            yield node.key_mv.tobytes(), node.value
            while (node := self._get_next_node(node)) is not None:
                yield node.key_mv.tobytes(), node.value


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
                key = f'key{i:08d}_a'.encode('utf-8')
                print(key, reader.find_exact(key))
            print(*reader.find_range(b'', b'key0000010_a'))
            print(*reader.find_range(b'key16775200_a'))
            print(*reader.find_range(b'key00000001_a', b'key00000100_a'))
            code.interact(local={**locals(), **globals()})


if __name__ == '__main__':
    main()


__all__ = (
    'KeyKaReader',
)
