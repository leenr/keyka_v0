import math
import os
from typing import BinaryIO, Collection, Iterable

from .structs import (
    BRANCH_NODE_HEADER_STRUCT, KEY_SIZE_STRUCT, LEAF_NODE_HEADER_STRUCT,
    MAGIC_BYTES, OFFSET_STRUCT
)


def pwrite(b: BinaryIO, offset: int, data: bytes) -> None:
    if fileno := b.fileno():
        os.pwrite(fileno, data, offset)
    else:
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


def pack_tree(key_values: Iterable[tuple[bytes, int]], *, f: BinaryIO) -> None:
    node_offsets = list[int]()

    tree_base_offset = f.tell()

    # write NULL as "root" node offset
    # (will be filled later with the root node offset if tree is not empty)
    f.write(OFFSET_STRUCT.pack(0))

    idx = None
    prev_key = None
    for idx, (key, value) in enumerate(key_values):
        # check that input is sorted by key
        if prev_key is not None:
            assert key > prev_key, f'Unsorted input: {key} !> {prev_key}'
        prev_key = key

        # 0 - leaf, 1+ - branches
        level = get_btree_level(idx)

        # we may need to save a reference to that node later,
        # so save the offset from the start of the tree
        node_offset = f.tell() - tree_base_offset
        if level == 0:
            # "leaf" nodes should have negative offset:
            # in this case we would not need to pointlessly store
            # left and right offsets as zero values
            node_offset = -node_offset

        # this is a place for RAM optimizations if necessary:
        # `node_offsets` should be the only thing that grow in size.
        # **it is possible** to significantly optimize the usage,
        # but the code will be significantly more complex
        node_offsets.append(node_offset)

        print(
            f'#{idx}(level={level}) {node_offset:+#011x}: {key!r} = {value!r}: ',
            end=''
        )

        if level >= 1:  # "branch"
            # the "delta" is a number of indexes to skip (both forward and backwards)
            # to access the lower-level node
            delta = 2 ** (level - 1)

            # write header
            left_node_offset = node_offsets[idx - delta]
            right_node_offset = 0  # will be filled later by lower-level node (we don't know it yet)
            f.write(BRANCH_NODE_HEADER_STRUCT.pack(value, left_node_offset, right_node_offset))
            print(f'branch ±{delta} (left_offset={left_node_offset:+#011x})', end='')

            # compute higher-level node index to write our offset to it
            higher_node_idx = idx - delta * 2  # use the delta from higher level
        else:  # "leaf"
            # write header
            f.write(LEAF_NODE_HEADER_STRUCT.pack(value))
            print('leaf', end='')

            # compute higher-level node index to write our offset to it
            higher_node_idx = idx - 1  # higher-level node is always the previous one for leaf nodes

        # write key
        f.write(KEY_SIZE_STRUCT.pack(len(key)) + key)

        # write our offset to the higher-lever node "right offset" field
        # `if` is there to not do it for the first node
        if higher_node_idx >= 0:
            higher_node_offset = node_offsets[higher_node_idx]
            print(f' higher_node=#{higher_node_idx} {higher_node_offset:+#011x}', end='')
            # higher-level can't be a leaf b/c of its nature
            assert higher_node_offset > 0
            pwrite(
                f,
                offset=(
                    tree_base_offset
                    + higher_node_offset
                    + BRANCH_NODE_HEADER_STRUCT.size
                    - OFFSET_STRUCT.size  # "right offset" field
                ),
                data=OFFSET_STRUCT.pack(node_offset)
            )

        print()

    # write the root if tree is not empty
    if idx is not None:
        # the "root" is the topmost level node (it can access any other node)
        root_node_idx = 2 ** math.floor(math.log(idx + 1, 2)) - 1
        root_node_offset = node_offsets[root_node_idx]
        print(f'root = #{root_node_idx} {root_node_offset:+#011x}')
        pwrite(f, tree_base_offset, OFFSET_STRUCT.pack(root_node_offset))
    else:
        # empty tree, do nothing since root offset is already set to 0
        pass


def pack_into_file(filename: str, key_n_values: Collection[tuple[bytes, int]]):
    # disable buffering for `pwrite` to actually work
    with open(filename, 'wb', buffering=False) as f:
        f.write(MAGIC_BYTES)
        # write the tree
        pack_tree(key_n_values, f=f)


if __name__ == '__main__':
    pack_into_file(
        'test_pack.keyka',
        ((f'key{i:08d}_a'.encode('utf-8'), i) for i in range(2 ** 24))
    )

