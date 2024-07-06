import math
from operator import itemgetter
from typing import BinaryIO, Collection, Iterable

from .structs import (
    BRANCH_NODE_HEADER_STRUCT, KEY_SIZE_STRUCT, LEAF_NODE_HEADER_STRUCT,
    MAGIC_BYTES, OFFSET_STRUCT
)


def pwrite(b: BinaryIO, offset: int, data: bytes) -> None:
    old_tell = b.tell()
    b.seek(offset)
    b.write(data)
    b.seek(old_tell)


def get_btree_level(idx: int) -> int:
    # I don't have any mathematical proof to that (algorithm was deduced from
    # visual form and some experimentation), but I feel that something about
    # it is correct, and it's working brilliantly.
    # "Level" here is the height from bottom at which the node with that index
    # will reside if there was a binary tree.
    # Basically, it is counting where the first "0" resides in the binary
    # number representation of `idx`.

    level = 0
    while idx % 2 == 1:
        idx >>= 1
        level += 1
    return level


def pack_tree(key_values: Collection[tuple[bytes, int]], *, f: BinaryIO) -> None:
    write_offset_to = dict[int, int]()
    node_offsets = list[int]()

    tree_base = f.tell()

    # write "root" node offset stub (will be filled later if tree is not empty)
    f.write(OFFSET_STRUCT.pack(0))

    idx = None
    prev_key = None
    for idx, (key, value) in enumerate(key_values):
        if prev_key is not None:
            assert key > prev_key, f'Unsorted input: {key} !> {prev_key}'
        prev_key = key

        # 0  - leaf
        # 1+ - branches
        level = get_btree_level(idx)
        is_leaf = level == 0

        # we need to reference that node from the others somehow,
        # so save the offset from the start of the tree
        node_offset = f.tell() - tree_base
        if is_leaf:
            # negative offsets are for "leaf" nodes
            node_offset = -node_offset

        node_offsets.append(node_offset)

        print(
            f'#{idx}(level={level}) {node_offset:+#011x}: {key!r} = {value!r}: ',
            end=''
        )

        if not is_leaf:
            # the "delta" is a number of indexes to skip (both forward and
            # backwards) to access the children on the lower level
            delta = 2 ** (level - 1)

            left_offset = node_offsets[idx - delta]
            right_offset = 0  # will be filled later if needed
            f.write(BRANCH_NODE_HEADER_STRUCT.pack(value, left_offset, right_offset))

            print(f'branch ±{delta} (left_offset={left_offset:+#011x})', end='')

            # if there is no child directly underneath us, descend deeper
            while idx + delta >= len(key_values):
                delta //= 2
            if delta:
                # ask the children to write a reference to themselves
                # here when it will be packed (we can't know their
                # offset beforehand since the key is variable sized)
                assert (idx + delta) not in write_offset_to
                write_offset_to[idx + delta] = f.tell() - OFFSET_STRUCT.size
        else:
            f.write(LEAF_NODE_HEADER_STRUCT.pack(value))
            print('leaf', end='')

        # write key
        f.write(KEY_SIZE_STRUCT.pack(len(key)))
        f.write(key)

        print()

        if (_write_offset_to := write_offset_to.pop(idx, None)) is not None:
            # we're requested to write our offset to some other node
            print(f'+ #{idx} *{_write_offset_to - tree_base:#010x} = {node_offset:+#011x}')
            pwrite(f, _write_offset_to, OFFSET_STRUCT.pack(node_offset))

    # write the root
    if idx is not None:
        # the "root" is the topmost level node (it can access any other node)
        root_idx = 2 ** math.floor(math.log(idx + 1, 2)) - 1
        root_offset = node_offsets[root_idx]
        print(f'root = #{root_idx} {root_offset:+#011x}')
        pwrite(f, tree_base, OFFSET_STRUCT.pack(root_offset))
    else:
        # empty tree, do nothing since root offset is already set to 0
        pass


def pack_into_file(filename: str, key_n_values: Iterable[tuple[bytes, int]]):
    with open(filename, 'wb') as f:
        f.write(MAGIC_BYTES)
        # write the tree
        pack_tree(sorted(key_n_values, key=itemgetter(0)), f=f)


if __name__ == '__main__':
    pack_into_file(
        'test_pack.keyka',
        ((f'key{i:03d}_a'.encode('utf-8'), i) for i in reversed(range(16)))
    )

