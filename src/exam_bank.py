#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam_bank.py  ·  42 Common Core  ·  Exam Rank 03 (Python)

Exercise bank for the ExamShell tester.

Each exercise provides:
  - level     : which exam level it belongs to (1..6)
  - function  : the exact function name the student must define
  - subject   : the full assignment text (shown to the student)
  - oracle    : verified reference implementation (used ONLY to compute the
                expected outputs -- students never see this at grading time)
  - cases     : curated edge-case inputs
  - fuzz      : callable(rng) -> args, generates extra randomized inputs

  ⚠  This file contains the reference solutions (answer key). Do not peek
     if you actually want to practice!
"""

import string
import textwrap

N_LEVELS = 6

# ══════════════════════════════════════════════════════════════
#  ORACLE  ·  verified reference implementations
# ══════════════════════════════════════════════════════════════
def _ref_cryptic_sorter(strings):
    return sorted(strings, key=lambda w: (len(w), w.lower(),
                  sum(ch.lower() in "aeiou" for ch in w)))

def _ref_inter(s1, s2):
    res = ""
    for ch in s1:
        if ch not in res and ch in s2:
            res += ch
    return res

def _ref_echo_validator(text):
    clean = "".join(ch.lower() for ch in text if ch.isalpha())
    if clean == "":
        return False
    return clean == clean[::-1]

def _ref_mirror_matrix(matrix):
    return [list(reversed(row)) for row in matrix]

def _ref_hidenp(small, big):
    it = iter(big)
    return all(ch in it for ch in small)

_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _ref_number_base_converter(number, from_base, to_base):
    # Deliberately does NOT use int(number, base): that would also accept
    # "+10", " 10 " and "1_0", which the subject says nothing about.
    # Every oracle must be self-contained (see grader.oracle_source), so the
    # digit table is defined here rather than pulled from the module.
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if not isinstance(number, str):
        return "ERROR"
    if not isinstance(from_base, int) or not isinstance(to_base, int):
        return "ERROR"
    if not 2 <= from_base <= 36 or not 2 <= to_base <= 36:
        return "ERROR"
    neg = number.startswith("-")
    body = number[1:] if neg else number
    if body == "":
        return "ERROR"
    dec = 0
    for ch in body.upper():
        value = digits.find(ch)
        if value < 0 or value >= from_base:
            return "ERROR"
        dec = dec * from_base + value
    if dec == 0:
        return "0"
    res = ""
    while dec > 0:
        res = digits[dec % to_base] + res
        dec //= to_base
    return ("-" + res) if neg else res

def _ref_pattern_tracker(text):
    cnt = 0
    for i in range(len(text) - 1):
        a, b = text[i], text[i + 1]
        if a.isdigit() and b.isdigit() and int(a) + 1 == int(b):
            cnt += 1
    return cnt

def _ref_anagram(s1, s2):
    a = sorted(s1.lower().replace(" ", ""))
    b = sorted(s2.lower().replace(" ", ""))
    return a == b

def _ref_shadow_merge(l1, l2):
    return sorted(l1 + l2)

def _ref_string_permutation_checker(s1, s2):
    return sorted(s1) == sorted(s2)

def _ref_string_sculptor(text):
    to_low = True
    res = ""
    for ch in text:
        if ch.isspace():
            to_low = True
        if ch.isalpha():
            res += ch.lower() if to_low else ch.upper()
            to_low = not to_low
        else:
            res += ch
    return res

def _ref_twist_sequence(arr, k):
    if not arr:
        return []
    k %= len(arr)
    return arr[-k:] + arr[:-k] if k else list(arr)

def _ref_bracket_validator(s):
    stack = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    for br in s:
        if br in pairs:
            stack.append(br)
        elif br in pairs.values():
            if not stack or pairs[stack.pop()] != br:
                return False
    return not stack

def _ref_whisper_cipher(text, shift):
    res = ""
    for ch in text:
        if "a" <= ch <= "z":
            res += chr((ord(ch) - 97 + shift) % 26 + 97)
        elif "A" <= ch <= "Z":
            res += chr((ord(ch) - 65 + shift) % 26 + 65)
        else:
            res += ch
    return res

# ══════════════════════════════════════════════════════════════
#  FUZZERS  ·  generate random valid inputs per exercise
# ══════════════════════════════════════════════════════════════
def _rand_word(rng, lo=0, hi=8, alphabet=None):
    alphabet = alphabet or string.ascii_letters
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi)))

def _rand_intlist(rng, lo=0, hi=8, vmin=-20, vmax=20):
    return [rng.randint(vmin, vmax) for _ in range(rng.randint(lo, hi))]

def _fuzz_cryptic_sorter(rng):
    alpha = string.ascii_letters + "  !?"
    return [[_rand_word(rng, 0, 6, alpha) for _ in range(rng.randint(0, 8))]]

def _fuzz_inter(rng):
    a = string.ascii_lowercase[:8]
    return [_rand_word(rng, 0, 12, a), _rand_word(rng, 0, 12, a)]

def _fuzz_echo_validator(rng):
    base = _rand_word(rng, 1, 5, "abcde")
    if rng.random() < 0.5:
        mid = rng.choice(["", rng.choice("abcde")])
        raw = base + mid + base[::-1]
    else:
        raw = _rand_word(rng, 1, 9, "abcde ")
    if rng.random() < 0.5:
        raw = " ".join(raw)
    if rng.random() < 0.5:
        raw = raw.upper()
    return [raw]

def _fuzz_mirror_matrix(rng):
    rows, cols = rng.randint(1, 4), rng.randint(1, 5)
    return [[[rng.randint(-9, 9) for _ in range(cols)] for _ in range(rows)]]

def _fuzz_hidenp(rng):
    big = _rand_word(rng, 0, 14, "abcABC123")
    if big and rng.random() < 0.6:
        idx = sorted(rng.sample(range(len(big)), rng.randint(0, len(big))))
        small = "".join(big[i] for i in idx)
    else:
        small = _rand_word(rng, 0, 6, "abcABC123")
    return [small, big]

def _fuzz_number_base_converter(rng):
    fb, tb = rng.randint(2, 36), rng.randint(2, 36)
    v = rng.randint(0, 100000)
    s = "0" if v == 0 else ""
    while v > 0:
        s = _DIGITS[v % fb] + s
        v //= fb
    if rng.random() < 0.20:                 # negative numbers
        s = "-" + s
    if rng.random() < 0.20:                 # digits are case-insensitive
        s = s.lower()
    if rng.random() < 0.15:                 # out-of-range base -> ERROR
        fb = rng.choice([0, 1, 37, 40, -2])
    elif rng.random() < 0.15:               # junk input -> ERROR
        s = rng.choice(["", "+1", " 1", "1_0", "1 ", "!", "-"])
    return [s, fb, tb]

def _fuzz_pattern_tracker(rng):
    return [_rand_word(rng, 0, 14, "0123456789abc")]

def _fuzz_anagram(rng):
    a = _rand_word(rng, 0, 8, "abcde ")
    if rng.random() < 0.5:
        lst = list(a); rng.shuffle(lst); b = "".join(lst)
        if rng.random() < 0.4:
            b = b.upper()
    else:
        b = _rand_word(rng, 0, 8, "abcde ")
    return [a, b]

def _fuzz_shadow_merge(rng):
    return [sorted(_rand_intlist(rng, 0, 7)), sorted(_rand_intlist(rng, 0, 7))]

def _fuzz_string_permutation_checker(rng):
    a = _rand_word(rng, 0, 8, "abAB 12")
    if rng.random() < 0.5:
        lst = list(a); rng.shuffle(lst); b = "".join(lst)
    else:
        b = _rand_word(rng, 0, 8, "abAB 12")
    return [a, b]

def _fuzz_string_sculptor(rng):
    return [_rand_word(rng, 0, 14, string.ascii_letters + "  123.!")]

def _fuzz_twist_sequence(rng):
    return [_rand_intlist(rng, 0, 9), rng.randint(0, 20)]

def _fuzz_bracket_validator(rng):
    return [_rand_word(rng, 0, 12, "()[]{}ab")]

def _fuzz_whisper_cipher(rng):
    return [_rand_word(rng, 0, 14, string.ascii_letters + " 12!"),
            rng.choice([-52, -30, -3, -1, 0, 1, 3, 13, 25, 26, 27, 52, 100])]

# ══════════════════════════════════════════════════════════════
#  SUBJECT BUILDER
# ══════════════════════════════════════════════════════════════
def _sub(name, body):
    head = (f"Assignment name  : {name}\n"
            f"Expected files   : {name}.py\n"
            f"Allowed functions: None\n"
            + "-" * 80 + "\n\n")
    return head + textwrap.dedent(body).strip("\n") + "\n"

# ══════════════════════════════════════════════════════════════
#  EXERCISE BANK
# ══════════════════════════════════════════════════════════════
EXERCISES = {
    # ── LEVEL 1 ────────────────────────────────────────────────
    "py_cryptic_sorter": {
        "level": 1, "function": "cryptic_sorter",
        "oracle": _ref_cryptic_sorter, "fuzz": _fuzz_cryptic_sorter,
        "subject": _sub("py_cryptic_sorter", """
        Write a function that sorts a list of strings by multiple criteria:
          1. Primary   : by length (shortest first)
          2. Secondary : ASCII order, letters compared case-insensitively
          3. Tertiary  : by number of vowels (ascending)
          4. Equal strings keep their original input order (stable).

            def cryptic_sorter(strings: list[str]) -> list[str]:

        Examples:
            cryptic_sorter(["apple","cat","banana","dog","elephant"])
                -> ["cat","dog","apple","banana","elephant"]
            cryptic_sorter(["aaa","bbb","AAA","BBB"]) -> ["aaa","AAA","bbb","BBB"]
            cryptic_sorter([]) -> []
        """),
        "cases": [
            [["apple", "cat", "banana", "dog", "elephant"]],
            [["aaa", "bbb", "AAA", "BBB"]],
            [["hello", "world", "hi", "test"]],
            [[]], [[""]], [["z", "a", "m"]], [["dog", "dog", "cat"]],
            [["Bb", "bb", "aa", "AA"]], [["a", "A", "b", "B"]],
            [["  ", " ", "   "]], [["xyz", "xya", "xyb"]],
            [["ee", "aa", "oo", "ii"]], [["Zoo", "zoo", "zoO"]],
        ],
    },
    "py_inter": {
        "level": 1, "function": "inter",
        "oracle": _ref_inter, "fuzz": _fuzz_inter,
        "subject": _sub("py_inter", """
        Write a function that returns a string with the characters that appear
        in BOTH strings, without repetitions, in the order of their first
        appearance in the FIRST string.

            def inter(s1: str, s2: str) -> str:

        Examples:
            inter("hello", "world") -> "lo"
            inter("banana", "band") -> "ban"
            inter("abc", "xyz")     -> ""
        """),
        "cases": [
            ["hello", "world"], ["banana", "band"], ["abcabc", "bc"],
            ["abc", "xyz"], ["", "abc"], ["abc", ""], ["aabbcc", "abc"],
            ["", ""], ["aaaa", "a"], ["12321", "13"], ["AaBb", "ab"],
            ["the quick", "brown fox"], ["mississippi", "sip"],
        ],
    },

    # ── LEVEL 2 ────────────────────────────────────────────────
    "py_echo_validator": {
        "level": 2, "function": "echo_validator",
        "oracle": _ref_echo_validator, "fuzz": _fuzz_echo_validator,
        "subject": _sub("py_echo_validator", """
        Write a function that checks whether a string is a palindrome.
        Only alphabetic characters are considered: case, spaces, digits and
        punctuation are all ignored. If there is no letter left to compare
        (empty string, "42", "!!!", …) the answer is False.

            def echo_validator(text: str) -> bool:

        Examples:
            echo_validator("racecar")                     -> True
            echo_validator("A man a plan a canal Panama") -> True
            echo_validator("No lemon, no melon")          -> True
            echo_validator("race a car")                  -> False
            echo_validator("")                            -> False
            echo_validator("12 21")                       -> False
        """),
        "cases": [
            ["racecar"], ["A man a plan a canal Panama"], ["race a car"],
            ["Was it a car or a cat I saw"], ["hello"], ["Madam Im Adam"],
            [""], ["a"], ["ab"], ["Aa"], ["Noon"], ["12 21"], ["!!!"],
            ["   "], ["a1b2a"], ["ab1ba"],
            ["No lemon, no melon"], ["Able was I ere I saw Elba"],
        ],
    },
    "py_mirror_matrix": {
        "level": 2, "function": "mirror_matrix",
        "oracle": _ref_mirror_matrix, "fuzz": _fuzz_mirror_matrix,
        "subject": _sub("py_mirror_matrix", """
        Given a 2D matrix (list of lists), return a NEW matrix where each row
        is reversed.

            def mirror_matrix(matrix: list[list[int]]) -> list[list[int]]:

        Examples:
            mirror_matrix([[1,2,3],[4,5,6]]) -> [[3,2,1],[6,5,4]]
            mirror_matrix([[7]])             -> [[7]]
        """),
        "cases": [
            [[[1, 2, 3], [4, 5, 6]]], [[[1, 2], [3, 4], [5, 6]]],
            [[[7]]], [[[1, 2, 3, 4]]], [[[-1, -2], [-3, -4]]],
            [[[]]], [[]], [[[0]]], [[[1], [2], [3]]],
            [[[5, 4, 3, 2, 1]]], [[[1, 1], [1, 1]]],
        ],
    },

    # ── LEVEL 3 ────────────────────────────────────────────────
    "py_number_base_converter": {
        "level": 3, "function": "number_base_converter",
        "oracle": _ref_number_base_converter, "fuzz": _fuzz_number_base_converter,
        "subject": _sub("py_number_base_converter", """
        Write a function that converts a number from one base to another.
        Both bases go from 2 to 36 inclusive. Digits are 0-9 then A-Z for the
        values 10-35; the OUTPUT always uses upper-case letters, the INPUT
        accepts either case. A leading '-' is allowed, nothing else is: no
        '+', no spaces, no underscores.

        Return the string "ERROR" for anything invalid: a base outside 2..36,
        an empty number, or a digit that does not exist in `from_base`.

            def number_base_converter(number: str, from_base: int, to_base: int) -> str:

        Examples:
            number_base_converter("1010", 2, 10) -> "10"
            number_base_converter("FF", 16, 10)  -> "255"
            number_base_converter("ff", 16, 10)  -> "255"
            number_base_converter("255", 10, 16) -> "FF"
            number_base_converter("-1010", 2, 10)-> "-10"
            number_base_converter("123", 1, 10)  -> "ERROR"
            number_base_converter("G", 16, 10)   -> "ERROR"
        """),
        "cases": [
            ["1010", 2, 10], ["FF", 16, 10], ["255", 10, 16], ["123", 10, 2],
            ["Z", 36, 10], ["35", 10, 36], ["123", 1, 10], ["G", 16, 10],
            ["0", 10, 2], ["1", 2, 10], ["0", 2, 16], ["ZZ", 36, 2],
            ["10", 2, 2], ["abc", 16, 10], ["", 10, 2], ["7", 8, 8],
            ["100", 10, 37], ["DEAD", 16, 10], ["11111111", 2, 16],
            ["-1010", 2, 10], ["-FF", 16, 10], ["-0", 10, 2], ["-", 10, 2],
            ["+10", 10, 2], [" 10", 10, 2], ["1_0", 2, 10], ["12", 2, 10],
            ["100", 10, 1], ["777", 8, 16], ["deadBEEF", 16, 36],
        ],
    },
    "py_pattern_tracker": {
        "level": 3, "function": "pattern_tracker",
        "oracle": _ref_pattern_tracker, "fuzz": _fuzz_pattern_tracker,
        "subject": _sub("py_pattern_tracker", """
        Write a function that counts valid consecutive digit pairs in a string.
        A valid pair is two adjacent digits where the second is exactly one
        greater than the first. A 9 followed by 0 is NOT valid.

            def pattern_tracker(text: str) -> int:

        Examples:
            pattern_tracker("123")       -> 2
            pattern_tracker("12a34")     -> 2
            pattern_tracker("987654321") -> 0
            pattern_tracker("90")        -> 0
        """),
        "cases": [
            ["123"], ["12a34"], ["987654321"], ["01234567"], ["abc"],
            ["1a2b3c4"], ["112233"], ["90"], [""], ["0"], ["89"],
            ["1234567890"], ["9012"], ["aa11bb22"], ["1223334444"],
        ],
    },
    "py_hidenp": {
        "level": 3, "function": "hidenp",
        "oracle": _ref_hidenp, "fuzz": _fuzz_hidenp,
        "subject": _sub("py_hidenp", """
        Write a function that checks whether 'small' is a subsequence of 'big'.
        A subsequence means all characters of 'small' appear in 'big' in the
        same order, but not necessarily consecutively. Case-sensitive.

            def hidenp(small: str, big: str) -> bool:

        Examples:
            hidenp("abc", "a1b2c3") -> True
            hidenp("ace", "abcde")  -> True
            hidenp("aec", "abcde")  -> False
            hidenp("", "abc")       -> True
        """),
        "cases": [
            ["abc", "a1b2c3"], ["ace", "abcde"], ["aec", "abcde"],
            ["", "abc"], ["", ""], ["abc", "ab"], ["xyz", "abc"],
            ["aaaa", "aaa"], ["aab", "aaab"], ["aba", "aabb"],
            ["abc", "ABC"], ["sing", "subsequence testing"], ["a", "a"],
            ["hello", "heeeelllooo"],
        ],
    },

    # ── LEVEL 4 ────────────────────────────────────────────────
    "py_anagram": {
        "level": 4, "function": "anagram",
        "oracle": _ref_anagram, "fuzz": _fuzz_anagram,
        "subject": _sub("py_anagram", """
        Write a function that checks whether two strings are anagrams.
        They must contain exactly the same letters in the same amounts,
        ignoring case and spaces.

            def anagram(s1: str, s2: str) -> bool:

        Examples:
            anagram("listen", "silent")        -> True
            anagram("Dormitory", "Dirty Room") -> True
            anagram("hello", "world")          -> False
            anagram("", "")                    -> True
        """),
        "cases": [
            ["listen", "silent"], ["Triangle", "Integral"],
            ["Dormitory", "Dirty Room"], ["Astronomer", "Moon starer"],
            ["hello", "world"], ["test", "ttew"], ["abc", "abcc"],
            ["", ""], ["a gentleman", "elegant man"], ["aabb", "ab"],
            ["a", "A"], ["ab ", " ba"], ["The eyes", "They see"],
        ],
    },
    "py_shadow_merge": {
        "level": 4, "function": "shadow_merge",
        "oracle": _ref_shadow_merge, "fuzz": _fuzz_shadow_merge,
        "subject": _sub("py_shadow_merge", """
        Write a function that merges two already-sorted lists into one sorted
        list.

            def shadow_merge(list1: list[int], list2: list[int]) -> list[int]:

        Examples:
            shadow_merge([1,3,5], [2,4,6]) -> [1,2,3,4,5,6]
            shadow_merge([], [1,2,3])      -> [1,2,3]
            shadow_merge([1,1,2], [1,3,3]) -> [1,1,1,2,3,3]
        """),
        "cases": [
            [[1, 3, 5], [2, 4, 6]], [[1, 2, 3], [4, 5, 6]], [[1], [2, 3, 4]],
            [[], [1, 2, 3]], [[1, 1, 2], [1, 3, 3]], [[], []], [[5], [5]],
            [[-3, -1], [-2, 0]], [[1, 2, 3], []], [[10], [1, 2, 3, 4, 5]],
        ],
    },
    "py_string_permutation_checker": {
        "level": 4, "function": "string_permutation_checker",
        "oracle": _ref_string_permutation_checker,
        "fuzz": _fuzz_string_permutation_checker,
        "subject": _sub("py_string_permutation_checker", """
        Write a function that determines whether two strings are permutations
        of each other. CASE-SENSITIVE. Whitespace and punctuation count as
        regular characters. Two empty strings are permutations.

            def string_permutation_checker(s1: str, s2: str) -> bool:

        Examples:
            string_permutation_checker("abc", "bca") -> True
            string_permutation_checker("Abc", "abc") -> False
            string_permutation_checker("", "")       -> True
        """),
        "cases": [
            ["abc", "bca"], ["abc", "def"], ["listen", "silent"],
            ["hello", "bello"], ["", ""], ["a", ""], ["Abc", "abc"],
            ["a gentleman", "elegant man"], ["aab", "aba"], ["a b", "b a"],
            ["!@#", "#@!"],
        ],
    },

    # ── LEVEL 5 ────────────────────────────────────────────────
    "py_string_sculptor": {
        "level": 5, "function": "string_sculptor",
        "oracle": _ref_string_sculptor, "fuzz": _fuzz_string_sculptor,
        "subject": _sub("py_string_sculptor", """
        Write a function that alternates the case of ALPHABETIC characters
        only. Non-alphabetic characters stay unchanged and are NOT counted in
        the alternation index. The first alpha is lowercase, the second
        uppercase, and so on. Whitespace resets the alternation (the next
        alpha after a space, tab or newline is lowercase again).

            def string_sculptor(text: str) -> str:

        Examples:
            string_sculptor("hello")       -> "hElLo"
            string_sculptor("Hello World") -> "hElLo wOrLd"
            string_sculptor("abc123def")   -> "aBc123DeF"
        """),
        "cases": [
            ["hello"], ["Hello World"], ["abc123def"], ["Python3.9!"],
            [""], ["a"], ["AB"], ["a b c"], ["  x"], ["12ab 34cd"],
            ["ONE two THREE"], ["a1b2c3d4"],
        ],
    },
    "py_twist_sequence": {
        "level": 5, "function": "twist_sequence",
        "oracle": _ref_twist_sequence, "fuzz": _fuzz_twist_sequence,
        "subject": _sub("py_twist_sequence", """
        Write a function that rotates an array to the RIGHT by k positions.
        Rotating right by k means the last k elements move to the front.
        k is never negative but may be larger than the length of the array.
        Return a NEW list; do not modify the one you were given.

            def twist_sequence(arr: list[int], k: int) -> list[int]:

        Examples:
            twist_sequence([1,2,3,4,5], 2) -> [4,5,1,2,3]
            twist_sequence([1,2,3], 5)     -> [2,3,1]
            twist_sequence([], 3)          -> []
        """),
        "cases": [
            [[1, 2, 3, 4, 5], 2], [[1, 2, 3], 1], [[1, 2, 3, 4], 0],
            [[1, 2, 3], 5], [[], 3], [[1], 1], [[1, 2], 4], [[1, 2, 3], 3],
            [[1, 2, 3, 4, 5], 7], [[9], 0], [[1, 2, 3, 4, 5, 6], 100],
        ],
    },

    # ── LEVEL 6 ────────────────────────────────────────────────
    "py_bracket_validator": {
        "level": 6, "function": "bracket_validator",
        "oracle": _ref_bracket_validator, "fuzz": _fuzz_bracket_validator,
        "subject": _sub("py_bracket_validator", """
        Write a function that checks whether the brackets in a string are
        valid. Valid means every opening bracket has a matching closing bracket
        in the correct order. Allowed brackets: (), [], {}. Other characters
        are ignored.

            def bracket_validator(s: str) -> bool:

        Examples:
            bracket_validator("()[]{}")       -> True
            bracket_validator("([)]")         -> False
            bracket_validator("hello(world)") -> True
            bracket_validator("")             -> True
        """),
        "cases": [
            ["()"], ["()[]{}"], ["(]"], ["([)]"], ["{[]}"],
            ["hello(world)[test]{code}"], ["((()))"], ["((())"], [""],
            ["["], ["}{"], [")("], ["{[()]}"], ["abc"], ["([{}])"],
        ],
    },
    "py_whisper_cipher": {
        "level": 6, "function": "whisper_cipher",
        "oracle": _ref_whisper_cipher, "fuzz": _fuzz_whisper_cipher,
        "subject": _sub("py_whisper_cipher", """
        Write a function that creates a Caesar cipher by shifting letters by a
        given amount. Non-alphabetic characters stay unchanged. The shift can
        be negative (shift left).

            def whisper_cipher(text: str, shift: int) -> str:

        Examples:
            whisper_cipher("hello", 3)        -> "khoor"
            whisper_cipher("Hello World!", 1) -> "Ifmmp Xpsme!"
            whisper_cipher("xyz", 3)          -> "abc"
            whisper_cipher("abc", -3)         -> "xyz"
        """),
        "cases": [
            ["hello", 3], ["Hello World!", 1], ["xyz", 3], ["ABC123def", 5],
            ["", 10], ["abc", -3], ["abc", 0], ["abc", 26], ["abc", 52],
            ["Zz", 1], ["abc", -29], ["The quick brown fox", 13],
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
        raise ValueError("exam_bank: %s has level %r, expected 1..%d"
                         % (_name, _lvl, N_LEVELS))
    LEVELS[_lvl].append(_name)

for _lvl, _pool in LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank: level %d has no exercise" % _lvl)


def signature_of(name):
    """The `def …:` line of an exercise, as shown in its subject."""
    for line in EXERCISES[name]["subject"].splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") and stripped.endswith(":"):
            return stripped
    return None