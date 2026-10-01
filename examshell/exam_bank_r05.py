#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam_bank_r05.py  ·  42 Common Core  ·  Exam Rank 05 (Python)

Exercise bank for the ExamShell tester, same shape as exam_bank.py (Rank
03) — see that module's docstring for what each key means.

What is different here:

  · 3 levels, not 6, and 7 exercises — every one a documented subject, so
    all 7 are "standard" and there is no Extra pool.
  · One subject (py_compress_decompress) asks for TWO functions. It uses
    the bank's "parts" key: one entry per function, each with its own
    oracle/cases/fuzz, all graded into a single verdict. See
    grader.parts_of().
  · Several subjects hand tuples in and out (schedule_meetings,
    prism_detector) or key a dict by int (graph_cycle_detector). Those
    survive the trip to the sandbox intact — see grader.encode_value().

Subjects, signatures and examples were taken from the published Rank 05
Python pool (rank05.42exam.net) and the behaviour re-derived from the
worked examples given there.

  ⚠  This file contains the reference solutions (answer key). Do not peek
     if you actually want to practice!
"""

import string

from .bank_common import sub as _sub
from .bank_common import signature_of as _signature_of

N_LEVELS = 3

# ══════════════════════════════════════════════════════════════
#  ORACLE  ·  verified reference implementations
#
#  Every oracle must be self-contained: no module-level helper, no
#  import, nothing but builtins and its own locals (a nested def is fine,
#  it is a local). grader.selftest() lifts each one into a standalone file
#  and grades it like a submission, which only works if it carries no free
#  globals (see grader.oracle_free_globals).
# ══════════════════════════════════════════════════════════════
def _ref_compress(s):
    out = ""
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        run = j - i
        out += s[i] if run == 1 else s[i] + str(run)
        i = j
    return out


def _ref_decompress(s):
    out = ""
    i = 0
    while i < len(s):
        ch = s[i]
        i += 1
        digits = ""
        while i < len(s) and s[i].isdigit():
            digits += s[i]
            i += 1
        out += ch * (int(digits) if digits else 1)
    return out


def _ref_generate_spiral(n):
    if n <= 0:
        return []
    grid = [[0] * n for _ in range(n)]
    top, bottom, left, right = 0, n - 1, 0, n - 1
    value = 1
    while top <= bottom and left <= right:
        for col in range(left, right + 1):
            grid[top][col] = value
            value += 1
        top += 1
        for row in range(top, bottom + 1):
            grid[row][right] = value
            value += 1
        right -= 1
        if top <= bottom:
            for col in range(right, left - 1, -1):
                grid[bottom][col] = value
                value += 1
            bottom -= 1
        if left <= right:
            for row in range(bottom, top - 1, -1):
                grid[row][left] = value
                value += 1
            left += 1
    return grid


def _ref_graph_cycle_detector(graph):
    # Iterative three-colour DFS (0 unvisited, 1 on the current path,
    # 2 finished). Iterative rather than recursive so a long chain cannot
    # blow the interpreter's stack inside the sandbox.
    color = {node: 0 for node in graph}
    for start in graph:
        if color[start] != 0:
            continue
        color[start] = 1
        stack = [(start, 0)]
        while stack:
            node, index = stack[-1]
            neighbours = graph[node]
            if index >= len(neighbours):
                color[node] = 2
                stack.pop()
                continue
            stack[-1] = (node, index + 1)
            nxt = neighbours[index]
            if nxt not in graph:
                continue          # an edge to a node that has no entry
            if color[nxt] == 1:
                return True
            if color[nxt] == 0:
                color[nxt] = 1
                stack.append((nxt, 0))
    return False


def _ref_schedule_meetings(intervals):
    rooms = []
    for meeting in sorted(intervals, key=lambda m: m[0]):
        placed = False
        for room in rooms:
            if room[-1][1] <= meeting[0]:
                room.append(tuple(meeting))
                placed = True
                break
        if not placed:
            rooms.append([tuple(meeting)])
    return (len(rooms), rooms)


def _ref_island_matrix_counter(matrix):
    # A visited set rather than sinking cells in place: the oracle is
    # graded like a submission and must not modify its input.
    seen = set()
    islands = 0
    for row in range(len(matrix)):
        for col in range(len(matrix[row])):
            if matrix[row][col] != "1" or (row, col) in seen:
                continue
            islands += 1
            seen.add((row, col))
            stack = [(row, col)]
            while stack:
                y, x = stack.pop()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if not (0 <= ny < len(matrix)):
                        continue
                    if not (0 <= nx < len(matrix[ny])):
                        continue
                    if (ny, nx) in seen or matrix[ny][nx] != "1":
                        continue
                    seen.add((ny, nx))
                    stack.append((ny, nx))
    return islands


def _ref_prism_detector(grid, pattern):
    if not grid or not pattern:
        return []
    directions = ((1, 0, "H"), (-1, 0, "H-"), (0, 1, "V"), (0, -1, "V-"),
                  (1, 1, "D1"), (-1, -1, "D1-"), (-1, 1, "D2"), (1, -1, "D2-"))
    found = []
    for y in range(len(grid)):
        for x in range(len(grid[y])):
            for dx, dy, code in directions:
                hit = True
                for step in range(len(pattern)):
                    ny, nx = y + dy * step, x + dx * step
                    if not (0 <= ny < len(grid) and 0 <= nx < len(grid[ny])):
                        hit = False
                        break
                    if grid[ny][nx] != pattern[step]:
                        hit = False
                        break
                if hit:
                    found.append((x, y, code))
    return found


def _ref_word_ladder(start, end, sentence):
    known = set(sentence)
    if end not in known:
        return 0
    if start == end:
        return 1

    def one_letter_apart(a, b):
        if len(a) != len(b):
            return False
        seen = 0
        for x, y in zip(a, b):
            if x != y:
                seen += 1
                if seen > 1:
                    return False
        return seen == 1

    unused = [w for w in known]
    unused.sort()
    frontier = [start]
    length = 1
    while frontier:
        length += 1
        following = []
        still_unused = []
        for word in unused:
            if any(one_letter_apart(word, current) for current in frontier):
                if word == end:
                    return length
                following.append(word)
            else:
                still_unused.append(word)
        unused = still_unused
        frontier = following
    return 0


# ══════════════════════════════════════════════════════════════
#  FUZZERS  ·  callable(rng) -> args
# ══════════════════════════════════════════════════════════════
def _fuzz_compress(rng):
    text = ""
    for _ in range(rng.randint(0, 6)):
        text += rng.choice(string.ascii_lowercase[:5]) * rng.randint(1, 13)
    return [text]


def _fuzz_decompress(rng):
    text = ""
    for _ in range(rng.randint(0, 6)):
        run = rng.randint(1, 13)
        ch = rng.choice(string.ascii_lowercase[:5])
        text += ch if run == 1 else ch + str(run)
    return [text]


def _fuzz_generate_spiral(rng):
    # The curated cases already cover 0..8 one by one, and build_tests()
    # drops a duplicate, so a narrow range here would add almost nothing.
    return [rng.randint(0, 16)]


def _fuzz_graph_cycle_detector(rng):
    n = rng.randint(0, 6)
    graph = {}
    for node in range(n):
        edges = []
        for _ in range(rng.randint(0, 2)):
            # mostly forward edges (acyclic), sometimes a backward one
            target = rng.randrange(n) if rng.random() < 0.35 \
                else rng.randint(node + 1, n) if node + 1 <= n else node
            if target < n:
                edges.append(target)
        graph[node] = edges
    return [graph]


def _fuzz_schedule_meetings(rng):
    meetings = []
    for _ in range(rng.randint(0, 7)):
        start = rng.randint(0, 20)
        meetings.append((start, start + rng.randint(0, 10)))
    return [meetings]


def _fuzz_island_matrix_counter(rng):
    rows = rng.randint(0, 6)
    cols = rng.randint(1, 6)
    return [[[rng.choice("1100") for _ in range(cols)] for _ in range(rows)]]


def _fuzz_prism_detector(rng):
    size = rng.randint(1, 5)
    grid = ["".join(rng.choice("CAT.") for _ in range(size))
            for _ in range(size)]
    pattern = "".join(rng.choice("CAT") for _ in range(rng.randint(1, 3)))
    return [grid, pattern]


def _fuzz_word_ladder(rng):
    def word(rng_):
        return "".join(rng_.choice("abc") for _ in range(3))
    start = word(rng)
    end = word(rng)
    sentence = [word(rng) for _ in range(rng.randint(0, 8))]
    return [start, end, sentence]


# ══════════════════════════════════════════════════════════════
#  EXERCISES
# ══════════════════════════════════════════════════════════════
EXERCISES = {

    # ── LEVEL 1 ────────────────────────────────────────────────
    "py_compress_decompress": {
        "level": 1, "function": "compress", "standard": True,
        # Two functions, one verdict — see grader.parts_of(). The exercise's
        # own oracle/cases/fuzz mirror the first part so everything that
        # only wants "the function this exercise is about" (stub signature,
        # --diff's code panel) keeps working.
        "oracle": _ref_compress, "fuzz": _fuzz_compress,
        "parts": [
            {"function": "compress", "oracle": _ref_compress,
             "fuzz": _fuzz_compress,
             "cases": [
                 ["aabcccccaaa"], [""], ["a"], ["aa"], ["abc"],
                 ["aaaaaaaaaaaa"], ["aabbaa"], ["zzzzzzzzzzzzz"],
                 ["abcdefghij"], ["qqqqqwww"], ["mississippi"],
             ]},
            {"function": "decompress", "oracle": _ref_decompress,
             "fuzz": _fuzz_decompress,
             "cases": [
                 ["a2bc5a3"], [""], ["a"], ["a12"], ["abc"],
                 ["z13"], ["a2b2a2"], ["q5w3"], ["m1i4s4p2"],
                 ["a10b10"], ["x100"],
             ]},
        ],
        "hint": {
            "default": ("compress and decompress are graded together, so "
                       "both have to be right. The count is omitted for a "
                       "run of exactly one ('abc' stays 'abc', it does not "
                       "become 'a1b1c1'), and decompress has to read a "
                       "MULTI-digit count as one number — 'a12' is twelve "
                       "a's, not 'aa' followed by a stray '2'. Keep "
                       "consuming digits while the next character is a "
                       "digit, then convert the whole run at once."),
            "crash": ("An index is running off the end of the string. Both "
                     "halves of this need a while-loop that advances by a "
                     "variable amount (a whole run for compress, a "
                     "character plus its digits for decompress), so every "
                     "inner loop needs its own `i < len(s)` guard before "
                     "it looks at s[i] — including the very last run, "
                     "where there is no next character to peek at."),
        },
        "subject": _sub("py_compress_decompress", """
        Write TWO functions: a run-length compressor and its exact inverse.

            def compress(s: str) -> str:
            def decompress(s: str) -> str:

        compress:
          · Collapse each run of repeated characters into the character
            followed by how many times it repeats.
          · A run of exactly ONE character keeps no number: "abc" stays
            "abc", it does not become "a1b1c1".
          · An empty string compresses to an empty string.
          · The input contains letters only.

        decompress:
          · Expand a compressed string back to its original form.
          · A count may have several digits: "a12" is twelve a's.
          · A character with no digits after it counts as one.

        Both functions are graded, so both must be defined in your file.

        Examples:
            compress("aabcccccaaa")   -> "a2bc5a3"
            decompress("a2bc5a3")     -> "aabcccccaaa"
            compress("")              -> ""
            decompress("a12")         -> "aaaaaaaaaaaa"
        """),
    },

    "py_spiral_generator": {
        "level": 1, "function": "generate_spiral", "standard": True,
        "oracle": _ref_generate_spiral, "fuzz": _fuzz_generate_spiral,
        # Named py_spiral_generator, not py_spiral_matrix as the published
        # pool has it: the training bank already ships a py_spiral_matrix
        # (spiral TRAVERSAL of an existing matrix, a different exercise),
        # and two subjects sharing one rendu/ filename but wanting
        # different functions is a trap, not a feature. The function name
        # itself is unchanged from the published subject.
        "hint": ("Track four walls — top, bottom, left, right — and shrink "
                "the one you just filled after each of the four passes. The "
                "usual bug is the last two passes on a leftover single row "
                "or single column: after filling the top row and the right "
                "column, `bottom` may already have crossed `top`, and "
                "re-running the bottom pass then writes over cells you "
                "already filled. Re-check `top <= bottom` before the "
                "right-to-left pass and `left <= right` before the "
                "bottom-to-top one."),
        "subject": _sub("py_spiral_generator", """
        Write a function that builds an n x n matrix filled with the
        numbers 1..n² in clockwise spiral order.

            def generate_spiral(n: int) -> list[list[int]]:

        The spiral starts at the top-left cell (0, 0) going right, then
        down, then left, then up, spiralling inwards. An n of 0 or less
        yields an empty list.

        Examples:
            generate_spiral(3) -> [[1, 2, 3], [8, 9, 4], [7, 6, 5]]
            generate_spiral(1) -> [[1]]
            generate_spiral(0) -> []
        """),
        "cases": [[0], [1], [2], [3], [4], [5], [6], [7], [-1], [8]],
    },

    # ── LEVEL 2 ────────────────────────────────────────────────
    "py_graph_cycle_detector": {
        "level": 2, "function": "graph_cycle_detector", "standard": True,
        "oracle": _ref_graph_cycle_detector, "fuzz": _fuzz_graph_cycle_detector,
        "forbidden": ("TopologicalSorter",),
        "hint": ("A plain visited set is not enough: revisiting a node you "
                "already FINISHED exploring (a diamond, two paths meeting "
                "again) is not a cycle, while revisiting one that is still "
                "on the path you are currently walking is. Track three "
                "states per node — untouched, on the current path, done — "
                "and report a cycle only when you reach a node in the "
                "second state. Start a fresh walk from every node, or a "
                "cycle sitting in a disconnected component goes unseen."),
        "subject": _sub("py_graph_cycle_detector", """
        Write a function that decides whether a DIRECTED graph contains at
        least one cycle.

            def graph_cycle_detector(graph: dict[int, list[int]]) -> bool:

        · graph is an adjacency list: each key is a node id, each value is
          the list of nodes it points at.
        · Return True when the graph contains a cycle, False when it is
          acyclic — including for an empty graph.
        · The graph may have several disconnected components; a cycle in
          any of them counts.
        · An edge pointing at a node that is not itself a key of the
          dictionary leads nowhere, and is not part of any cycle.

        (Some campuses name this function py_graph_cycle_detector — the
        behaviour asked for is the same.)

        Examples:
            graph_cycle_detector({0: [1], 1: [2], 2: [0]}) -> True
            graph_cycle_detector({0: [1], 1: [2], 2: []})  -> False
            graph_cycle_detector({})                       -> False
        """),
        "cases": [
            [{0: [1], 1: [2], 2: [0]}],
            [{0: [1], 1: [2], 2: []}],
            [{}],
            [{0: [0]}],
            [{0: []}],
            [{0: [1], 1: [], 2: [3], 3: [2]}],
            [{0: [1, 2], 1: [3], 2: [3], 3: []}],
            [{0: [1], 1: [2], 2: [3], 3: [1]}],
            [{0: [9]}],
            [{0: [1, 1], 1: []}],
            [{1: [2], 2: [3], 3: [4], 4: [5], 5: []}],
            [{0: [1], 1: [0], 2: []}],
        ],
    },

    "py_schedule_meetings": {
        "level": 2, "function": "schedule_meetings", "standard": True,
        "oracle": _ref_schedule_meetings, "fuzz": _fuzz_schedule_meetings,
        "hint": ("Sort by START time first — the assignment rule only makes "
                "sense on meetings taken in chronological order. Then, for "
                "each meeting, scan the rooms IN ORDER and take the first "
                "one whose last meeting has already ended; only open a new "
                "room when none has. 'Already ended' is end <= start, not "
                "end < start: a meeting ending exactly when the next one "
                "begins does not overlap it. Note the return type — a "
                "tuple (count, rooms), not a list."),
        "subject": _sub("py_schedule_meetings", """
        Write a function that works out the minimum number of meeting rooms
        needed for a list of meetings, and which meetings go where.

            def schedule_meetings(intervals: list[tuple[int, int]]) -> tuple[int, list]:

        · Each meeting is a (start_time, end_time) tuple.
        · Go through the meetings in order of start time and put each one
          in the FIRST room that is already free (a room is free when its
          last meeting ends at or before this one starts); open a new room
          only when no existing room is free.
        · Return a tuple (num_rooms, rooms), where rooms is a list of lists
          holding each room's meetings in the order they were assigned.
        · An empty input returns (0, []).

        Examples:
            schedule_meetings([(0,30), (5,10), (15,20)])
                -> (2, [[(0, 30)], [(5, 10), (15, 20)]])
            schedule_meetings([])                    -> (0, [])
            schedule_meetings([(0,5), (5,10)])       -> (1, [[(0, 5), (5, 10)]])
        """),
        "cases": [
            [[(0, 30), (5, 10), (15, 20)]],
            [[]],
            [[(0, 5), (5, 10)]],
            [[(0, 5)]],
            [[(0, 10), (0, 10), (0, 10)]],
            [[(5, 10), (0, 30), (15, 20)]],
            [[(1, 2), (3, 4), (5, 6)]],
            [[(0, 1), (0, 2), (1, 3)]],
            [[(7, 10), (2, 4)]],
            [[(0, 0), (0, 0)]],
            [[(1, 5), (2, 6), (3, 7), (4, 8)]],
        ],
    },

    "py_island_matrix_counter": {
        "level": 2, "function": "island_matrix_counter", "standard": True,
        "oracle": _ref_island_matrix_counter, "fuzz": _fuzz_island_matrix_counter,
        "hint": ("Count one island per NEW starting cell, then flood the "
                "whole island before moving on — if you increment once per "
                "'1' you find, a five-cell island counts as five. The "
                "flood has to be exhaustive (a stack or a queue, or "
                "recursion) and must mark cells as visited the moment it "
                "queues them, or the same cell gets pushed several times "
                "and a large island can loop forever. Only the four "
                "orthogonal neighbours connect — no diagonals — and the "
                "cells hold one-character STRINGS, not the integers 1 and "
                "0, so compare against '1' rather than 1."),
        "subject": _sub("py_island_matrix_counter", """
        Write a function that counts the islands in a 2D matrix of the
        strings "1" (land) and "0" (water).

            def island_matrix_counter(matrix: list[list[str]]) -> int:

        · An island is a group of "1" cells connected horizontally or
          vertically. Diagonal neighbours do NOT connect.
        · Count each separate island exactly once.
        · An empty matrix (or one with no rows) returns 0.
        · Do not modify the matrix you were given — make your own copy or
          keep your own set of visited cells.

        Examples:
            island_matrix_counter([["1","1","1","1","0"],
                                   ["1","1","1","0","0"],
                                   ["1","1","1","1","0"],
                                   ["0","0","0","0","0"]]) -> 1
            island_matrix_counter([["1","1","0","0","0"],
                                   ["1","1","0","0","0"],
                                   ["0","0","1","0","0"],
                                   ["0","0","0","1","1"]]) -> 3
            island_matrix_counter([])                       -> 0
        """),
        "cases": [
            [[["1", "1", "1", "1", "0"], ["1", "1", "1", "0", "0"],
              ["1", "1", "1", "1", "0"], ["0", "0", "0", "0", "0"]]],
            [[["1", "1", "0", "0", "0"], ["1", "1", "0", "0", "0"],
              ["0", "0", "1", "0", "0"], ["0", "0", "0", "1", "1"]]],
            [[]],
            [[["0"]]],
            [[["1"]]],
            [[["1", "0", "1", "0", "1"]]],
            [[["1"], ["0"], ["1"]]],
            [[["1", "0"], ["0", "1"]]],
            [[["0", "0"], ["0", "0"]]],
            [[["1", "1"], ["1", "1"]]],
            [[["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]]],
            [[["1", "1", "1"], ["0", "1", "0"], ["1", "1", "1"]]],
        ],
    },

    # ── LEVEL 3 ────────────────────────────────────────────────
    "py_prism_detector": {
        "level": 3, "function": "prism_detector", "standard": True,
        "oracle": _ref_prism_detector, "fuzz": _fuzz_prism_detector,
        "hint": ("Mind the coordinate order: a match is reported as "
                "(x, y, code) where x is the COLUMN and y is the ROW, but "
                "the character at that spot is grid[y][x] — the two are "
                "swapped relative to each other, and getting it wrong is "
                "invisible on a square grid full of symmetric matches. "
                "Bounds-check every single step of a candidate before "
                "indexing (a negative index does not raise in Python, it "
                "silently wraps to the other end of the row and reports a "
                "match that isn't there). Finally, the order of the "
                "returned list follows the direction table as it is "
                "written, so walk the directions in that order for each "
                "cell."),
        "subject": _sub("py_prism_detector", """
        Write a function that finds every occurrence of a pattern inside a
        2D grid of characters, in all 8 directions.

            def prism_detector(grid: list[str], pattern: str) -> list[tuple]:

        The (dx, dy) directions and the code each one reports, in this
        order:

            (1, 0)    "H"     horizontal, right
            (-1, 0)   "H-"    horizontal, left
            (0, 1)    "V"     vertical, down
            (0, -1)   "V-"    vertical, up
            (1, 1)    "D1"    diagonal, down-right
            (-1, -1)  "D1-"   diagonal, up-left
            (-1, 1)   "D2"    diagonal, up-right
            (1, -1)   "D2-"   diagonal, down-left

        · Return a list of (x, y, direction_code) tuples, one per match,
          where x is the column and y is the row of the pattern's FIRST
          character.
        · Scan the grid row by row, left to right, and try the directions
          in the order listed above.
        · Return [] when either the grid or the pattern is empty.

        Examples:
            prism_detector(["CAT", "A..", "T.."], "CAT")
                -> [(0, 0, "H"), (0, 0, "V")]
            prism_detector([], "CAT")   -> []
            prism_detector(["CAT"], "") -> []
        """),
        "cases": [
            [["CAT", "A..", "T.."], "CAT"],
            [[], "CAT"],
            [["CAT"], ""],
            [["CAT"], "CAT"],
            [["TAC"], "CAT"],
            [["C.", ".A"], "CA"],
            [["..C", ".A.", "T.."], "CAT"],
            [["AA", "AA"], "A"],
            [["AA", "AA"], "AA"],
            [["CAT", "CAT", "CAT"], "CCC"],
            [["...", "...", "..."], "C"],
            [["ABC", "DEF", "GHI"], "AEI"],
        ],
    },

    "py_word_ladder": {
        "level": 3, "function": "word_ladder", "standard": True,
        "oracle": _ref_word_ladder, "fuzz": _fuzz_word_ladder,
        "hint": ("Shortest path means breadth-first, one whole level at a "
                "time — a depth-first walk finds *a* ladder, rarely the "
                "shortest. Count WORDS, not steps: hit -> hot -> dot -> "
                "dog -> cog is 5, so the start word already counts as 1. "
                "Two words are neighbours when they have the same length "
                "and differ at exactly one position. And mark a word as "
                "used the moment you enqueue it, or the search revisits it "
                "forever; if the end word is not in the list at all there "
                "is no ladder, so return 0."),
        "subject": _sub("py_word_ladder", """
        Write a function that returns the length of the SHORTEST
        transformation sequence turning `start` into `end`.

            def word_ladder(start: str, end: str, sentence: list[str]) -> int:

        · Each step changes exactly one character.
        · Every word you pass through (the end word included) must be in
          `sentence`; the start word need not be.
        · Return the number of words in the shortest ladder, counting both
          `start` and `end`.
        · Return 0 when no such sequence exists — including when `end` is
          not in `sentence` at all.
        · When `start` and `end` are the same word (and it is in
          `sentence`), the ladder is that one word: return 1.

        Examples:
            word_ladder("hit", "cog", ["hot","dot","dog","lot","log","cog"]) -> 5
            word_ladder("hit", "cog", ["hot","dot","dog","lot","log"])       -> 0
            word_ladder("hit", "hot", ["hot"])                               -> 2
        """),
        "cases": [
            ["hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]],
            ["hit", "cog", ["hot", "dot", "dog", "lot", "log"]],
            ["hit", "hot", ["hot"]],
            ["hit", "hit", ["hit"]],
            ["hit", "hit", []],
            ["abc", "abc", ["abc"]],
            ["aaa", "bbb", ["aab", "abb", "bbb"]],
            ["aaa", "bbb", ["aab", "bbb"]],
            ["a", "c", ["b", "c"]],
            ["hot", "dog", ["hot", "dog", "dot"]],
            ["red", "tax", ["ted", "tex", "tax", "tad", "den", "rex", "pee"]],
            ["cat", "dog", []],
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
        raise ValueError("exam_bank_r05: %s has level %r, expected 1..%d"
                         % (_name, _lvl, N_LEVELS))
    LEVELS[_lvl].append(_name)
    _ex.setdefault("standard", False)

for _lvl, _pool in LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank_r05: level %d has no exercise" % _lvl)

# Every exercise here is a documented Rank 05 subject, so the Standard pool
# (what `make exam` draws from) is the whole bank — see exam_bank_r04.py.
STANDARD_LEVELS = {lvl: [name for name in pool if EXERCISES[name]["standard"]]
                   for lvl, pool in LEVELS.items()}

for _lvl, _pool in STANDARD_LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank_r05: level %d has no standard exercise" % _lvl)


def signature_of(name):
    """The `def …:` line of an exercise, as shown in its subject."""
    return _signature_of(EXERCISES[name]["subject"])
