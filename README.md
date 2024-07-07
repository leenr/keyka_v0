## KeyKa v0

KeyKa v0 is an very simple but not versatile, _variable-sized key_ to _**fixed-size value**_ key-value **persistent** storage.
It's based on an idea I had a very long time, implemented initially in a library (un)known as [_ROFL DB_](https://github.com/leenr/rofldb-prototype).

Note "_not versatile_". I made it with one purpose in mind: to be a core component of another **simple but kinda limited in possible uses** _variable-sized key_ to _**variable**-sized value_ key-value persistent storage, which is yet to be implemented.

KeyKa family storages and yet-to-be-implemented aforementioned storage will (quite possible always) share the following properties:
 * _Write-once_[^1] and _read-only_: you can write the file with the _packer_ instance, and send the **completed** file or stream to a separate _reader_ instance or instances, which in turn may read it when necessary.
 * (regarding _reader_ instance) Very light initialization and almost zero memory requirements.
 * _Packer_ instance may be reasonably slow and reasonably heavy for the sake of simplicity and speed and memory usage of _reader_ instance.
 * _Packer_ instance require for an input to be sorted by key.
 * Exactly one value per one key (only KeyKa storage themselves, not necessarily all storages using it).

[^1]: Appending (if input will still be sorted by key) and value replacing **may** be implemented in the future, as it **may** theoretically be possible to do so (even on a live storage!).

KeyKa family storages will have the following _reader_ instance methods:
 * Find a **fixed-size** value (e.g. 64-bit integer) associated with **variable-sized** key (e.g. a string) by exact match by `O(log n)`, where `n` is a number of key-value pairs in storage.
 * (not currently implemented in code, but possible) The same as ^, but using a non-exact match in any direction (same computational complexity).
 * Find all key-value combinations by key's prefix or range by `O(log n)` (for finding starting match) + `O(k)` (for iterating over nodes and for checking an invariant).

### Current state
I believe that all the theory used in this project is sound, and tested enough.

File format of KeyKa v0 is subject to change for the time being. It will most likely be finalized very shortly. I don't have a reason to change it yet, but want to reserve the right to do so. When I finalize the file format, I will document it in this repository.

Implementations is work-in-progress. Things work, but little tested yet.

Currently, I only have pure-Python basic implementation of both _packer_ and _reader_ (see [_python_v0_](./python_v0) directory). In the long run, this implememtaion will probably focus on being the reference implementation, not the speedy one.

I'm also considering writing a Cython and a Rust implementations as a "production-ready" libraries. They will probably live in this monorepository for the time being, but may be decoupled as project matures.

I will also publish benchmarks after I'll make at least one "proper" implementation.

### How it works
KeyKa v0 is essentially just a Binary Search Tree in a file with all nodes laid out in sorted (by key) order to be able to implement range queries at almost no cost at runtime.

**This part of the README is yet to be written.**

### About the feature requests
KeyKa is written to be simple and to be able to support _just_ the use-cases I intend for it to support, nothing much more.

If you want to add something to support yours or somebody else's use case - it may be fine if changes are not complex, but please respect that I may choose **not** to include them in KeyKa project itself. That also means that I may choose to close feature requests without any resolution if they do not fit the original's project ideas.

You are very much **welcome** to fork the project, however. Please, do write me a note if you do so (it's just an ask) - I would like to hear what other things may be implemented on it's base.

Also, for the aforementioned reasons, KeyKa v0 may be declared as **feature complete** after very short time for the sake of not breaking anything.

### Relation to _ROFL DB_
KeyKa v0 is a successor of [_ROFL DB_](https://github.com/leenr/rofldb-prototype). Latter was just a "Proof of Concept", not a finished thing in any way. With the KeyKa, I intend to make it a production-ready thing, this time.

_ROFL DB_ has had almost the same features and properties as listed in this README. The one thing is missing is **variable-sized values**. I decided to implement that separately, for number of reasons - such project is under way.

The file format also differs substantially, although it based on the same basic principles.

### License
The code is licensed under the BSD 3-clause [license](./LICENSE).
