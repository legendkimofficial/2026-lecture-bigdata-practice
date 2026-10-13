#!/usr/bin/env python3
"""Week 4 · Task 3 — Same memory, fewer mistakes.

Textbook §4.4 (Bloom filters), §4.5 (counting distinct).

`NaiveFilter` is a membership filter in a fixed number of bits. It works. It
also makes far more mistakes than it has to with the memory it was given, and
it does so for a reason you can find by reading §4.4.2 and doing one derivative.

You get **exactly the same number of bits**. Make fewer mistakes.

    python3 bench.py
    python3 bench.py --yours
The rule that makes this interesting: a false negative is not allowed. Ever.
The whole point of this structure is that "no" means no. A filter that gets a
better score by occasionally forgetting something it was given has not improved
anything, it has broken the contract.
"""
import hashlib
import sys


class NaiveFilter:
    """One hash function, and the bits it was given."""

    def __init__(self, n_bits, seed=246):
        self.n_bits = n_bits
        self.seed = seed
        self.bits = bytearray(n_bits)
    def _index(self, item):
        d = hashlib.blake2b(str(item).encode(), digest_size=8,
                            key=str(self.seed).encode()).digest()
        return int.from_bytes(d, "big") % self.n_bits

    def add(self, item):
        self.bits[self._index(item)] = 1

    def __contains__(self, item):
        return bool(self.bits[self._index(item)])

    def memory_bits(self):
        return self.n_bits


class YourFilter:
    """Your filter.
        __init__(n_bits, seed=246)
        add(item)
        item in filter  ->  bool
        memory_bits()   ->  how many bits you are using

    `memory_bits()` must not exceed the `n_bits` you were given. The harness
    checks. Counting only some of your memory is not an optimisation.
    §4.4.2 gives the false-positive rate of a filter with m bits, k hashes and
    n items inserted. There is a k that minimises it, and it depends on m/n.
    The harness tells you n before you start, so you have no excuse for guessing.

    Then there is a second question, which is worth more: the harness inserts
    a **known** number of items, but a real stream does not tell you n in
    advance. What would you do then? You do not have to implement it - but
    observation.md asks.
    """
    # At 10 bits per item, k* = (m/n) ln(2) = 6.93, so use seven hashes.
    # Slots avoid an instance dictionary. One bytearray holds both the seed
    # metadata and the bit vector, avoiding a separate Python bytes object.
    __slots__ = ("_state",)

    def __init__(self, n_bits, seed=246):
        if not isinstance(n_bits, int) or n_bits <= 0:
            raise ValueError("n_bits must be a positive integer")
        seed_key = str(seed).encode()
        if len(seed_key) > 64:
            seed_key = hashlib.blake2b(seed_key, digest_size=16).digest()

        # Charge the object/slot and bytearray header (including its terminating
        # byte), not only its logical bit payload. The array itself also stores
        # one byte for seed length and the seed bytes. Immutable
        # class/module code and temporary hash buffers are shared/computation,
        # not retained filter state. A nonempty bytearray has one extra byte.
        headers = sys.getsizeof(self) + sys.getsizeof(bytearray(1)) - 1
        payload_bytes = n_bits // 8 - headers
        if payload_bytes <= 1 + len(seed_key):
            raise ValueError("budget is too small for the filter metadata")
        self._state = bytearray(payload_bytes)
        self._state[0] = len(seed_key)
        self._state[1:1 + len(seed_key)] = seed_key
        if self.memory_bits() > n_bits:
            raise ValueError("runtime object overhead exceeds the bit budget")

    def _indices(self, item):
        # Seven separate 64-bit blocks of a cryptographic digest act as seven
        # uniform hash values. This avoids correlations from a short repeated
        # arithmetic progression. Insertion and lookup use the same positions,
        # so no inserted item can become a false negative.
        bit_offset = 1 + self._state[0]
        digest = hashlib.blake2b(str(item).encode(), digest_size=56,
                                 key=self._state[1:bit_offset]).digest()
        m = 8 * (len(self._state) - bit_offset)
        for start in range(0, 56, 8):
            yield 8 * bit_offset + int.from_bytes(digest[start:start + 8], "big") % m

    def add(self, item):
        for index in self._indices(item):
            self._state[index >> 3] |= 1 << (index & 7)

    def __contains__(self, item):
        return all(self._state[index >> 3] & (1 << (index & 7))
                   for index in self._indices(item))

    def memory_bits(self):
        """Allocated bytes of all retained, instance-owned state, in bits."""
        return 8 * (sys.getsizeof(self) + sys.getsizeof(self._state))
