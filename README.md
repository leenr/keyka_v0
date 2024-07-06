## KeyKa v0

KeyKa v0 is an experimental, **very simple but not versatile**, _variable-sized key_ to _fixed-size value_ key-value storage / format.
It's based on an idea I had a very long time, implemented initially in a library (un)known as [_ROFL DB_](https://github.com/leenr/rofldb-prototype).

Note "_not versatile_". I made it initially for one purpose only: to be a core component of another **simple but kinda limited in possible uses** _variable-sized key_ to _**variable**-sized value_ key-value storage, which is yet to be named and implemented.

KeyKa family storages and yet-to-be-announced aforementioned storage will (quite possible always) share the following properties:
 * _Write-once_[^1] and _read-only_: you can write the file with _packer_ instance, and send the **completed** file or stream to separate _reader_ instance or instances, which in turn may read it when necessary.
 * (regarding _Reader_ instance) Very light initialization and almost zero memory requirements.
 * _Packer_ instance may be slow and heavy for the sake of simplicity and speed and memory usage of _reader_ instance.
 * (only KeyKa storage themselves, not necessarily all storages using it) **Only one** value for one key.

[^1]: Appending (if input will still be sorted by key) and value replacing **may** be implemented in the future, as it **may** be theoretically be possible to do so (even on a live storage!).

KeyKa family storages will have the following _reader_ instance methods:
 * Find a **fixed-size** value (e.g. 64-bit integer) associated with **variable-sized** key (e.g. a string) by exact match by `O(log n)`, where `n` is a number of key-value pairs in storage.
 * (not yet implemented **in code**, but possible in theory and practice) The same as ^ (with same computational complexity), but using a non-exact match in any direction.
 * (not yet implemented **in code**, but possible in theory and practice) Find all key-value combinations by prefix or range match by `O(log n)` (for finding one match) + `O(k)` (for iterating over nodes and for checking an invariant).

### Current state
I consider all the theory used in this project as sound.

File format of KeyKa v0 is subject to change for the time being. It will most likely be finalized very shortly. I don't have a reason to change it yet, but want to reserve the right to do so. When I finalize the file format, I will document it in this repository.

Implementation is work-in-progress. At least on initial commit, things work, but little tested.

Currently, I only have pure-Python implementation of both _packer_ and, partially, _reader_ (see [_python_v0_](./python_v0) directory). For the first version, I tried to write _reader_ with performance in mind (and at the same time tried to balance it with readability), but in the long run pure-Python will probably not focus on it. Instead, I consider to have it as _reference_ implementation, and may rewrite it in the future to be more readable even if it will be less performant as a result.

I'm also considering writing a Cython and a Rust implementations as a "production-ready" libraries. They will probably live in this monorepository for the time being, but may be decoupled as project matures.

I will also publish benchmarks after I'll make at least one "proper" implementation.

### How it works
KeyKa v0 is essentially just a B-Tree in a file with all nodes laid out in sorted (by key) order to be able to implement range queries at almost no cost at runtime.

**This part of the README is yet to be written.**

_Packer_ instance accepts key-value pairs (it's possible to stream them), checks it's ordering and writes **most** of the data as data comes (except "right" offsets for non-leaf nodes and except one spot for root node offset).

_Reader_ instance reads the nodes starting with  first and follows the "left" or "right" path depending

### About the features
KeyKa is written to be simple and to be able to support just the use-cases **I** intend for it to support, nothing much more.

If you want to add something to support yours or somebody else's use case - it may be fine if changes are not complex, but please respect that I may choose to **not** include any of them in KeyKa project itself. That also means that I may choose to close feature requests without any resolution if they do not fit the original's project ideas.

You are very much **welcome** to fork the project, however, at any time, especially if your changes is substantial. Please, do write me a note if you do so (it's not a requirement, just an ask) - I would like to hear what other things may be implemented on it's base.

Also, for the aforementioned reasons, KeyKa v0 may be declared as **feature complete** after very short time for the sake of not breaking anything.

### Relation to _ROFL DB_
KeyKa v0 is a successor of _ROFL DB_. Latter was just a "Proof of Concept", not a finished thing **in any way**. For the KeyKa, I intend to make it a production-ready thing, this time.

_ROFL DB_ has had almost the same features and properties as listed in this README (if you include ones yet to be implemented in code). The one thing is missing is **variable-sized values**. I decided to implement that separately, for number of reasons - the project is under way.

The file format also differs substantially, although it based on the same basic principles.

### License
The code is licensed under the BSD 3-clause [license](./LICENSE).
