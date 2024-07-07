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
        # check the magic
        assert mv[:len(MAGIC_BYTES)] == MAGIC_BYTES

        # skip the magic
        self._mv = mv[len(MAGIC_BYTES):].toreadonly()

        # read the root node
        root_node_offset = OFFSET_STRUCT.unpack_from(self._mv, offset=0)[0]
        # it's not strictly necessary to read it a whole,
        # but if not, we still need to store the read offset to it,
        # so why not just read it and store it as parsed node?
        self._root_node = self._read_node(root_node_offset)

    def _read_key(self, offset: int) -> memoryview:
        # key is prefixed with 2 bytes (subject to change) length field
        # (limited to 65_535 bytes max, but not limited in character set)
        length, = KEY_LENGTH_STRUCT.unpack_from(self._mv, offset=offset)
        offset += KEY_LENGTH_STRUCT.size
        return self._mv[offset:offset + length]

    def _read_node(self, offset: int) -> _Node | None:
        # there are two types of nodes:
        #  - half of nodes are "leaf" nodes (referenced by negative offset)
        #  - other half of nodes are "branch" nodes (referenced by positive offset)
        # "leaf" nodes are those that reside on level 0 (lowest), they are slowest to find,
        # but they are very light in wire: there are only key and value, nothing more
        # "branch" nodes contains, besides key and value, two references:
        #  - to the "left" node (which key is **less** than its own)
        #  - to the "right" node (which key is **greater** than its own)
        # there must always be a "left" reference in a "branch" node,
        # but there may not necessarily be a "right" reference (latter is the case
        # for the last node of the tree with an odd number of items).
        # in the case of missing reference, `NULL` offset must be written
        # (`NULL` offset's actual value is `0`)

        # there is no node on `offset == 0` because first 4 bytes of the tree
        # is reserved for the root node's offset:
        # there (on zero offset) is no node to be read, only one offset
        if offset == NULL:
            return None  # "null" offset (no node)
        elif offset > 0:
            # "branch" node structure:
            # (header) uint64 - value
            # (header) int32 - "left" offset
            # (header) int32 - "right" offset
            # (key) uint16 - key length
            # (key) any - key itself
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
            # "leaf" node structure:
            # (header) uint64 - value
            # (key) uint16 - key length
            # (key) any - key itself
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
        # "leaf" and "branch" nodes are actually interleaved on wire
        # that means that we may determine a node type of the next node
        # just by knowing a type of the current node:
        # if current node is a "leaf", next node will be "branch"
        # if current node is a "branch", next node will be "leaf"

        if node.offset < 0:  # leaf -> branch
            next_node_offset = (
                -node.offset
                + LEAF_NODE_HEADER_STRUCT.size  # skip "branch" node header
                + KEY_LENGTH_STRUCT.size  # skip key length field
                + len(node.key_mv)  # skip key itself
            )
            # check that we will not out of bounds
            # (it's possible if we already were at the end)
            if next_node_offset >= len(self._mv):
                return None
        else:  # branch -> leaf
            next_node_offset = (
                -node.offset
                - len(node.key_mv)  # skip key itself
                - KEY_LENGTH_STRUCT.size  # skip key length field
                - BRANCH_NODE_HEADER_STRUCT.size  # skip "branch" node header
            )
            # check that we will not out of bounds
            # (it's possible if we already were at the end)
            if -next_node_offset >= len(self._mv):
                return None

        return self._read_node(next_node_offset)

    def _find_matching_node(
            self,
            key_mv: memoryview, *,
            allow_strict_equality: bool
    ) -> _Node | None:

        node = self._root_node
        last_left_node = None
        while node is not None:
            match memcmp(key_mv, node.key_mv):
                case MemCmpResult.LESS:
                    # searched key is less than the node's, so
                    # go deeper left
                    if deeper_node := self._read_node(node.left_offset):
                        last_left_node = node
                        node = deeper_node
                    else:
                        # there is no deeper node with a _greater_ key,
                        # return the one that greater the most
                        return node
                case MemCmpResult.GREATER:
                    # searched key is greater than the node's, so
                    # go deeper right
                    if deeper_node := self._read_node(node.right_offset):
                        node = deeper_node
                    else:
                        # there is no deeper node with a _lesser_ key,
                        # return the last one that has a _greater_ key
                        # (the one where we last have gone deeper left)
                        # there is one case when there was no such key:
                        # when *all* keys in a tree are less than searched key,
                        # in this case we must return `None`
                        return last_left_node
                case MemCmpResult.EQUAL:
                    if not allow_strict_equality:
                        # we found the node with strictly equal key,
                        # but we've requested to not return such,
                        # so return immediately the next one
                        # (it will be greater, if exists)
                        node = self._get_next_node(node)
                    return node  # hooray :)

    def find_range(
            self,
            key1: Buffer,
            key2: Buffer | None = None,
            key1_allow_strict_equality: bool = True,
            key2_allow_strict_equality: bool = False
    ) -> Generator[tuple[bytes, int], None, None]:

        with key1.__buffer__(BufferFlags.FULL_RO) as key1_mv:
            # find the starting node - the one that matches the `key1`
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
            for i in range(2 ** 16):
                key = f'key{i:08d}_a'.encode('utf-8')
                reader.find_exact(key)
                # print(key, reader.find_exact(key))
            # print(*reader.find_range(b'', b'key0000010_a'))
            # print(*reader.find_range(b'key16775200_a'))
            # print(*reader.find_range(b'key00000001_a', b'key00000100_a'))
            # code.interact(local={**locals(), **globals()})
            # import timeit; print(timeit.timeit(lambda: reader.find_exact(b'key00000004_a'), number=100_000))


if __name__ == '__main__':
    main()


__all__ = (
    'KeyKaReader',
)
