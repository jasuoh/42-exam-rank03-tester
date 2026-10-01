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

def _ref_string_compression(chars):
    if not chars:
        return ""
    res, prev, count = "", chars[0], 0
    for ch in chars:
        if ch == prev:
            count += 1
        else:
            res += prev + (str(count) if count > 1 else "")
            prev, count = ch, 1
    res += prev + (str(count) if count > 1 else "")
    return res

def _ref_longest_common_subsequence(s1, s2):
    n, m = len(s1), len(s2)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
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

def _fuzz_string_compression(rng):
    n = rng.randint(0, 14)
    return [list(rng.choice("aabbccdd") for _ in range(n))]

def _fuzz_longest_common_subsequence(rng):
    return [_rand_word(rng, 0, 9, "abc"), _rand_word(rng, 0, 9, "abc")]


# ══════════════════════════════════════════════════════════════
#  TRAINING BANK
# ══════════════════════════════════════════════════════════════
TRAINING_EXERCISES = {
    # ── EASY ───────────────────────────────────────────────────
    "py_fizzbuzz_list": {
        "difficulty": "easy", "function": "fizzbuzz_list",
        "oracle": _ref_fizzbuzz_list, "fuzz": _fuzz_fizzbuzz_list,
        "hint": ("Check the multiple-of-15 case (both 3 and 5) before "
                "checking 3 or 5 alone — if your 'multiple of 3' branch "
                "fires first, 15 will print 'Fizz' and never reach "
                "'FizzBuzz'."),
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
        "hint": ("Count how many times each character appears first (one "
                "pass), then scan the string again looking for the first "
                "one whose count is 1 — checking uniqueness by rescanning "
                "the rest of the string for every character works but is "
                "needlessly O(n^2) and easy to get the index wrong on."),
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
        "hint": ("The list has n elements but the values range over "
                "0..n (n+1 possible values) — the expected sum is "
                "n*(n+1)//2, not (n-1)*n//2, so double check which n "
                "you're using before subtracting the actual sum."),
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
        "hint": ("Comparing every pair of elements works but is O(n^2) "
                "and can time out on larger fuzz inputs — putting the "
                "elements in a set and comparing its size to the "
                "original list's length answers the question in one "
                "pass."),
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
        "hint": ("XOR every element together: a value XORed with itself "
                "is 0, so every paired-up number cancels out and only "
                "the lone one survives — no counting dict needed, and it "
                "works even with negative numbers."),
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
        "hint": ("This is just Fibonacci: ways(n) = ways(n-1) + ways(n-2), "
                "because your last move was either a 1-step or a 2-step. "
                "Both n=0 and n=1 have exactly one way, so seed your two "
                "base cases to 1, not 0 and 1."),
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
        "hint": ("Two words are anagrams exactly when their sorted "
                "letters are identical, so use that sorted string as a "
                "dict key to bucket words together — but the OUTPUT group "
                "order must follow each key's first appearance in the "
                "input, not dict insertion order from a different pass "
                "or a sorted-keys order."),
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
        "hint": ("Division-based solutions (multiply everything, divide "
                "by lst[i]) break the moment there's a 0 in the list, and "
                "division is against the rules here anyway. Instead do "
                "two passes: a running prefix product left-to-right, then "
                "a running suffix product right-to-left, multiplying them "
                "into the result."),
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
        "hint": ("k=1 means the largest, not the smallest, and k counts "
                "each duplicate value separately rather than treating "
                "equal values as one rank — sorting descending and "
                "indexing at k-1 handles both of those automatically."),
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
        "hint": ("Sort first, then fix one number and two-pointer the "
                "rest of the list from both ends toward the middle "
                "(move the low pointer up when the sum's too small, the "
                "high pointer down when it's too big). After sorting, "
                "skip over a fixed value (or a pointer value) that's "
                "equal to the one you just used, or you'll emit the same "
                "triplet more than once."),
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
        "hint": ("Peel the matrix like an onion: take the whole top row, "
                "then the last element of every remaining row, then the "
                "bottom row reversed, then the first element of every "
                "remaining row (top to bottom), and repeat on what's "
                "left. Re-check that inner loop's guards after each peel "
                "— a matrix with only one row or one column left is where "
                "this usually double-counts or crashes."),
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
        "hint": ("Checking every pair of lines is O(n^2) and will time "
                "out on longer inputs. Use two pointers starting at the "
                "opposite ends: at each step the shorter of the two lines "
                "is the bottleneck, so move that pointer inward (moving "
                "the taller one can only ever shrink the width without "
                "raising the height)."),
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
    "py_string_compression": {
        "difficulty": "medium", "function": "string_compression",
        "oracle": _ref_string_compression, "fuzz": _fuzz_string_compression,
        "hint": ("Walk the list tracking the current run's character and "
                "count; when the character changes, flush the previous "
                "run to the result — but only append the count when it's "
                "greater than 1, a run of length 1 gets just the bare "
                "character. Don't forget to flush the last run after the "
                "loop ends, it never triggers a character-change."),
        "subject": _sub("py_string_compression", """
        Write a function that compresses a list of single characters:
        each maximal run of the same character becomes that character
        followed by the run's length, but ONLY when the run is longer
        than 1 (a run of length 1 is written as just the character, no
        digit). Return the result as one string, not a list. An empty
        list returns "".

            def string_compression(chars: list[str]) -> str:

        Examples:
            string_compression(["a","a","b","b","b"]) -> "a2b3"
            string_compression(["a","b","c"])          -> "abc"
            string_compression([])                      -> ""
        """),
        "cases": [
            [[]], [["a"]], [["a", "a"]], [["a", "b", "c"]],
            [["a", "a", "b", "b", "b"]],
            [["a"] + ["b"] * 12], [list("aabbccdd")], [list("aaaa")],
            [["x", "x", "x", "y"]],
        ],
    },

    # ── HARD ───────────────────────────────────────────────────
    "py_merge_intervals": {
        "difficulty": "hard", "function": "merge_intervals",
        "oracle": _ref_merge_intervals, "fuzz": _fuzz_merge_intervals,
        "hint": ("Sort the intervals by start first — unsorted, deciding "
                "whether two intervals overlap means checking every pair. "
                "Sorted, you only need to compare each interval to the "
                "last one you've kept: if it starts at or before that "
                "one's end, extend its end (with max, not just overwrite "
                "it — a contained interval like [2,3] inside [1,10] must "
                "not shrink the merged end)."),
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
        "hint": ("Classic DP: dp[i] = the length of the longest "
                "increasing subsequence ENDING at index i. For each i, "
                "look back at every j < i and, whenever lst[j] < lst[i], "
                "try dp[j] + 1. The answer is the max of the whole dp "
                "array, not dp[-1] — the longest subsequence doesn't have "
                "to end at the last element. Every step is strictly "
                "increasing, so equal values never extend a run."),
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
        "hint": ("The water trapped above any single bar is bounded by "
                "the taller of its two neighbouring walls, not just its "
                "immediate neighbour: water[i] = min(tallest bar to the "
                "left of i, tallest bar to the right of i) - heights[i] "
                "(never negative). Precompute the running max-so-far from "
                "the left and from the right, then combine them per "
                "index."),
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
        "hint": ("A greedy 'always take the biggest coin that fits' "
                "strategy fails on some denominations (e.g. coins "
                "[1,3,4] for amount 6: greedy picks 4+1+1=3 coins, but "
                "3+3=2 is better) — build a DP table instead, where "
                "dp[a] is the fewest coins to make amount a, trying every "
                "coin against every smaller amount. Initialize "
                "unreachable amounts to infinity (not 0), and remember "
                "dp[0] = 0."),
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
        "hint": ("Build a 2D DP table where dp[i][j] is the edit distance "
                "between s1's first i characters and s2's first j: when "
                "the current characters match, dp[i][j] = dp[i-1][j-1] "
                "(no edit needed); otherwise it's 1 + the best of the "
                "three neighbours (delete, insert, substitute). Row 0 and "
                "column 0 aren't zero everywhere — they're 0,1,2,3...  "
                "since turning \"\" into a j-length string always costs "
                "j insertions."),
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
        "hint": ("Trying every pair of bars as the rectangle's edges is "
                "O(n^2) and will time out. Use a monotonic stack of "
                "INDICES (not heights) kept increasing by height: when "
                "the next bar is shorter than the bar on top of the "
                "stack, that top bar can't extend any further right, so "
                "pop it and compute its area using the current index and "
                "whatever index is now exposed below it on the stack as "
                "its left/right boundaries. Append a sentinel 0-height bar "
                "at the end so every remaining bar on the stack gets "
                "popped and considered."),
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
    "py_longest_common_subsequence": {
        "difficulty": "hard", "function": "longest_common_subsequence",
        "oracle": _ref_longest_common_subsequence,
        "fuzz": _fuzz_longest_common_subsequence,
        "hint": ("A 2D DP table again: dp[i][j] is the LCS length of "
                "s1's first i chars and s2's first j chars. When "
                "s1[i-1] == s2[j-1], extend the diagonal (dp[i-1][j-1] + "
                "1); otherwise take the better of dropping one character "
                "from either string (max(dp[i-1][j], dp[i][j-1])) — "
                "never both at once, that undercounts. This is not "
                "'longest common SUBSTRING': the matched characters don't "
                "need to be contiguous."),
        "subject": _sub("py_longest_common_subsequence", """
        Write a function that returns the LENGTH of the longest common
        subsequence of two strings: the longest sequence of characters
        that appears, in order but not necessarily contiguously, in both.

            def longest_common_subsequence(s1: str, s2: str) -> int:

        Examples:
            longest_common_subsequence("abcde", "ace") -> 3
            longest_common_subsequence("abc", "def")    -> 0
            longest_common_subsequence("", "abc")       -> 0
        """),
        "cases": [
            ["abcde", "ace"], ["abc", "abc"], ["abc", "def"],
            ["", "abc"], ["abc", ""], ["", ""], ["aaaa", "aa"],
            ["abcba", "abcbcba"], ["bsbininm", "jmjkbkjkv"],
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
