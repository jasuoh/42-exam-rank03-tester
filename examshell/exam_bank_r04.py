#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam_bank_r04.py  ·  42 Common Core  ·  Exam Rank 04 (Python)

Exercise bank for the ExamShell tester, same shape as exam_bank.py (Rank
03) — see that module's docstring for what each key means.

Two things differ from the Rank 03 bank, both because the published Rank
04 pool is what it is rather than by choice:

  · 4 levels, not 6.
  · 7 exercises, every one of them a documented subject, so all 7 are
    "standard" and there is no Extra pool. Level 2 and level 4 have a
    single exercise each — `new` during an exam therefore re-draws the
    same one there, which is honest: the real pool is that small.

Subjects, signatures, examples and the forbidden-call notes were taken
from the published Rank 04 Python pool (rank04.42exam.net) and the
behaviour re-derived from the worked examples given there.

  ⚠  This file contains the reference solutions (answer key). Do not peek
     if you actually want to practice!
"""

import string

from .bank_common import sub as _sub
from .bank_common import signature_of as _signature_of

N_LEVELS = 4

# ══════════════════════════════════════════════════════════════
#  ORACLE  ·  verified reference implementations
#
#  Every oracle must be self-contained: no module-level helper, no
#  import, nothing but builtins and its own locals. grader.selftest()
#  lifts each one into a standalone file and grades it like a submission,
#  which only works if it carries no free globals (see
#  grader.oracle_free_globals).
# ══════════════════════════════════════════════════════════════
def _ref_array_rotation_detector(arr1, arr2):
    if len(arr1) != len(arr2):
        return False
    n = len(arr1)
    if n == 0:
        return True
    for shift in range(n):
        if all(arr2[i] == arr1[(i + shift) % n] for i in range(n)):
            return True
    return False


def _ref_constellation_mapper(stars, dim):
    if dim <= 0:
        return []
    grid = [["." for _ in range(dim)] for _ in range(dim)]
    for row, col in stars:
        if 0 <= row < dim and 0 <= col < dim:
            grid[row][col] = "*"
    return ["".join(cells) for cells in grid]


def _ref_list_intersection_finder(lists):
    if not lists:
        return []
    common = set(lists[0])
    for other in lists[1:]:
        common &= set(other)
    return sorted(common)


def _ref_merge_sorted_lists(lists):
    # A k-way merge by hand: repeatedly take the smallest head. Deliberately
    # not sorted(l1 + l2) — that is exactly what the subject forbids.
    heads = [0] * len(lists)
    remaining = sum(len(lst) for lst in lists)
    merged = []
    for _ in range(remaining):
        best = -1
        for i, lst in enumerate(lists):
            if heads[i] >= len(lst):
                continue
            if best < 0 or lst[heads[i]] < lists[best][heads[best]]:
                best = i
        merged.append(lists[best][heads[best]])
        heads[best] += 1
    return merged


def _ref_palindrome_partitioner(text):
    n = len(text)
    if n == 0:
        return 0
    pal = [[False] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        for j in range(i, n):
            if text[i] == text[j] and (j - i < 2 or pal[i + 1][j - 1]):
                pal[i][j] = True
    cuts = [0] * n
    for j in range(n):
        if pal[0][j]:
            cuts[j] = 0
            continue
        best = j
        for i in range(1, j + 1):
            if pal[i][j] and cuts[i - 1] + 1 < best:
                best = cuts[i - 1] + 1
        cuts[j] = best
    return cuts[n - 1]


def _ref_package_dependency_resolver(packages):
    # Kahn's algorithm, one whole ready-layer at a time with each layer
    # sorted — that (not a global min-heap) is what reproduces the order
    # the published examples show, e.g. web/api/frontend/backend ->
    # ["api", "web", "backend", "frontend"].
    deps = {}
    for name in packages:
        wanted = []
        for dep in packages[name]:
            if dep in packages and dep not in wanted:
                wanted.append(dep)
        deps[name] = wanted
    dependents = {name: [] for name in packages}
    indegree = {name: len(deps[name]) for name in packages}
    for name in packages:
        for dep in deps[name]:
            dependents[dep].append(name)
    order = []
    ready = sorted(name for name in packages if indegree[name] == 0)
    while ready:
        order.extend(ready)
        following = []
        for name in ready:
            for user in dependents[name]:
                indegree[user] -= 1
                if indegree[user] == 0:
                    following.append(user)
        ready = sorted(following)
    if len(order) != len(packages):
        return []
    return order


def _ref_sliding_window_maximum(nums, k):
    if k <= 0 or not nums or k > len(nums):
        return []
    maxima = []
    for start in range(len(nums) - k + 1):
        best = nums[start]
        for i in range(start + 1, start + k):
            if nums[i] > best:
                best = nums[i]
        maxima.append(best)
    return maxima


# ══════════════════════════════════════════════════════════════
#  FUZZERS  ·  callable(rng) -> args
# ══════════════════════════════════════════════════════════════
def _fuzz_array_rotation_detector(rng):
    n = rng.randint(0, 7)
    arr = [rng.randint(-5, 5) for _ in range(n)]
    kind = rng.random()
    if kind < 0.45 and n:                      # a genuine rotation
        shift = rng.randrange(n)
        return [arr, arr[shift:] + arr[:shift]]
    if kind < 0.7:                             # a length mismatch
        return [arr, arr + [rng.randint(-5, 5)]]
    return [arr, [rng.randint(-5, 5) for _ in range(n)]]


def _fuzz_constellation_mapper(rng):
    dim = rng.randint(0, 6)
    stars = [(rng.randint(-2, 7), rng.randint(-2, 7))
             for _ in range(rng.randint(0, 8))]
    return [stars, dim]


def _fuzz_list_intersection_finder(rng):
    count = rng.randint(0, 4)
    lists = [[rng.randint(0, 9) for _ in range(rng.randint(0, 6))]
             for _ in range(count)]
    return [lists]


def _fuzz_merge_sorted_lists(rng):
    lists = [sorted(rng.randint(-20, 20) for _ in range(rng.randint(0, 6)))
             for _ in range(rng.randint(1, 4))]
    return [lists]


def _fuzz_palindrome_partitioner(rng):
    alphabet = "aab"                            # a tiny alphabet makes
    n = rng.randint(0, 12)                      # real palindromes likely
    return ["".join(rng.choice(alphabet) for _ in range(n))]


def _fuzz_package_dependency_resolver(rng):
    names = list(string.ascii_lowercase[:rng.randint(0, 6)])
    packages = {}
    for i, name in enumerate(names):
        if rng.random() < 0.15:
            # point somewhere later on purpose: sometimes a cycle, and
            # sometimes a name that isn't a package at all
            packages[name] = [rng.choice(names + ["ghost"])]
            continue
        earlier = names[:i]
        picks = rng.sample(earlier, rng.randint(0, len(earlier))) if earlier else []
        packages[name] = picks
    return [packages]


def _fuzz_sliding_window_maximum(rng):
    nums = [rng.randint(-15, 15) for _ in range(rng.randint(0, 10))]
    return [nums, rng.randint(-1, 6)]


# ══════════════════════════════════════════════════════════════
#  EXERCISES
# ══════════════════════════════════════════════════════════════
EXERCISES = {

    # ── LEVEL 1 ────────────────────────────────────────────────
    "py_array_rotation_detector": {
        "level": 1, "function": "array_rotation_detector", "standard": True,
        "oracle": _ref_array_rotation_detector,
        "fuzz": _fuzz_array_rotation_detector,
        # The published subject forbids collections.deque.rotate(); the
        # header already bans every import, and this catches a `.rotate()`
        # call reached any other way.
        "forbidden": ("rotate",),
        "hint": ("Two arrays of different lengths can never be rotations "
                "of each other — check that first, before anything else, "
                "or an index will run off the end. Then note that a "
                "rotation is cyclic: element i of arr2 must equal element "
                "(i + shift) % len(arr1) of arr1 for ONE single shift "
                "that works for every i at once — finding a shift that "
                "matches only the first element is not enough "
                "([1,2,3] vs [3,2,1] fails on the second element)."),
        "subject": _sub("py_array_rotation_detector", """
        Write a function that decides whether arr2 is a rotation of arr1.
        A rotation shifts every element cyclically while keeping their
        relative order — [4,5,1,2,3] is a rotation of [1,2,3,4,5], but
        [3,2,1] is not a rotation of [1,2,3].

            def array_rotation_detector(arr1: list, arr2: list) -> bool:

        Return True when arr2 is a valid rotation of arr1, False otherwise
        (including when the two lengths differ). Two empty lists count as
        a valid rotation.

        Examples:
            array_rotation_detector([1,2,3,4,5], [4,5,1,2,3]) -> True
            array_rotation_detector([1,2,3,4,5], [5,1,2,3,4]) -> True
            array_rotation_detector([1,2,3], [3,2,1])         -> False
            array_rotation_detector([1,2], [1,2,3])           -> False
            array_rotation_detector([], [])                   -> True
        """),
        "cases": [
            [[1, 2, 3, 4, 5], [4, 5, 1, 2, 3]],
            [[1, 2, 3, 4, 5], [5, 1, 2, 3, 4]],
            [[1, 2, 3], [3, 2, 1]],
            [[1, 2], [1, 2, 3]],
            [[], []],
            [[1], [1]],
            [[1], [2]],
            [[1, 2, 3], [1, 2, 3]],
            [[1, 1, 2], [1, 2, 1]],
            [[1, 2, 1, 2], [2, 1, 2, 1]],
            [[1, 2, 3], []],
            [[0, 0, 0], [0, 0, 0]],
            [[1, 2, 3, 4], [3, 4, 1, 2]],
            [[1, 2, 3, 4], [4, 3, 2, 1]],
        ],
    },

    "py_constellation_mapper": {
        "level": 1, "function": "constellation_mapper", "standard": True,
        "oracle": _ref_constellation_mapper,
        "fuzz": _fuzz_constellation_mapper,
        "hint": ("Build the grid as a list of LISTS of single characters "
                "and join each row into a string only at the very end — "
                "strings are immutable, so grid[row][col] = '*' cannot "
                "work on a list of strings. Watch the row/column order "
                "too: a star is given as (row, col), so it goes at "
                "grid[row][col], not grid[col][row] — a mix-up is "
                "invisible on a symmetric example like the diagonal one "
                "and obvious on any other."),
        "subject": _sub("py_constellation_mapper", """
        Write a function that maps a constellation of stars onto a square
        grid and returns it as a list of strings, one per row.

            def constellation_mapper(stars: list[tuple[int, int]], dim: int) -> list[str]:

        · stars is a list of (row, col) tuples; dim is the grid's size.
        · A star is '*', empty space is '.'.
        · (0, 0) is the top-left cell.
        · Coordinates outside the grid (negative ones included) are ignored.
        · The same coordinate listed twice is still one star.
        · A dim of 0 or less yields an empty list.

        Examples:
            constellation_mapper([(0,0), (1,1), (2,2)], 3) -> ['*..', '.*.', '..*']
            constellation_mapper([(1,1), (0,1), (2,1), (1,0), (1,2)], 3)
                                                           -> ['.*.', '***', '.*.']
            constellation_mapper([], 2)                    -> ['..', '..']
            constellation_mapper([(0,0), (5,5)], 3)        -> ['*..', '...', '...']
        """),
        "cases": [
            [[(0, 0), (1, 1), (2, 2)], 3],
            [[(1, 1), (0, 1), (2, 1), (1, 0), (1, 2)], 3],
            [[], 2],
            [[(0, 0), (0, 0), (1, 1)], 2],
            [[(0, 0), (5, 5)], 3],
            [[(1, 0), (1, 1), (1, 2)], 3],
            [[], 0],
            [[(0, 0)], 1],
            [[(-1, 0), (0, -1)], 2],
            [[(2, 0), (0, 2)], 3],
            [[(0, 1), (1, 0)], 2],
            [[(3, 3)], 3],
        ],
    },

    "py_list_intersection_finder": {
        "level": 1, "function": "list_intersection_finder", "standard": True,
        "oracle": _ref_list_intersection_finder,
        "fuzz": _fuzz_list_intersection_finder,
        "hint": ("Two edge cases sink most attempts here. An EMPTY outer "
                "list ([]) has no first list to start intersecting from — "
                "handle it before you touch lists[0]. And any inner list "
                "being empty makes the whole intersection empty, which "
                "falls out for free if you keep intersecting instead of "
                "skipping empties. Sets give you uniqueness; sorted() at "
                "the end gives you the required ascending order."),
        "subject": _sub("py_list_intersection_finder", """
        Write a function that finds the elements present in EVERY one of
        the given integer lists, returned unique and sorted ascending.

            def list_intersection_finder(lists: list[list[int]]) -> list[int]:

        Return an empty list when the outer list is empty, when any inner
        list is empty, or when there is no common element at all.

        Examples:
            list_intersection_finder([[1,2,3], [2,3,4], [2,3,5]]) -> [2, 3]
            list_intersection_finder([[1,2,3,4], [2,4,6,8], [4,8,12]]) -> [4]
            list_intersection_finder([[1,1,2,3], [1,2,2,3], [1,2,3,3]]) -> [1, 2, 3]
            list_intersection_finder([[1,2,3], [4,5,6]])          -> []
            list_intersection_finder([])                          -> []
            list_intersection_finder([[1,2,3], []])               -> []
            list_intersection_finder([[5]])                       -> [5]
        """),
        "cases": [
            [[[1, 2, 3], [2, 3, 4], [2, 3, 5]]],
            [[[1, 2, 3, 4], [2, 4, 6, 8], [4, 8, 12]]],
            [[[1, 1, 2, 3], [1, 2, 2, 3], [1, 2, 3, 3]]],
            [[[1, 2, 3], [4, 5, 6]]],
            [[]],
            [[[1, 2, 3], []]],
            [[[5]]],
            [[[]]],
            [[[3, 1, 2], [2, 1, 3]]],
            [[[-1, 0, 1], [0, 1, 2], [1, 2, 3]]],
            [[[7, 7, 7], [7]]],
            [[[1], [2], [3]]],
        ],
    },

    # ── LEVEL 2 ────────────────────────────────────────────────
    "py_merge_sorted_lists": {
        "level": 2, "function": "merge_sorted_lists", "standard": True,
        "oracle": _ref_merge_sorted_lists, "fuzz": _fuzz_merge_sorted_lists,
        # heapq.merge() is banned too (see the subject) but is not listed
        # here on purpose: this check matches on the bare call name, and
        # `merge` is far too plausible a name for a student's OWN helper
        # to reject outright. The import ban already covers heapq.
        "forbidden": ("sorted", "sort"),
        "hint": ("You are not allowed to concatenate and sort — the point "
                "is to exploit the fact that every input list is ALREADY "
                "sorted. Keep one read position per list, repeatedly pick "
                "the list whose current head is smallest, and advance only "
                "that one. Duplicates are kept, so never skip an equal "
                "value; and a list that has been fully consumed must stop "
                "being considered, or its index will run off the end."),
        "subject": _sub("py_merge_sorted_lists", """
        Write a function that merges several already-sorted integer lists
        into one sorted list.

            def merge_sorted_lists(lists: list[list[int]]) -> list[int]:

        · The result is in ascending order.
        · Every duplicate is kept.
        · Empty inner lists (and an empty outer list) are handled gracefully.
        · Do NOT concatenate and re-sort: sorted(), .sort() and heapq.merge()
          are all forbidden. Merge the lists by walking them in parallel.

        Examples:
            merge_sorted_lists([[1,3,5], [2,4,6]])       -> [1,2,3,4,5,6]
            merge_sorted_lists([[1,5,9], [2,3,8], [4,6,7]]) -> [1,2,3,4,5,6,7,8,9]
            merge_sorted_lists([[1,1,2], [2,3,3]])       -> [1,1,2,2,3,3]
            merge_sorted_lists([[], [1,2,3]])            -> [1,2,3]
            merge_sorted_lists([[]])                     -> []
        """),
        "cases": [
            [[[1, 3, 5], [2, 4, 6]]],
            [[[1, 5, 9], [2, 3, 8], [4, 6, 7]]],
            [[[5], [1, 3], [2, 4]]],
            [[[1, 1, 2], [2, 3, 3]]],
            [[[], [1, 2, 3]]],
            [[[]]],
            [[[-5, -1, 0], [-3, 2, 4]]],
            [[[10], [10], [10]]],
            [[]],
            [[[1, 2, 3]]],
            [[[], []]],
            [[[0, 0, 0], [0, 0]]],
            [[[1, 4], [2, 5], [3, 6], [0, 7]]],
        ],
    },

    # ── LEVEL 3 ────────────────────────────────────────────────
    "py_palindrome_partitioner": {
        "level": 3, "function": "palindrome_partitioner", "standard": True,
        "oracle": _ref_palindrome_partitioner,
        "fuzz": _fuzz_palindrome_partitioner,
        "hint": ("Count CUTS, not pieces: 'aab' splits into 'aa' and 'b', "
                "which is 2 pieces but 1 cut, and a string that is already "
                "a palindrome needs 0. Trying every split point recursively "
                "is exponential and will time out on longer inputs — build "
                "it up instead: first work out, for every pair (i, j), "
                "whether text[i:j+1] is a palindrome (a table you can fill "
                "from the inside out), then sweep left to right computing "
                "the cheapest way to end a palindrome at each position."),
        "subject": _sub("py_palindrome_partitioner", """
        Given a string, find the MINIMUM number of cuts needed to split it
        so that every resulting piece is a palindrome.

            def palindrome_partitioner(s: str) -> int:

        · Return the number of cuts, as an integer.
        · A string that is already a palindrome needs 0 cuts.
        · A one-character string needs 0 cuts, and so does an empty one.

        Examples:
            palindrome_partitioner("aab") -> 1     # "aa" | "b"
            palindrome_partitioner("aba") -> 0     # already a palindrome
            palindrome_partitioner("abc") -> 2     # "a" | "b" | "c"
        """),
        "cases": [
            ["aab"], ["aba"], ["abc"], [""], ["a"], ["aa"], ["ab"],
            ["racecar"], ["aabaa"], ["abbab"], ["noonabbad"],
            ["banana"], ["aaaaaa"], ["abcdefg"], ["ababbbabbababa"],
        ],
    },

    "py_package_dependency_resolver": {
        "level": 3, "function": "package_dependency_resolver", "standard": True,
        "oracle": _ref_package_dependency_resolver,
        "fuzz": _fuzz_package_dependency_resolver,
        "forbidden": ("TopologicalSorter",),
        "hint": ("This is a topological sort. Count, for each package, how "
                "many of its dependencies are actually in the dictionary "
                "(references to unknown packages are ignored, so they must "
                "not be counted); install everything whose count is 0, "
                "decrement the counts of whatever depended on those, and "
                "repeat. Two details decide whether you match the expected "
                "output exactly: a cycle is detected by finishing with "
                "FEWER packages installed than you were given (return [] "
                "then, not a partial order), and each batch of "
                "simultaneously-installable packages goes out in "
                "alphabetical order."),
        "subject": _sub("py_package_dependency_resolver", """
        Write a function that returns a valid package installation order:
        every package comes after all of the dependencies it needs.

            def package_dependency_resolver(packages: dict[str, list[str]]) -> list[str]:

        · packages maps a package name to the list of names it depends on.
        · Dependencies are installed before whatever requires them.
        · A reference to a package that is not a key of the dictionary is
          ignored — it is not something you can install.
        · Return [] when no valid order exists (a circular dependency), and
          [] for an empty input.
        · When several packages could be installed at the same moment,
          install them in alphabetical order.

        Examples:
            package_dependency_resolver({"app": ["database"],
                                         "database": ["driver"],
                                         "driver": []})
                -> ["driver", "database", "app"]
            package_dependency_resolver({"A": [], "B": ["A"], "C": ["A","B"]})
                -> ["A", "B", "C"]
            package_dependency_resolver({"X": ["Y"], "Y": ["X"]})  -> []
            package_dependency_resolver({})                        -> []
            package_dependency_resolver({"web": [], "api": [],
                                         "frontend": ["web"],
                                         "backend": ["api"]})
                -> ["api", "web", "backend", "frontend"]
        """),
        "cases": [
            [{"app": ["database"], "database": ["driver"], "driver": []}],
            [{"A": [], "B": ["A"], "C": ["A", "B"]}],
            [{}],
            [{"X": ["Y"], "Y": ["X"]}],
            [{"web": [], "api": [], "frontend": ["web"], "backend": ["api"]}],
            [{"solo": []}],
            [{"self": ["self"]}],
            [{"a": ["ghost"]}],
            [{"a": ["b", "b"], "b": []}],
            [{"a": ["b"], "b": ["c"], "c": ["a"]}],
            [{"z": [], "y": [], "x": []}],
            [{"a": [], "b": ["a"], "c": ["b"], "d": ["a", "c"]}],
        ],
    },

    # ── LEVEL 4 ────────────────────────────────────────────────
    "py_sliding_window_maximum": {
        "level": 4, "function": "sliding_window_maximum", "standard": True,
        "oracle": _ref_sliding_window_maximum,
        "fuzz": _fuzz_sliding_window_maximum,
        "hint": ("Count the windows before you write the loop: a list of n "
                "elements has exactly n - k + 1 windows of size k, so your "
                "range stops at len(nums) - k + 1, not at len(nums). All "
                "three invalid cases return [] rather than raising or "
                "guessing — an empty list, a k of 0 or less, and a k larger "
                "than the list — and it is worth checking them up front, "
                "since len(nums) - k + 1 quietly goes negative for the "
                "last one and an empty loop would return [] for the wrong "
                "reason."),
        "subject": _sub("py_sliding_window_maximum", """
        Write a function that returns the maximum of every window of size k
        as that window slides across the list, one position at a time.

            def sliding_window_maximum(nums: list[int], k: int) -> list[int]:

        Return [] for invalid input: an empty list, a k of 0 or less, or a
        k larger than the list itself.

        Examples:
            sliding_window_maximum([1,3,-1,-3,5,3,6,7], 3) -> [3,3,5,5,6,7]
            sliding_window_maximum([1,2,3,4,5], 2)         -> [2,3,4,5]
            sliding_window_maximum([5,4,3,2,1], 1)         -> [5,4,3,2,1]
            sliding_window_maximum([1,2,3], 3)             -> [3]
            sliding_window_maximum([1,2,3], 4)             -> []
            sliding_window_maximum([], 2)                  -> []
            sliding_window_maximum([1,2,3], 0)             -> []
        """),
        "cases": [
            [[1, 3, -1, -3, 5, 3, 6, 7], 3],
            [[1, 2, 3, 4, 5], 2],
            [[5, 4, 3, 2, 1], 1],
            [[1, 2, 3], 3],
            [[1, 2, 3], 4],
            [[], 2],
            [[1, 2, 3], 0],
            [[1, 2, 3], -1],
            [[], 0],
            [[7], 1],
            [[-5, -2, -9], 2],
            [[4, 4, 4, 4], 2],
            [[1, -1, 1, -1, 1], 3],
        ],
    },
}

# ══════════════════════════════════════════════════════════════
#  INDEXES  ·  built from EXERCISES, validated at import time
# ══════════════════════════════════════════════════════════════
LEVELS = {lvl: [] for lvl in range(1, N_LEVELS + 1)}
for _name, _ex in EXERCISES.items():
    _lvl = _ex["level"]
    if _lvl not in LEVELS:
        raise ValueError("exam_bank_r04: %s has level %r, expected 1..%d"
                         % (_name, _lvl, N_LEVELS))
    LEVELS[_lvl].append(_name)
    _ex.setdefault("standard", False)

for _lvl, _pool in LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank_r04: level %d has no exercise" % _lvl)

# Every exercise here is a documented Rank 04 subject, so the Standard pool
# (what `make exam` draws from) is the whole bank — unlike the Rank 03 bank,
# which also carries an Extra pool for practice only. The split is kept so
# both banks answer the same questions the same way.
STANDARD_LEVELS = {lvl: [name for name in pool if EXERCISES[name]["standard"]]
                   for lvl, pool in LEVELS.items()}

for _lvl, _pool in STANDARD_LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank_r04: level %d has no standard exercise" % _lvl)


def signature_of(name):
    """The `def …:` line of an exercise, as shown in its subject."""
    return _signature_of(EXERCISES[name]["subject"])
