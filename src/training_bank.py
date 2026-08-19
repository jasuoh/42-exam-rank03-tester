#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
training_bank.py  ·  ExamShell  ·  LeetCode-style training pool

A second, independent exercise bank for open-ended practice. Exercises here
are grouped by DIFFICULTY (easy / medium / hard) instead of exam level, and
are never drawn into the 6-level exam — `examshell.py` keeps this pool's
index (TRAINING_BY_DIFFICULTY) completely separate from exam_bank's LEVELS.

Same shape as exam_bank.py otherwise: each exercise has a self-contained
`oracle` (the answer key, used only to compute expected outputs), curated
edge-case `cases`, and a `fuzz(rng)` generator for extra randomised inputs.
Graded through the exact same sandbox as the exam pool.

  ⚠  This file contains the reference solutions. Don't peek if you want to
     practice for real!
"""

import string

from .bank_common import sub as _sub

DIFFICULTIES = ["easy", "medium", "hard"]


# ══════════════════════════════════════════════════════════════
#  ORACLE  ·  verified reference implementations
# ══════════════════════════════════════════════════════════════
def _ref_fizzbuzz_list(n):
    res = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            res.append("FizzBuzz")
        elif i % 3 == 0:
            res.append("Fizz")
        elif i % 5 == 0:
            res.append("Buzz")
        else:
            res.append(str(i))
    return res

def _ref_first_unique_char(text):
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    for i, ch in enumerate(text):
        if counts[ch] == 1:
            return i
    return -1

def _ref_missing_number(lst):
    n = len(lst)
    return n * (n + 1) // 2 - sum(lst)

def _ref_group_anagrams(words):
    groups, order = {}, []
    for w in words:
        key = "".join(sorted(w))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(w)
    return [groups[k] for k in order]

def _ref_product_except_self(lst):
    n = len(lst)
    res = [1] * n
    prefix = 1
    for i in range(n):
        res[i] = prefix
        prefix *= lst[i]
    suffix = 1
    for i in range(n - 1, -1, -1):
        res[i] *= suffix
        suffix *= lst[i]
    return res

def _ref_kth_largest(lst, k):
    return sorted(lst, reverse=True)[k - 1]

def _ref_merge_intervals(intervals):
    if not intervals:
        return []
    ivs = sorted([list(iv) for iv in intervals], key=lambda x: x[0])
    merged = [ivs[0]]
    for start, end in ivs[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged

def _ref_longest_increasing_subsequence(lst):
    n = len(lst)
    if n == 0:
        return 0
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if lst[j] < lst[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)

def _ref_trapping_rain_water(heights):
    n = len(heights)
    if n == 0:
        return 0
    left_max = [0] * n
    right_max = [0] * n
    left_max[0] = heights[0]
    for i in range(1, n):
        left_max[i] = max(left_max[i - 1], heights[i])
    right_max[n - 1] = heights[n - 1]
    for i in range(n - 2, -1, -1):
        right_max[i] = max(right_max[i + 1], heights[i])
    return sum(min(left_max[i], right_max[i]) - heights[i] for i in range(n))

def _ref_contains_duplicate(lst):
    return len(set(lst)) != len(lst)

def _ref_single_number(lst):
    result = 0
    for x in lst:
        result ^= x
    return result

def _ref_climbing_stairs(n):
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def _ref_three_sum(lst):
    nums = sorted(lst)
    n = len(nums)
    res = []
    for i in range(n - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            total = nums[i] + nums[lo] + nums[hi]
            if total < 0:
                lo += 1
            elif total > 0:
                hi -= 1
            else:
                res.append([nums[i], nums[lo], nums[hi]])
                lo += 1
                hi -= 1
                while lo < hi and nums[lo] == nums[lo - 1]:
                    lo += 1
                while lo < hi and nums[hi] == nums[hi + 1]:
                    hi -= 1
    return res

def _ref_spiral_matrix(matrix):
    if not matrix or not matrix[0]:
        return []
    m = [row[:] for row in matrix]
    res = []
    while m:
        res += m.pop(0)
        if m and m[0]:
            for row in m:
                res.append(row.pop())
        if m:
            res += m.pop()[::-1]
        if m and m[0]:
            for row in m[::-1]:
                res.append(row.pop(0))
    return res

def _ref_container_with_most_water(heights):
    lo, hi = 0, len(heights) - 1
    best = 0
    while lo < hi:
        best = max(best, min(heights[lo], heights[hi]) * (hi - lo))
        if heights[lo] < heights[hi]:
            lo += 1
        else:
            hi -= 1
    return best

def _ref_coin_change(coins, amount):
    inf = float("inf")
    dp = [0] + [inf] * amount
    for a in range(1, amount + 1):
        for coin in coins:
            if coin <= a and dp[a - coin] + 1 < dp[a]:
                dp[a] = dp[a - coin] + 1
    return dp[amount] if dp[amount] != inf else -1

def _ref_edit_distance(s1, s2):
    n, m = len(s1), len(s2)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[n][m]

def _ref_largest_rectangle_histogram(heights):
    stack = []
    best = 0
    n = len(heights)
    for i in range(n + 1):
        h = heights[i] if i < n else 0
        while stack and heights[stack[-1]] >= h:
            top = stack.pop()
            w = i if not stack else i - stack[-1] - 1
            best = max(best, heights[top] * w)
        stack.append(i)
    return best


# ══════════════════════════════════════════════════════════════
#  FUZZERS  ·  generate random valid inputs per exercise
# ══════════════════════════════════════════════════════════════
def _rand_word(rng, lo=0, hi=8, alphabet=None):
    alphabet = alphabet or string.ascii_letters
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi)))

def _rand_intlist(rng, lo=0, hi=8, vmin=-10, vmax=10):
    return [rng.randint(vmin, vmax) for _ in range(rng.randint(lo, hi))]

def _fuzz_fizzbuzz_list(rng):
    return [rng.randint(0, 60)]

def _fuzz_first_unique_char(rng):
    return [_rand_word(rng, 0, 14, "aabbccdd")]

def _fuzz_missing_number(rng):
    n = rng.randint(0, 15)
    full = list(range(n + 1))
    del full[rng.randrange(len(full))]
    rng.shuffle(full)
    return [full]

def _fuzz_group_anagrams(rng):
    n = rng.randint(0, 8)
    return [[_rand_word(rng, 0, 4, "abc") for _ in range(n)]]

def _fuzz_product_except_self(rng):
    n = rng.randint(0, 8)
    return [[rng.randint(-6, 6) for _ in range(n)]]

def _fuzz_kth_largest(rng):
    n = rng.randint(1, 10)
    lst = [rng.randint(-20, 20) for _ in range(n)]
    return [lst, rng.randint(1, n)]

def _fuzz_merge_intervals(rng):
    n = rng.randint(0, 6)
    intervals = []
    for _ in range(n):
        start = rng.randint(0, 20)
        intervals.append([start, start + rng.randint(0, 5)])
    return [intervals]

def _fuzz_longest_increasing_subsequence(rng):
    n = rng.randint(0, 12)
    return [[rng.randint(-10, 10) for _ in range(n)]]

def _fuzz_trapping_rain_water(rng):
    n = rng.randint(0, 15)
    return [[rng.randint(0, 8) for _ in range(n)]]

def _fuzz_contains_duplicate(rng):
    return [_rand_intlist(rng, 0, 10, vmin=-5, vmax=5)]

def _fuzz_single_number(rng):
    n = rng.randint(1, 6)
    used = set()
    vals = []
    while len(used) < n:
        v = rng.randint(-15, 15)
        if v in used:
            continue
        used.add(v)
        vals += [v, v]
    singleton = rng.randint(-15, 15)
    while singleton in used:
        singleton = rng.randint(-15, 15)
    vals.append(singleton)
    rng.shuffle(vals)
    return [vals]

def _fuzz_climbing_stairs(rng):
    return [rng.randint(0, 30)]

def _fuzz_three_sum(rng):
    return [_rand_intlist(rng, 0, 9, vmin=-8, vmax=8)]

def _fuzz_spiral_matrix(rng):
    rows, cols = rng.randint(0, 5), rng.randint(0, 5)
    if rows == 0 or cols == 0:
        return [[]]
    return [[[rng.randint(-9, 9) for _ in range(cols)] for _ in range(rows)]]

def _fuzz_container_with_most_water(rng):
    return [_rand_intlist(rng, 0, 12, vmin=0, vmax=10)]

def _fuzz_coin_change(rng):
    n_coins = rng.randint(1, 4)
    coins = sorted(set(rng.randint(1, 12) for _ in range(n_coins))) or [1]
    return [coins, rng.randint(0, 40)]

def _fuzz_edit_distance(rng):
    return [_rand_word(rng, 0, 8, "abc"), _rand_word(rng, 0, 8, "abc")]

def _fuzz_largest_rectangle_histogram(rng):
    return [[rng.randint(0, 10) for _ in range(rng.randint(0, 10))]]


# ══════════════════════════════════════════════════════════════
#  TRAINING BANK
# ══════════════════════════════════════════════════════════════
TRAINING_EXERCISES = {
    # ── EASY ───────────────────────────────────────────────────
    "py_fizzbuzz_list": {
        "difficulty": "easy", "function": "fizzbuzz_list",
        "oracle": _ref_fizzbuzz_list, "fuzz": _fuzz_fizzbuzz_list,
        "subject": _sub("py_fizzbuzz_list", """
        Write the classic FizzBuzz. Return a list of strings for every
        number from 1 to n (inclusive): "Fizz" for multiples of 3, "Buzz"
        for multiples of 5, "FizzBuzz" for multiples of both, otherwise the
        number itself as a string. n = 0 returns an empty list.

            def fizzbuzz_list(n: int) -> list[str]:

        Examples:
            fizzbuzz_list(5)  -> ["1", "2", "Fizz", "4", "Buzz"]
            fizzbuzz_list(15)[-1] -> "FizzBuzz"
            fizzbuzz_list(0)  -> []
        """),
        "cases": [
            [0], [1], [2], [3], [4], [5], [15], [16], [20], [30], [45], [50],
        ],
    },
    "py_first_unique_char": {
        "difficulty": "easy", "function": "first_unique_char",
        "oracle": _ref_first_unique_char, "fuzz": _fuzz_first_unique_char,
        "subject": _sub("py_first_unique_char", """
        Write a function that returns the index of the first character in
        a string that does not repeat anywhere else in it. Case-sensitive.
        If every character repeats (or the string is empty), return -1.

            def first_unique_char(text: str) -> int:

        Examples:
            first_unique_char("leetcode")  -> 0
            first_unique_char("aabb")      -> -1
            first_unique_char("")          -> -1
        """),
        "cases": [
            ["leetcode"], ["aabb"], [""], ["a"], ["aabbc"], ["abcabc"],
            ["stress"], ["aabbccz"], ["z"], ["abab c"], ["  a "],
        ],
    },
    "py_missing_number": {
        "difficulty": "easy", "function": "missing_number",
        "oracle": _ref_missing_number, "fuzz": _fuzz_missing_number,
        "subject": _sub("py_missing_number", """
        You are given a list of n distinct integers taken from the range
        0..n (inclusive) with exactly one of them missing, in any order.
        Return the missing number.

            def missing_number(lst: list[int]) -> int:

        Examples:
            missing_number([3, 0, 1])                 -> 2
            missing_number([9,6,4,2,3,5,7,0,1])        -> 8
            missing_number([0])                        -> 1
            missing_number([1])                         -> 0
        """),
        "cases": [
            [[3, 0, 1]], [[0, 1]], [[1, 0]], [[9, 6, 4, 2, 3, 5, 7, 0, 1]],
            [[0]], [[1]], [[2, 0]], [[0, 2]], [[1, 2]], [[4, 3, 1, 0]],
        ],
    },
    "py_contains_duplicate": {
        "difficulty": "easy", "function": "contains_duplicate",
        "oracle": _ref_contains_duplicate, "fuzz": _fuzz_contains_duplicate,
        "subject": _sub("py_contains_duplicate", """
        Write a function that returns True if any value appears at least
        twice in the list, False if every value is distinct.

            def contains_duplicate(lst: list[int]) -> bool:

        Examples:
            contains_duplicate([1,2,3,1]) -> True
            contains_duplicate([1,2,3,4]) -> False
            contains_duplicate([])        -> False
        """),
        "cases": [
            [[1, 2, 3, 1]], [[1, 2, 3, 4]], [[]], [[1]], [[1, 1, 1, 1]],
            [[1, 2, 2, 3, 3]], [[0, -1, 1]], [[5, 5]],
        ],
    },
    "py_single_number": {
        "difficulty": "easy", "function": "single_number",
        "oracle": _ref_single_number, "fuzz": _fuzz_single_number,
        "subject": _sub("py_single_number", """
        Every element in the list appears exactly twice, except one which
        appears exactly once. Find and return that one element.

            def single_number(lst: list[int]) -> int:

        Examples:
            single_number([2,2,1])       -> 1
            single_number([4,1,2,1,2])   -> 4
            single_number([1])           -> 1
        """),
        "cases": [
            [[2, 2, 1]], [[4, 1, 2, 1, 2]], [[1]], [[-1, -1, 5]],
            [[0, 0, 7]], [[3, 5, 3]], [[9, 1, 9, 2, 1]],
        ],
    },
    "py_climbing_stairs": {
        "difficulty": "easy", "function": "climbing_stairs",
        "oracle": _ref_climbing_stairs, "fuzz": _fuzz_climbing_stairs,
        "subject": _sub("py_climbing_stairs", """
        You are climbing a staircase of n steps. Each move you can climb
        either 1 or 2 steps. Return the number of distinct ways to reach
        the top. n = 0 has exactly one way (do nothing).

            def climbing_stairs(n: int) -> int:

        Examples:
            climbing_stairs(2) -> 2   # 1+1, 2
            climbing_stairs(3) -> 3   # 1+1+1, 1+2, 2+1
            climbing_stairs(0) -> 1
        """),
        "cases": [
            [0], [1], [2], [3], [4], [5], [10], [20], [30],
        ],
    },

    # ── MEDIUM ─────────────────────────────────────────────────
    "py_group_anagrams": {
        "difficulty": "medium", "function": "group_anagrams",
        "oracle": _ref_group_anagrams, "fuzz": _fuzz_group_anagrams,
        "subject": _sub("py_group_anagrams", """
        Write a function that groups words that are anagrams of each
        other. Two words are anagrams if they contain exactly the same
        letters, case-sensitively. Groups appear in the order their first
        word first appeared in the input; within a group, keep the words
        in their original relative order.

            def group_anagrams(words: list[str]) -> list[list[str]]:

        Examples:
            group_anagrams(["eat","tea","tan","ate","nat","bat"])
                -> [["eat","tea","ate"], ["tan","nat"], ["bat"]]
            group_anagrams([""])   -> [[""]]
            group_anagrams([])     -> []
        """),
        "cases": [
            [["eat", "tea", "tan", "ate", "nat", "bat"]], [[""]], [[]],
            [["a"]], [["ab", "ba", "abc"]], [["aa", "aa"]],
            [["x", "y", "z"]], [["abc", "bca", "cab", "xyz"]],
            [["listen", "silent", "hello"]],
        ],
    },
    "py_product_except_self": {
        "difficulty": "medium", "function": "product_except_self",
        "oracle": _ref_product_except_self, "fuzz": _fuzz_product_except_self,
        "subject": _sub("py_product_except_self", """
        Write a function that returns a new list where each element is the
        product of every OTHER element in the input list. Do not use
        division. An empty list returns an empty list.

            def product_except_self(lst: list[int]) -> list[int]:

        Examples:
            product_except_self([1,2,3,4])     -> [24,12,8,6]
            product_except_self([-1,1,0,-3,3]) -> [0,0,9,0,0]
            product_except_self([5])           -> [1]
        """),
        "cases": [
            [[1, 2, 3, 4]], [[-1, 1, 0, -3, 3]], [[]], [[5]], [[2, 3]],
            [[0, 0]], [[1, 1, 1, 1]], [[-5]], [[2, 2, 2]], [[0, 1, 2]],
        ],
    },
    "py_kth_largest": {
        "difficulty": "medium", "function": "kth_largest",
        "oracle": _ref_kth_largest, "fuzz": _fuzz_kth_largest,
        "subject": _sub("py_kth_largest", """
        Write a function that returns the k-th largest element in a list
        of integers (k = 1 means the single largest). Duplicate values
        count individually. k is always valid: 1 <= k <= len(lst).

            def kth_largest(lst: list[int], k: int) -> int:

        Examples:
            kth_largest([3,2,1,5,6,4], 2)             -> 5
            kth_largest([3,2,3,1,2,4,5,5,6], 4)       -> 4
            kth_largest([7,7,7], 2)                    -> 7
        """),
        "cases": [
            [[3, 2, 1, 5, 6, 4], 2], [[3, 2, 3, 1, 2, 4, 5, 5, 6], 4],
            [[1], 1], [[7, 7, 7], 2], [[-1, -2, -3], 1], [[5, 4], 1],
            [[5, 4], 2], [[10, 9, 8, 7], 4], [[1, 2], 2],
        ],
    },
    "py_three_sum": {
        "difficulty": "medium", "function": "three_sum",
        "oracle": _ref_three_sum, "fuzz": _fuzz_three_sum,
        "subject": _sub("py_three_sum", """
        Write a function that finds every unique triplet of elements in a
        list that adds up to zero. Sort each triplet's own three values
        ascending, and sort the outer list of triplets ascending too (this
        is what the standard sort-and-two-pointer approach naturally
        produces — match that order exactly).

            def three_sum(lst: list[int]) -> list[list[int]]:

        Examples:
            three_sum([-1,0,1,2,-1,-4]) -> [[-1,-1,2], [-1,0,1]]
            three_sum([0,0,0])          -> [[0,0,0]]
            three_sum([1,2,-2,-1])      -> []
        """),
        "cases": [
            [[-1, 0, 1, 2, -1, -4]], [[0, 0, 0]], [[0, 0, 0, 0]], [[]],
            [[1, 2, -2, -1]], [[3, -2, 1, 0]], [[-2, 0, 1, 1, 2]],
            [[1, -1, -1, 0]],
        ],
    },
    "py_spiral_matrix": {
        "difficulty": "medium", "function": "spiral_matrix",
        "oracle": _ref_spiral_matrix, "fuzz": _fuzz_spiral_matrix,
        "subject": _sub("py_spiral_matrix", """
        Write a function that returns every element of a matrix in
        clockwise spiral order, starting from the top-left corner, as a
        flat list. The matrix is rectangular but need not be square.

            def spiral_matrix(matrix: list[list[int]]) -> list[int]:

        Examples:
            spiral_matrix([[1,2,3],[4,5,6],[7,8,9]]) -> [1,2,3,6,9,8,7,4,5]
            spiral_matrix([[1,2],[3,4]])              -> [1,2,4,3]
            spiral_matrix([])                          -> []
        """),
        "cases": [
            [[[1, 2, 3], [4, 5, 6], [7, 8, 9]]],
            [[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]],
            [[[1]]], [[[1, 2], [3, 4]]], [[]], [[[1, 2, 3]]],
            [[[1], [2], [3]]],
        ],
    },
    "py_container_with_most_water": {
        "difficulty": "medium", "function": "container_with_most_water",
        "oracle": _ref_container_with_most_water,
        "fuzz": _fuzz_container_with_most_water,
        "subject": _sub("py_container_with_most_water", """
        Each value in the list is the height of a vertical line at that
        index. Together with the x-axis, any two lines form a container.
        Return the maximum amount of water such a container can hold
        (width = distance between the two lines, height = the shorter of
        the two).

            def container_with_most_water(heights: list[int]) -> int:

        Examples:
            container_with_most_water([1,8,6,2,5,4,8,3,7]) -> 49
            container_with_most_water([1,1])                -> 1
            container_with_most_water([4,3,2,1,4])           -> 16
        """),
        "cases": [
            [[1, 8, 6, 2, 5, 4, 8, 3, 7]], [[1, 1]], [[4, 3, 2, 1, 4]],
            [[1, 2, 1]], [[]], [[5]], [[0, 2]], [[2, 0]],
        ],
    },

    # ── HARD ───────────────────────────────────────────────────
    "py_merge_intervals": {
        "difficulty": "hard", "function": "merge_intervals",
        "oracle": _ref_merge_intervals, "fuzz": _fuzz_merge_intervals,
        "subject": _sub("py_merge_intervals", """
        Write a function that merges every pair of overlapping intervals.
        Each interval is [start, end] with start <= end. Two intervals
        overlap when one starts at or before the other one ends. Return
        the merged intervals sorted by start.

            def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:

        Examples:
            merge_intervals([[1,3],[2,6],[8,10],[15,18]])
                -> [[1,6],[8,10],[15,18]]
            merge_intervals([[1,4],[4,5]]) -> [[1,5]]
            merge_intervals([])            -> []
        """),
        "cases": [
            [[[1, 3], [2, 6], [8, 10], [15, 18]]], [[[1, 4], [4, 5]]],
            [[]], [[[1, 4]]], [[[1, 4], [2, 3]]], [[[1, 4], [0, 4]]],
            [[[1, 2], [3, 4]]], [[[1, 10], [2, 3], [4, 5], [6, 7]]],
            [[[5, 6], [1, 2], [3, 4]]],
        ],
    },
    "py_longest_increasing_subsequence": {
        "difficulty": "hard", "function": "longest_increasing_subsequence",
        "oracle": _ref_longest_increasing_subsequence,
        "fuzz": _fuzz_longest_increasing_subsequence,
        "subject": _sub("py_longest_increasing_subsequence", """
        Write a function that returns the LENGTH of the longest strictly
        increasing subsequence of a list of integers. The subsequence does
        not need to be contiguous, but must keep the original order.

            def longest_increasing_subsequence(lst: list[int]) -> int:

        Examples:
            longest_increasing_subsequence([10,9,2,5,3,7,101,18]) -> 4
            longest_increasing_subsequence([7,7,7,7])              -> 1
            longest_increasing_subsequence([])                     -> 0
        """),
        "cases": [
            [[10, 9, 2, 5, 3, 7, 101, 18]], [[0, 1, 0, 3, 2, 3]],
            [[7, 7, 7, 7]], [[]], [[1]], [[5, 4, 3, 2, 1]],
            [[1, 2, 3, 4, 5]], [[3, 1, 4, 1, 5, 9, 2, 6]],
        ],
    },
    "py_trapping_rain_water": {
        "difficulty": "hard", "function": "trapping_rain_water",
        "oracle": _ref_trapping_rain_water, "fuzz": _fuzz_trapping_rain_water,
        "subject": _sub("py_trapping_rain_water", """
        Given a list of non-negative bar heights (width 1 each), compute
        how many units of water are trapped between the bars after rain.

            def trapping_rain_water(heights: list[int]) -> int:

        Examples:
            trapping_rain_water([0,1,0,2,1,0,1,3,2,1,2,1]) -> 6
            trapping_rain_water([4,2,0,3,2,5])              -> 9
            trapping_rain_water([])                          -> 0
        """),
        "cases": [
            [[0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]], [[4, 2, 0, 3, 2, 5]],
            [[]], [[1]], [[1, 1, 1]], [[5, 4, 1, 2]], [[0, 0, 0]],
            [[3, 0, 3]], [[2, 0, 2, 0, 2]],
        ],
    },
    "py_coin_change": {
        "difficulty": "hard", "function": "coin_change",
        "oracle": _ref_coin_change, "fuzz": _fuzz_coin_change,
        "subject": _sub("py_coin_change", """
        You have an unlimited supply of each coin denomination in `coins`.
        Return the minimum number of coins needed to make exactly
        `amount`, or -1 if it can't be made. amount = 0 needs 0 coins.

            def coin_change(coins: list[int], amount: int) -> int:

        Examples:
            coin_change([1,2,5], 11) -> 3   # 5+5+1
            coin_change([2], 3)       -> -1
            coin_change([1], 0)       -> 0
        """),
        "cases": [
            [[1, 2, 5], 11], [[2], 3], [[1], 0], [[1, 3, 4], 6],
            [[2, 5, 10], 27], [[1], 1], [[5], 3], [[1, 2, 5], 0],
        ],
    },
    "py_edit_distance": {
        "difficulty": "hard", "function": "edit_distance",
        "oracle": _ref_edit_distance, "fuzz": _fuzz_edit_distance,
        "subject": _sub("py_edit_distance", """
        Write a function that returns the minimum number of single-
        character insertions, deletions or substitutions needed to turn
        s1 into s2 (the classic Levenshtein distance).

            def edit_distance(s1: str, s2: str) -> int:

        Examples:
            edit_distance("horse", "ros")            -> 3
            edit_distance("intention", "execution")  -> 5
            edit_distance("", "abc")                  -> 3
        """),
        "cases": [
            ["horse", "ros"], ["intention", "execution"], ["", "abc"],
            ["abc", ""], ["", ""], ["abc", "abc"], ["a", "b"],
            ["kitten", "sitting"],
        ],
    },
    "py_largest_rectangle_histogram": {
        "difficulty": "hard", "function": "largest_rectangle_histogram",
        "oracle": _ref_largest_rectangle_histogram,
        "fuzz": _fuzz_largest_rectangle_histogram,
        "subject": _sub("py_largest_rectangle_histogram", """
        Each value in the list is the height of a histogram bar of width
        1, all standing side by side. Return the area of the largest
        rectangle that fits entirely within the histogram's outline.

            def largest_rectangle_histogram(heights: list[int]) -> int:

        Examples:
            largest_rectangle_histogram([2,1,5,6,2,3]) -> 10
            largest_rectangle_histogram([2,4])           -> 4
            largest_rectangle_histogram([])               -> 0
        """),
        "cases": [
            [[2, 1, 5, 6, 2, 3]], [[2, 4]], [[1]], [[]], [[0, 0, 0]],
            [[5, 4, 1, 2]], [[6, 2, 5, 4, 5, 1, 6]], [[1, 1, 1, 1]],
        ],
    },
}

# ══════════════════════════════════════════════════════════════
#  INDEXES  ·  built from TRAINING_EXERCISES, validated at import time
# ══════════════════════════════════════════════════════════════
TRAINING_BY_DIFFICULTY = {d: [] for d in DIFFICULTIES}
for _name, _ex in TRAINING_EXERCISES.items():
    _d = _ex["difficulty"]
    if _d not in TRAINING_BY_DIFFICULTY:
        raise ValueError("training_bank: %s has difficulty %r, expected one of %s"
                         % (_name, _d, DIFFICULTIES))
    TRAINING_BY_DIFFICULTY[_d].append(_name)

for _d, _pool in TRAINING_BY_DIFFICULTY.items():
    if not _pool:
        raise ValueError("training_bank: difficulty %r has no exercise" % _d)
