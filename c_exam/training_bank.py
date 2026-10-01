#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
training_bank.py  ·  C Exam Rank 02 tester  ·  LeetCode-style training pool

A second, independent exercise bank for open-ended practice — mirrors
examshell/training_bank.py's role for the Python tester: exercises here are
grouped by DIFFICULTY (easy / medium / hard) instead of exam level, and
`c_exam/examshell.py` keeps this pool's index (TRAINING_BY_DIFFICULTY)
completely separate from bank.py's LEVELS, so it is never drawn into
`make c-exam`.

Every exercise here is deliberately "function"-kind with only int/int_arr
args and an int return — the same "safe to randomise" shape
c_exam/grader.py's --fuzz already knows how to generate values for (see
grader.FUZZABLE_VALUE_KINDS), and with no precondition on how the caller
orders an array (nothing here needs pre-sorted input) so generic fuzzing
never hands the oracle a value it doesn't expect. That's a deliberate
scope choice for a first pool, not a rule for future additions.

  ⚠  This file contains the reference solutions. Don't peek if you want to
     practice for real!
"""

import textwrap

from .bank import _sub_c

DIFFICULTIES = ["easy", "medium", "hard"]


# ══════════════════════════════════════════════════════════════
#  TRAINING BANK
# ══════════════════════════════════════════════════════════════
TRAINING_EXERCISES = {
    # ── EASY ─────────────────────────────────────────────────
    "array_sum": {
        "difficulty": "easy", "function": "array_sum",
        "prototype": "int array_sum(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": ("The accumulator has to start at 0 before the loop runs, "
                "not carry over some other value — and the loop "
                "condition must be i < size, never i <= size, since size "
                "is unsigned and stepping one past it reads outside the "
                "array. Get those two right and the empty-array case "
                "([], 0) falls out on its own."),
        "subject": _sub_c("array_sum", "int array_sum(int *arr, unsigned int size);",
                          "None", """
        Write a function that returns the sum of all `size` elements of
        an int array. An empty array sums to 0.

        Examples:
            array_sum([1,2,3,4,5], 5) -> 15
            array_sum([], 0)          -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int array_sum(int *arr, unsigned int size)
        {
            unsigned int i;
            int sum;

            sum = 0;
            i = 0;
            while (i < size)
            {
                sum += arr[i];
                i++;
            }
            return (sum);
        }
        """),
        "cases": [
            [[]], [[5]], [[1, 2, 3, 4, 5]], [[-1, -2, -3]],
            [[0, 0, 0]], [[100, -100, 50, -50]],
        ],
    },
    "find_max": {
        "difficulty": "easy", "function": "find_max",
        "prototype": "int find_max(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": ("Seeding max at 0 before scanning breaks the moment "
                "every element is negative (e.g. [-5,-1,-10]) — max "
                "should start at arr[0] itself, only after you've "
                "handled size == 0 separately (the one case that returns "
                "0 by spec)."),
        "subject": _sub_c("find_max", "int find_max(int *arr, unsigned int size);",
                          "None", """
        Write a function that returns the largest element of an int
        array. An empty array returns 0.

        Examples:
            find_max([3,1,4,1,5,9,2,6], 8) -> 9
            find_max([], 0)                -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int find_max(int *arr, unsigned int size)
        {
            unsigned int i;
            int max;

            if (size == 0)
                return (0);
            max = arr[0];
            i = 1;
            while (i < size)
            {
                if (arr[i] > max)
                    max = arr[i];
                i++;
            }
            return (max);
        }
        """),
        "cases": [
            [[]], [[5]], [[3, 1, 4, 1, 5, 9, 2, 6]], [[-5, -1, -10]],
            [[7, 7, 7]], [[-1, 0, 1]],
        ],
    },
    "is_palindrome_num": {
        "difficulty": "easy", "function": "is_palindrome_num",
        "prototype": "int is_palindrome_num(int n);",
        "args": ["int"], "returns": "int",
        "hint": ("Reject negative n up front — the spec says it's never "
                "a palindrome, and reversing a negative number's digits "
                "the naive way gives misleading results. Also make sure "
                "you compare the reversed value against a SAVED copy of "
                "the original n, not against n itself after you've "
                "already divided it down to 0 while building the "
                "reversal."),
        "subject": _sub_c("is_palindrome_num", "int is_palindrome_num(int n);",
                          "None", """
        Write a function that returns 1 if `n`'s decimal digits read the
        same forwards and backwards, 0 otherwise. Negative numbers are
        never palindromes.

        Examples:
            is_palindrome_num(121)  -> 1
            is_palindrome_num(-121) -> 0
            is_palindrome_num(10)   -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int is_palindrome_num(int n)
        {
            int original;
            int reversed;

            if (n < 0)
                return (0);
            original = n;
            reversed = 0;
            while (n > 0)
            {
                reversed = reversed * 10 + n % 10;
                n = n / 10;
            }
            return (reversed == original);
        }
        """),
        "cases": [
            [0], [1], [121], [-121], [12321], [123], [10], [1001],
        ],
    },

    # ── MEDIUM ───────────────────────────────────────────────
    "count_pairs_sum": {
        "difficulty": "medium", "function": "count_pairs_sum",
        "prototype": "int count_pairs_sum(int *arr, unsigned int size, int target);",
        "args": ["int_arr", "int"], "returns": "int",
        "hint": ("Keep the inner loop starting at j = i + 1, never j = 0 "
                "or j = i — starting from the beginning double-counts "
                "every pair as both (i,j) and (j,i), and letting i == j "
                "would wrongly pair an element with itself whenever "
                "target == 2 * arr[i]."),
        "subject": _sub_c("count_pairs_sum",
                          "int count_pairs_sum(int *arr, unsigned int size, int target);",
                          "None", """
        Write a function that returns how many pairs of DISTINCT indices
        (i, j), i < j, have arr[i] + arr[j] == target.

        Examples:
            count_pairs_sum([1,2,3,4], 4, 5) -> 2   ((1,4) and (2,3))
            count_pairs_sum([2,2,2,2], 4, 4) -> 6
        """),
        "oracle_c": textwrap.dedent("""
        int count_pairs_sum(int *arr, unsigned int size, int target)
        {
            unsigned int i;
            unsigned int j;
            int count;

            count = 0;
            i = 0;
            while (i < size)
            {
                j = i + 1;
                while (j < size)
                {
                    if (arr[i] + arr[j] == target)
                        count++;
                    j++;
                }
                i++;
            }
            return (count);
        }
        """),
        "cases": [
            [[], 0], [[1, 2, 3, 4], 5], [[1, 1, 1], 2],
            [[-1, 1, 0], 0], [[5], 5], [[2, 2, 2, 2], 4],
        ],
    },
    "kadane_max_sum": {
        "difficulty": "medium", "function": "kadane_max_sum",
        "prototype": "int kadane_max_sum(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": ("The classic Kadane's bug is flooring the running sum "
                "at 0 whenever it goes negative — that fails here, since "
                "an all-negative array like [-1,-2,-3] must still "
                "return -1, not 0. At each index there's only one "
                "decision: extend the running sum by the current "
                "element, or restart it there — never clamp it to 0 "
                "along the way."),
        "subject": _sub_c("kadane_max_sum",
                          "int kadane_max_sum(int *arr, unsigned int size);",
                          "None", """
        Write a function that returns the largest possible sum of a
        CONTIGUOUS subarray (at least one element). An empty array
        returns 0.

        Examples:
            kadane_max_sum([-2,1,-3,4,-1,2,1,-5,4], 9) -> 6   ([4,-1,2,1])
            kadane_max_sum([-1,-2,-3], 3)              -> -1
        """),
        "oracle_c": textwrap.dedent("""
        int kadane_max_sum(int *arr, unsigned int size)
        {
            unsigned int i;
            int max_ending_here;
            int max_so_far;

            if (size == 0)
                return (0);
            max_ending_here = arr[0];
            max_so_far = arr[0];
            i = 1;
            while (i < size)
            {
                if (max_ending_here + arr[i] > arr[i])
                    max_ending_here = max_ending_here + arr[i];
                else
                    max_ending_here = arr[i];
                if (max_ending_here > max_so_far)
                    max_so_far = max_ending_here;
                i++;
            }
            return (max_so_far);
        }
        """),
        "cases": [
            [[]], [[1]], [[-1]], [[-2, 1, -3, 4, -1, 2, 1, -5, 4]],
            [[5, 4, -1, 7, 8]], [[-1, -2, -3]],
        ],
    },
    "count_unique": {
        "difficulty": "medium", "function": "count_unique",
        "prototype": "int count_unique(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": ("For each element, only compare it against EARLIER "
                "elements (index < i) to decide whether it's a repeat — "
                "comparing against the whole array, including later "
                "occurrences, double-counts or under-counts each group "
                "of duplicates depending on which direction you scan."),
        "subject": _sub_c("count_unique",
                          "int count_unique(int *arr, unsigned int size);",
                          "None", """
        Write a function that returns how many DISTINCT values appear in
        an int array.

        Examples:
            count_unique([1,2,2,3,3,3], 6) -> 3
            count_unique([], 0)            -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int count_unique(int *arr, unsigned int size)
        {
            unsigned int i;
            unsigned int j;
            int count;
            int seen_before;

            count = 0;
            i = 0;
            while (i < size)
            {
                seen_before = 0;
                j = 0;
                while (j < i)
                {
                    if (arr[j] == arr[i])
                        seen_before = 1;
                    j++;
                }
                if (!seen_before)
                    count++;
                i++;
            }
            return (count);
        }
        """),
        "cases": [
            [[]], [[1, 1, 1]], [[1, 2, 3]], [[1, 2, 2, 3, 3, 3]],
            [[-1, -1, 0, 1]], [[5]],
        ],
    },

    # ── HARD ─────────────────────────────────────────────────
    "lis_length": {
        "difficulty": "hard", "function": "lis_length",
        "prototype": "int lis_length(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": {
            "crash": ("Indexing into `lengths` (or `arr`) before "
                     "checking size == 0 crashes on an empty array — "
                     "handle that case up front, before you malloc or "
                     "touch lengths[0]."),
            "leak": ("Every path that returns after the malloc has to "
                     "free `lengths` first — a leak here means some "
                     "return (including one you didn't expect to add) "
                     "skips that free."),
            "default": ("For each index i, look back at every earlier j "
                        "with arr[j] STRICTLY less than arr[i] (no <=, "
                        "or a run of equal values would count as "
                        "increasing) and keep the best lengths[j] + 1 — "
                        "that's the whole O(n^2) DP, nothing fancier "
                        "needed."),
        },
        "subject": _sub_c("lis_length", "int lis_length(int *arr, unsigned int size);",
                          "malloc, free", """
        Write a function that returns the length of the longest STRICTLY
        INCREASING subsequence of an int array — elements don't need to
        be contiguous, but must keep their original relative order. An
        empty array returns 0.

        Examples:
            lis_length([10,9,2,5,3,7,101,18], 8) -> 4   ([2,3,7,101] or [2,3,7,18])
            lis_length([7,7,7,7], 4)             -> 1
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        int lis_length(int *arr, unsigned int size)
        {
            unsigned int i;
            unsigned int j;
            int *lengths;
            int best;

            if (size == 0)
                return (0);
            lengths = malloc(sizeof(int) * size);
            if (!lengths)
                return (0);
            i = 0;
            while (i < size)
            {
                lengths[i] = 1;
                i++;
            }
            i = 1;
            while (i < size)
            {
                j = 0;
                while (j < i)
                {
                    if (arr[j] < arr[i] && lengths[j] + 1 > lengths[i])
                        lengths[i] = lengths[j] + 1;
                    j++;
                }
                i++;
            }
            best = lengths[0];
            i = 1;
            while (i < size)
            {
                if (lengths[i] > best)
                    best = lengths[i];
                i++;
            }
            free(lengths);
            return (best);
        }
        """),
        "cases": [
            [[]], [[1]], [[10, 9, 2, 5, 3, 7, 101, 18]], [[7, 7, 7, 7]],
            [[1, 2, 3, 4, 5]], [[5, 4, 3, 2, 1]],
        ],
    },
    "count_inversions": {
        "difficulty": "hard", "function": "count_inversions",
        "prototype": "int count_inversions(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": ("Only count a pair when arr[i] is STRICTLY greater than "
                "arr[j] (no >=) — equal values are not inversions, which "
                "is exactly why the [1,1,1] case expects 0. And start "
                "the inner loop at j = i + 1, not 0, or every "
                "out-of-order pair gets counted twice."),
        "subject": _sub_c("count_inversions",
                          "int count_inversions(int *arr, unsigned int size);",
                          "None", """
        Write a function that returns how many pairs of indices (i, j),
        i < j, have arr[i] > arr[j] — how far the array is from sorted.

        Examples:
            count_inversions([4,3,2,1], 4) -> 6   (every pair)
            count_inversions([1,2,3,4], 4) -> 0   (already sorted)
        """),
        "oracle_c": textwrap.dedent("""
        int count_inversions(int *arr, unsigned int size)
        {
            unsigned int i;
            unsigned int j;
            int count;

            count = 0;
            i = 0;
            while (i < size)
            {
                j = i + 1;
                while (j < size)
                {
                    if (arr[i] > arr[j])
                        count++;
                    j++;
                }
                i++;
            }
            return (count);
        }
        """),
        "cases": [
            [[]], [[1]], [[1, 2, 3, 4]], [[4, 3, 2, 1]],
            [[2, 4, 1, 3, 5]], [[1, 1, 1]],
        ],
    },
    "max_gap": {
        "difficulty": "hard", "function": "max_gap",
        "prototype": "int max_gap(int *arr, unsigned int size);",
        "args": ["int_arr"], "returns": "int",
        "hint": {
            "crash": ("Handle size < 2 before you malloc or touch the "
                     "copy — mallocing 0 bytes, or reading sorted[i - 1] "
                     "when there's nothing before index 0, is what "
                     "crashes on the empty and single-element cases."),
            "leak": ("The `sorted` copy is malloc'd — free it before "
                     "every return, including whichever early return "
                     "you added for the size < 2 case, or that path "
                     "leaks."),
            "default": ("You're required to sort a COPY, never the "
                        "caller's own array — sorting arr in place "
                        "passes the value checks but corrupts the "
                        "caller's data on any case that reuses it. Once "
                        "the copy is sorted, the answer is just the "
                        "largest difference between two ADJACENT "
                        "elements, not the overall min/max spread."),
        },
        "subject": _sub_c("max_gap", "int max_gap(int *arr, unsigned int size);",
                          "malloc, free", """
        Write a function that returns the maximum difference between two
        SUCCESSIVE elements once the array is sorted in ascending order.
        Fewer than 2 elements returns 0. Your own array must not be
        modified — sort a copy.

        Examples:
            max_gap([1,5,3,19,18,25], 6) -> 13  (sorted: 1,3,5,18,19,25)
            max_gap([3,3], 2)            -> 0
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        int max_gap(int *arr, unsigned int size)
        {
            int *sorted;
            unsigned int i;
            unsigned int j;
            int tmp;
            int max_diff;
            int diff;

            if (size < 2)
                return (0);
            sorted = malloc(sizeof(int) * size);
            if (!sorted)
                return (0);
            i = 0;
            while (i < size)
            {
                sorted[i] = arr[i];
                i++;
            }
            i = 0;
            while (i < size)
            {
                j = 0;
                while (j + 1 < size - i)
                {
                    if (sorted[j] > sorted[j + 1])
                    {
                        tmp = sorted[j];
                        sorted[j] = sorted[j + 1];
                        sorted[j + 1] = tmp;
                    }
                    j++;
                }
                i++;
            }
            max_diff = 0;
            i = 1;
            while (i < size)
            {
                diff = sorted[i] - sorted[i - 1];
                if (diff > max_diff)
                    max_diff = diff;
                i++;
            }
            free(sorted);
            return (max_diff);
        }
        """),
        "cases": [
            [[]], [[5]], [[1, 5, 3, 19, 18, 25]], [[1, 1, 1, 1]],
            [[3, 3]], [[-5, 0, 5, 10]],
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
        raise ValueError("c_exam.training_bank: %s has difficulty %r, expected one of %s"
                         % (_name, _d, DIFFICULTIES))
    TRAINING_BY_DIFFICULTY[_d].append(_name)
    _ex.setdefault("kind", "function")

for _d, _pool in TRAINING_BY_DIFFICULTY.items():
    if not _pool:
        raise ValueError("c_exam.training_bank: difficulty %r has no exercise" % _d)
