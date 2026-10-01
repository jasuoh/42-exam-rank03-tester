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

from .bank_common import sub as _sub
from .bank_common import signature_of as _signature_of

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

def _ref_vowel_counter(text):
    return sum(1 for ch in text if ch.lower() in "aeiou")

def _ref_capitalizer(text):
    return " ".join(w[:1].upper() + w[1:].lower() for w in text.split(" "))

def _ref_digit_extractor(text):
    return [int(ch) for ch in text if ch in "0123456789"]

def _ref_case_counter(text):
    upper = sum(1 for ch in text if ch.isupper())
    lower = sum(1 for ch in text if ch.islower())
    return [upper, lower]

def _ref_word_reverser(text):
    return " ".join(w[::-1] for w in text.split(" "))

def _ref_unique_elements(lst):
    counts = {}
    for item in lst:
        counts[item] = counts.get(item, 0) + 1
    return [item for item in lst if counts[item] == 1]

def _ref_matrix_transposer(matrix):
    if not matrix:
        return []
    return [list(row) for row in zip(*matrix)]

def _ref_longest_word(text):
    words = [w for w in text.split(" ") if w]
    if not words:
        return ""
    best = words[0]
    for w in words[1:]:
        if len(w) > len(best):
            best = w
    return best

def _ref_matrix_rotator(matrix):
    if not matrix:
        return []
    return [list(row) for row in zip(*matrix[::-1])]

def _ref_prime_finder(n):
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True

def _ref_leet_speak(text):
    table = {"a": "4", "A": "4", "e": "3", "E": "3",
             "i": "1", "I": "1", "o": "0", "O": "0"}
    return "".join(table.get(ch, ch) for ch in text)

def _ref_char_frequency(text):
    if not text:
        return ""
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    best_ch, best_n = text[0], 0
    for ch in text:
        if counts[ch] > best_n:
            best_ch, best_n = ch, counts[ch]
    return best_ch

def _ref_run_length_encoder(text):
    if not text:
        return ""
    res, prev, count = "", text[0], 0
    for ch in text:
        if ch == prev:
            count += 1
        else:
            res += prev + str(count)
            prev, count = ch, 1
    res += prev + str(count)
    return res

def _ref_second_largest(lst):
    uniq = sorted(set(lst), reverse=True)
    return uniq[1] if len(uniq) >= 2 else None

def _ref_run_length_decoder(text):
    res, i = "", 0
    while i < len(text):
        ch = text[i]
        i += 1
        digits = ""
        while i < len(text) and text[i].isdigit():
            digits += text[i]
            i += 1
        res += ch * int(digits) if digits else ch
    return res

def _ref_binary_gap(n):
    bits = bin(n)[2:]
    segments = bits.split("1")
    middle = segments[1:-1]
    return max((len(s) for s in middle), default=0)

def _ref_pangram_checker(text):
    letters = set(ch.lower() for ch in text if ch.isalpha())
    return len(letters) == 26

def _ref_max_subarray_sum(lst):
    if not lst:
        return 0
    best = cur = lst[0]
    for x in lst[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best

def _ref_zigzag_flatten(matrix):
    res = []
    for i, row in enumerate(matrix):
        res.extend(row if i % 2 == 0 else row[::-1])
    return res

def _ref_pascals_triangle_row(n):
    row = [1]
    for _ in range(n):
        row = [1] + [row[i] + row[i + 1] for i in range(len(row) - 1)] + [1]
    return row

def _ref_longest_palindromic_substring(text):
    if not text:
        return ""
    start, max_len = 0, 1

    def expand(l, r):
        while l >= 0 and r < len(text) and text[l] == text[r]:
            l -= 1
            r += 1
        return l + 1, r - l - 1

    for i in range(len(text)):
        s1, l1 = expand(i, i)
        if l1 > max_len:
            start, max_len = s1, l1
        s2, l2 = expand(i, i + 1)
        if l2 > max_len:
            start, max_len = s2, l2
    return text[start:start + max_len]

def _ref_two_sum_indices(lst, target):
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i] + lst[j] == target:
                return [i, j]
    return []

def _ref_string_reverser(text):
    return text[::-1]

def _ref_char_counter(text, ch):
    count = 0
    for c in text:
        if c == ch:
            count += 1
    return count

def _ref_even_odd_counter(lst):
    even = sum(1 for x in lst if x % 2 == 0)
    return [even, len(lst) - even]

def _ref_sum_of_squares(lst):
    total = 0
    for x in lst:
        total += x * x
    return total

def _ref_longest_common_prefix(strings):
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix

def _ref_camel_to_snake_converter(text):
    res = ""
    for ch in text:
        if ch.isupper():
            res += "_" + ch.lower()
        else:
            res += ch
    return res

def _ref_string_rotation_checker(s1, s2):
    if len(s1) != len(s2):
        return False
    return s2 in (s1 + s1)

def _ref_roman_numeral(n):
    values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    symbols = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    res = ""
    for value, symbol in zip(values, symbols):
        while n >= value:
            res += symbol
            n -= value
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

def _fuzz_vowel_counter(rng):
    return [_rand_word(rng, 0, 16, string.ascii_letters + "  123!?")]

def _fuzz_capitalizer(rng):
    return [_rand_word(rng, 0, 16, string.ascii_letters + "   ")]

def _fuzz_digit_extractor(rng):
    return [_rand_word(rng, 0, 16, string.ascii_letters + "0123456789 !?")]

def _fuzz_case_counter(rng):
    return [_rand_word(rng, 0, 16, string.ascii_letters + "  123!?")]

def _fuzz_word_reverser(rng):
    return [_rand_word(rng, 0, 20, string.ascii_letters + "   ")]

def _fuzz_unique_elements(rng):
    return [_rand_intlist(rng, 0, 10, vmin=-5, vmax=5)]

def _fuzz_matrix_transposer(rng):
    rows, cols = rng.randint(1, 4), rng.randint(1, 4)
    return [[[rng.randint(-9, 9) for _ in range(cols)] for _ in range(rows)]]

def _fuzz_longest_word(rng):
    return [_rand_word(rng, 0, 24, string.ascii_letters + "   ")]

def _fuzz_matrix_rotator(rng):
    rows, cols = rng.randint(1, 4), rng.randint(1, 4)
    return [[[rng.randint(-9, 9) for _ in range(cols)] for _ in range(rows)]]

def _fuzz_prime_finder(rng):
    if rng.random() < 0.3:
        return [rng.randint(-10, 1)]
    return [rng.randint(2, 500)]

def _fuzz_leet_speak(rng):
    return [_rand_word(rng, 0, 20, string.ascii_letters + " !?0123")]

def _fuzz_char_frequency(rng):
    return [_rand_word(rng, 0, 16, "aabbccdd 123!")]

def _fuzz_run_length_encoder(rng):
    n = rng.randint(0, 12)
    return ["".join(rng.choice("abc") for _ in range(n))]

def _fuzz_second_largest(rng):
    return [_rand_intlist(rng, 0, 8, vmin=-10, vmax=10)]

def _fuzz_run_length_decoder(rng):
    n = rng.randint(0, 5)
    parts = [rng.choice("abcdef") + str(rng.randint(1, 20)) for _ in range(n)]
    return ["".join(parts)]

def _fuzz_binary_gap(rng):
    return [rng.randint(0, 5000)]

def _fuzz_pangram_checker(rng):
    if rng.random() < 0.5:
        letters = list(string.ascii_lowercase)
        rng.shuffle(letters)
        extra = _rand_word(rng, 0, 5, string.ascii_letters + " .")
        return [" ".join(letters) + extra]
    return [_rand_word(rng, 0, 30, string.ascii_letters + "   .")]

def _fuzz_max_subarray_sum(rng):
    return [_rand_intlist(rng, 0, 10, vmin=-10, vmax=10)]

def _fuzz_zigzag_flatten(rng):
    rows = rng.randint(0, 5)
    return [[[rng.randint(-9, 9) for _ in range(rng.randint(0, 5))]
             for _ in range(rows)]]

def _fuzz_pascals_triangle_row(rng):
    return [rng.randint(0, 15)]

def _fuzz_longest_palindromic_substring(rng):
    alphabet = "ab" if rng.random() < 0.4 else string.ascii_lowercase
    return [_rand_word(rng, 0, 14, alphabet)]

def _fuzz_two_sum_indices(rng):
    lst = _rand_intlist(rng, 0, 8, vmin=-10, vmax=10)
    if len(lst) >= 2 and rng.random() < 0.5:
        i, j = rng.sample(range(len(lst)), 2)
        target = lst[i] + lst[j]
    else:
        target = rng.randint(-15, 15)
    return [lst, target]

def _fuzz_string_reverser(rng):
    return [_rand_word(rng, 0, 16, string.ascii_letters + " 123!?")]

def _fuzz_char_counter(rng):
    alphabet = "aabbccdd 123!"
    return [_rand_word(rng, 0, 20, alphabet), rng.choice(alphabet)]

def _fuzz_even_odd_counter(rng):
    return [_rand_intlist(rng, 0, 12, vmin=-15, vmax=15)]

def _fuzz_sum_of_squares(rng):
    return [_rand_intlist(rng, 0, 10, vmin=-10, vmax=10)]

def _fuzz_longest_common_prefix(rng):
    n = rng.randint(0, 6)
    if n == 0:
        return [[]]
    prefix = _rand_word(rng, 0, 5, string.ascii_lowercase)
    strings = []
    for _ in range(n):
        if rng.random() < 0.8:
            strings.append(prefix + _rand_word(rng, 0, 6, string.ascii_lowercase))
        else:
            strings.append(_rand_word(rng, 0, 8, string.ascii_lowercase))
    return [strings]

def _fuzz_camel_to_snake_converter(rng):
    return [_rand_word(rng, 0, 16, string.ascii_letters + "0123456789")]

def _fuzz_string_rotation_checker(rng):
    alphabet = string.ascii_lowercase[:6]
    base = _rand_word(rng, 0, 10, alphabet)
    if base and rng.random() < 0.6:
        k = rng.randint(0, len(base) - 1)
        rotated = base[k:] + base[:k]
        if rng.random() < 0.3:
            chars = list(rotated)
            idx = rng.randrange(len(chars))
            chars[idx] = rng.choice(alphabet)
            rotated = "".join(chars)
    else:
        rotated = _rand_word(rng, 0, 10, alphabet)
    return [base, rotated]

def _fuzz_roman_numeral(rng):
    return [rng.randint(1, 3999)]

# ══════════════════════════════════════════════════════════════
#  EXERCISE BANK
# ══════════════════════════════════════════════════════════════
EXERCISES = {
    # ── LEVEL 1 ────────────────────────────────────────────────
    "py_cryptic_sorter": {
        "level": 1, "function": "cryptic_sorter", "standard": True,
        "oracle": _ref_cryptic_sorter, "fuzz": _fuzz_cryptic_sorter,
        "forbidden": ("sorted", "sort"),
        "hint": ("sorted()/list.sort() are off-limits for this one — "
                "implement the ordering yourself (an insertion sort is "
                "plenty). Compare each pair of strings by a single tuple "
                "of all three criteria in exactly this order (length, "
                "then the word case-insensitively, then vowel count) — "
                "Python compares tuples lexicographically, so one "
                "tuple-vs-tuple comparison covers all three at once; "
                "don't compare in several separate passes, that breaks "
                "stability for equal words."),
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
        "level": 1, "function": "inter", "standard": True,
        "oracle": _ref_inter, "fuzz": _fuzz_inter,
        "hint": ("Build the result by scanning s1 (not s2) and keep a "
                "character only the first time you meet it — a set "
                "intersection is tempting but sets don't preserve order, "
                "so you'd still need to re-sort by position in s1 "
                "afterwards; just walk s1 once, keeping a character when "
                "it's in s2 and not already in your result."),
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

    "py_vowel_counter": {
        "level": 1, "function": "vowel_counter",
        "oracle": _ref_vowel_counter, "fuzz": _fuzz_vowel_counter,
        "hint": ("Check both cases of each vowel (or lowercase the "
                "character before comparing) — and leave 'y' out of your "
                "vowel set entirely, even though some people count it as "
                "one, this exercise doesn't."),
        "subject": _sub("py_vowel_counter", """
        Write a function that counts the vowels (a, e, i, o, u) in a string,
        case-insensitively. Accented letters and 'y' do not count.

            def vowel_counter(text: str) -> int:

        Examples:
            vowel_counter("hello")               -> 2
            vowel_counter("The Quick Brown Fox")  -> 4
            vowel_counter("")                     -> 0
            vowel_counter("xyz")                  -> 0
        """),
        "cases": [
            ["hello"], ["HELLO"], [""], ["xyz"], ["AEIOUaeiou"],
            ["The Quick Brown Fox"], ["1234"], ["   "], ["aAeEiIoOuU"],
            ["bcdfg"], ["y"], ["Y"],
        ],
    },
    "py_capitalizer": {
        "level": 1, "function": "capitalizer",
        "oracle": _ref_capitalizer, "fuzz": _fuzz_capitalizer,
        "hint": ("Split on \" \" specifically, not a bare .split() — a "
                "bare split collapses consecutive spaces and silently "
                "drops the empty 'words' they create, which this "
                "exercise expects you to keep untouched. Rejoin with "
                "\" \".join() so the original spacing is preserved."),
        "subject": _sub("py_capitalizer", """
        Write a function that capitalizes the first letter of every word and
        lowercases the rest. Words are separated by single spaces: runs of
        several spaces produce empty "words" that must stay empty (not
        turned into extra spaces or removed).

            def capitalizer(text: str) -> str:

        Examples:
            capitalizer("hello world")  -> "Hello World"
            capitalizer("HELLO WORLD")  -> "Hello World"
            capitalizer("")             -> ""
            capitalizer("a  b")         -> "A  B"
        """),
        "cases": [
            ["hello world"], ["HELLO WORLD"], [""], ["a"], ["  a  b  "],
            ["already Capitalized"], ["multiple   spaces"],
            ["ALL CAPS HERE"], ["mixed CaSe TeXt"], [" "], ["a b c"],
        ],
    },

    "py_leet_speak": {
        "level": 1, "function": "leet_speak",
        "oracle": _ref_leet_speak, "fuzz": _fuzz_leet_speak,
        "hint": ("Only a/e/i/o get replaced — 'u' and 'U' must stay "
                "exactly as they are, unlike some leetspeak conventions "
                "you might know that also turn u into something else. "
                "Every other character (consonants, digits, "
                "punctuation) passes through unchanged, case included."),
        "subject": _sub("py_leet_speak", """
        Write a function that turns text into leetspeak by replacing
        vowels with digits: a/A -> 4, e/E -> 3, i/I -> 1, o/O -> 0.
        'u'/'U' and every other character stay unchanged, including case.

            def leet_speak(text: str) -> str:

        Examples:
            leet_speak("hello")  -> "h3ll0"
            leet_speak("aeiou")  -> "4310u"
            leet_speak("")       -> ""
        """),
        "cases": [
            ["hello"], ["LEET SPEAK"], [""], ["aeiou"], ["AEIOU"],
            ["The Quick Brown Fox"], ["xyz"], ["AaEeIiOo"], ["u U"],
            ["123abc"],
        ],
    },
    "py_char_frequency": {
        "level": 1, "function": "char_frequency",
        "oracle": _ref_char_frequency, "fuzz": _fuzz_char_frequency,
        "hint": ("Tie-breaking matters: when several characters share "
                "the highest count, return whichever one reaches that "
                "count first while scanning left to right — count "
                "everything in one pass, then scan again and take the "
                "first character whose count equals the maximum. Don't "
                "sort by count, that can silently reorder tied "
                "characters. Handle the empty string separately."),
        "subject": _sub("py_char_frequency", """
        Write a function that returns the most frequent character in a
        string (case-sensitive). If several characters are tied for the
        highest count, return whichever of them reaches that count first
        while scanning the string from left to right. An empty string
        returns "".

            def char_frequency(text: str) -> str:

        Examples:
            char_frequency("aabbb")  -> "b"
            char_frequency("aabb")   -> "a"
            char_frequency("")       -> ""
        """),
        "cases": [
            ["aabbb"], ["aabb"], [""], ["a"], ["abcabc"], ["xxxxxxx"],
            ["Aa"], ["   "], ["112233"], ["!!!???"],
        ],
    },

    "py_string_reverser": {
        "level": 1, "function": "string_reverser",
        "oracle": _ref_string_reverser, "fuzz": _fuzz_string_reverser,
        "hint": ("If you're building the result with an index-based "
                "loop instead of slicing, check your bounds carefully — "
                "starting the range at len(text) instead of "
                "len(text) - 1, or getting the stop condition wrong, is "
                "the classic off-by-one here."),
        "subject": _sub("py_string_reverser", """
        Write a function that returns a string reversed.

            def string_reverser(text: str) -> str:

        Examples:
            string_reverser("hello")  -> "olleh"
            string_reverser("ab")     -> "ba"
            string_reverser("")       -> ""
        """),
        "cases": [
            ["hello"], [""], ["a"], ["ab"], ["racecar"], ["Hello World"],
            ["12345"], ["   "], ["a b c"], ["!@#$%"],
        ],
    },
    "py_char_counter": {
        "level": 1, "function": "char_counter",
        "oracle": _ref_char_counter, "fuzz": _fuzz_char_counter,
        "hint": ("Comparison is case-sensitive — don't lowercase text "
                "or ch before comparing, 'o' and 'O' are different "
                "characters here."),
        "subject": _sub("py_char_counter", """
        Write a function that counts how many times a character appears in
        a string. ch is always a single character; comparison is
        case-sensitive.

            def char_counter(text: str, ch: str) -> int:

        Examples:
            char_counter("hello", "l")        -> 2
            char_counter("Hello World", "o")  -> 2
            char_counter("", "a")              -> 0
        """),
        "cases": [
            ["hello", "l"], ["", "a"], ["aaaa", "a"], ["aaaa", "b"],
            ["Hello World", "o"], ["Hello World", "l"],
            ["mississippi", "s"], ["   ", " "], ["abcabc", "z"],
            ["112233", "1"],
        ],
    },

    # ── LEVEL 2 ────────────────────────────────────────────────
    "py_echo_validator": {
        "level": 2, "function": "echo_validator", "standard": True,
        "oracle": _ref_echo_validator, "fuzz": _fuzz_echo_validator,
        "hint": ("If filtering out non-alphabetic characters leaves "
                "nothing (e.g. for '42' or '!!!'), what's left is an "
                "empty string — and an empty string is symmetric to "
                "itself, so it would wrongly pass as a palindrome. "
                "Check that case explicitly."),
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
        "level": 2, "function": "mirror_matrix", "standard": True,
        "oracle": _ref_mirror_matrix, "fuzz": _fuzz_mirror_matrix,
        "hint": ("It's each individual row that gets reversed, not the "
                "order of the rows themselves. Build a brand new list "
                "of lists rather than reversing rows in place (e.g. "
                "with row.reverse()), and check that an empty matrix "
                "and rows of length 0 don't blow up."),
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

    "py_digit_extractor": {
        "level": 2, "function": "digit_extractor",
        "oracle": _ref_digit_extractor, "fuzz": _fuzz_digit_extractor,
        "hint": ("Convert each digit character to an actual int in "
                "your result, not just keep it as a one-character "
                "string — digit_extractor needs a list of ints, not "
                "strings. Preserve extraction order left to right, and "
                "an input with no digits at all returns an empty list."),
        "subject": _sub("py_digit_extractor", """
        Write a function that extracts every digit character from a string,
        in order, and returns them as a list of integers. Non-digit
        characters are skipped.

            def digit_extractor(text: str) -> list[int]:

        Examples:
            digit_extractor("a1b22c3")  -> [1, 2, 2, 3]
            digit_extractor("nothing")  -> []
            digit_extractor("")         -> []
        """),
        "cases": [
            ["a1b22c3"], ["nothing here"], ["12345"], [""],
            ["1a2b3c4d5e"], ["   42   "], ["v1.2.3"], ["0"],
            ["a0b0c0"], ["999x888"],
        ],
    },
    "py_case_counter": {
        "level": 2, "function": "case_counter",
        "oracle": _ref_case_counter, "fuzz": _fuzz_case_counter,
        "hint": ("The return order is [uppercase_count, "
                "lowercase_count] — double check you're not swapping "
                "them. Use str.isupper()/str.islower() rather than "
                "hand-rolled 'A'-'Z' range checks, so digits, spaces "
                "and punctuation correctly count as neither."),
        "subject": _sub("py_case_counter", """
        Write a function that counts upper-case and lower-case letters in a
        string. Digits, spaces and punctuation count as neither.

            def case_counter(text: str) -> list[int]:

        Returns a list [uppercase_count, lowercase_count].

        Examples:
            case_counter("Hello World")  -> [2, 8]
            case_counter("ALLCAPS")      -> [7, 0]
            case_counter("123!?")        -> [0, 0]
        """),
        "cases": [
            ["Hello World"], [""], ["ALLCAPS"], ["alllower"], ["123456"],
            ["MiXeD cAsE"], ["   "], ["A"], ["a"], ["AbCdEfG"],
        ],
    },

    "py_run_length_encoder": {
        "level": 2, "function": "run_length_encoder",
        "oracle": _ref_run_length_encoder, "fuzz": _fuzz_run_length_encoder,
        "hint": ("Always emit the count even when a run is exactly 1 "
                "character long — some RLE variants omit a lone '1', "
                "but here 'abc' must become 'a1b1c1', not 'abc'. Handle "
                "the empty string as a special case up front, since "
                "there's no first character to start a run with."),
        "subject": _sub("py_run_length_encoder", """
        Write a function that run-length-encodes a string: each maximal
        run of the same character becomes that character followed by its
        count. An empty string encodes to "".

            def run_length_encoder(text: str) -> str:

        Examples:
            run_length_encoder("aaabbc")  -> "a3b2c1"
            run_length_encoder("abc")     -> "a1b1c1"
            run_length_encoder("")        -> ""
        """),
        "cases": [
            ["aaabbc"], [""], ["a"], ["aaaa"], ["abcabc"], ["aabbaabb"],
            ["x"], ["aaaaaaaaaa"], ["ab"], ["aabbbcccc"],
        ],
    },
    "py_second_largest": {
        "level": 2, "function": "second_largest",
        "oracle": _ref_second_largest, "fuzz": _fuzz_second_largest,
        "hint": ("Dedupe before picking the second-largest value — if "
                "you just sort the raw list and take the second "
                "element, a duplicated maximum (e.g. [5, 5, 4]) will "
                "wrongly give you the max again instead of the real "
                "second-distinct value. Convert to a set first, and "
                "remember fewer than two distinct values means None."),
        "subject": _sub("py_second_largest", """
        Write a function that returns the second-largest DISTINCT value in
        a list of integers. Duplicates of the largest value do not count
        as a second value. If there are fewer than two distinct values,
        return None.

            def second_largest(lst: list[int]) -> int | None:

        Examples:
            second_largest([3,1,4,1,5,9,2,6]) -> 5
            second_largest([1,1,1])           -> None
            second_largest([])                -> None
        """),
        "cases": [
            [[3, 1, 4, 1, 5, 9, 2, 6]], [[1, 1, 1]], [[]], [[5]], [[5, 5]],
            [[1, 2]], [[2, 1]], [[-1, -2, -3]], [[0, 0, 0, 1]],
            [[10, 10, 9, 9, 8]],
        ],
    },

    "py_even_odd_counter": {
        "level": 2, "function": "even_odd_counter",
        "oracle": _ref_even_odd_counter, "fuzz": _fuzz_even_odd_counter,
        "hint": ("Zero counts as even, and Python's % already handles "
                "negative numbers correctly for this check (-3 % 2 == "
                "1, no need for abs()) — just make sure the return "
                "order is [even_count, odd_count], and an empty list "
                "gives [0, 0]."),
        "subject": _sub("py_even_odd_counter", """
        Write a function that counts how many even and how many odd
        numbers are in a list of integers.

            def even_odd_counter(lst: list[int]) -> list[int]:

        Returns a list [even_count, odd_count].

        Examples:
            even_odd_counter([1,2,3,4,5]) -> [2, 3]
            even_odd_counter([])          -> [0, 0]
            even_odd_counter([-4,-2,0])   -> [3, 0]
        """),
        "cases": [
            [[1, 2, 3, 4, 5]], [[]], [[2, 4, 6]], [[1, 3, 5]], [[0]],
            [[-1, -2, -3]], [[-4, -2, 0, 2, 4]], [[7]], [[100, 101]],
            [[0, 0, 0, 1, 1, 1]],
        ],
    },
    "py_sum_of_squares": {
        "level": 2, "function": "sum_of_squares",
        "oracle": _ref_sum_of_squares, "fuzz": _fuzz_sum_of_squares,
        "hint": ("Square each number individually and then add the "
                "squares together — don't sum the list first and "
                "square that total once, e.g. summing [10, -10] first "
                "would give 0**2 = 0, which is wrong; the two squares "
                "(100 + 100) must be added separately."),
        "subject": _sub("py_sum_of_squares", """
        Write a function that returns the sum of the squares of every
        number in a list. An empty list returns 0.

            def sum_of_squares(lst: list[int]) -> int:

        Examples:
            sum_of_squares([1,2,3]) -> 14
            sum_of_squares([])      -> 0
            sum_of_squares([-3])    -> 9
        """),
        "cases": [
            [[1, 2, 3]], [[]], [[0]], [[-1, -2, -3]], [[5]], [[1, 1, 1, 1]],
            [[10, -10]], [[0, 0, 0]], [[3, 4]], [[2, 2, 2, 2, 2]],
        ],
    },
    "py_longest_common_prefix": {
        "level": 2, "function": "longest_common_prefix",
        "oracle": _ref_longest_common_prefix, "fuzz": _fuzz_longest_common_prefix,
        "hint": ("Start by assuming the whole first string is the "
                "prefix, then shrink it one character at a time until "
                "every other string starts with it (str.startswith is "
                "handy here) — that naturally handles the empty-list "
                "and 'one string is shorter/empty' cases as soon as the "
                "prefix shrinks to \"\". Comparison is case-sensitive: "
                "\"ABC\" and \"abc\" share no prefix at all."),
        "subject": _sub("py_longest_common_prefix", """
        Write a function that returns the longest string that is a prefix
        of every string in a list. An empty list, or no common prefix at
        all, returns "". Case-sensitive.

            def longest_common_prefix(strings: list[str]) -> str:

        Examples:
            longest_common_prefix(["flower","flow","flight"]) -> "fl"
            longest_common_prefix(["dog","racecar","car"])    -> ""
            longest_common_prefix([])                          -> ""
        """),
        "cases": [
            [["flower", "flow", "flight"]], [["dog", "racecar", "car"]],
            [[]], [[""]], [["a"]], [["abc", "abc", "abc"]],
            [["", "abc"]], [["abc", ""]], [["ABC", "abc"]],
            [["interspecies", "interstellar", "interstate"]],
            [["a", "ab", "abc"]], [["abc", "ab"]],
        ],
    },
    "py_camel_to_snake_converter": {
        "level": 2, "function": "camel_to_snake_converter",
        "oracle": _ref_camel_to_snake_converter,
        "fuzz": _fuzz_camel_to_snake_converter,
        "hint": ("A leading upper-case letter still gets an underscore "
                "in front of it — don't special-case away a leading "
                "underscore the way some snake_case libraries do; "
                "\"AlreadyUpper\" really does become \"_already_upper\". "
                "Digits and any underscore already in the input pass "
                "through unchanged."),
        "subject": _sub("py_camel_to_snake_converter", """
        Write a function that converts a lowerCamelCase string to
        snake_case: every upper-case letter is replaced by an underscore
        followed by its lower-case form. Every other character (including
        digits and any underscore already in the string) is left exactly
        as it is — even a leading upper-case letter just produces a
        leading underscore.

            def camel_to_snake_converter(text: str) -> str:

        Examples:
            camel_to_snake_converter("helloWorld")   -> "hello_world"
            camel_to_snake_converter("thisIsATest")  -> "this_is_a_test"
            camel_to_snake_converter("single")       -> "single"
        """),
        "cases": [
            ["helloWorld"], ["thisIsATest"], ["single"], [""],
            ["AlreadyUpper"], ["a1B2c3D4"], ["ALLCAPS"], ["a"], ["A"],
            ["already_snake"], ["mixOf_bothStyles"],
        ],
    },

    # ── LEVEL 3 ────────────────────────────────────────────────
    "py_number_base_converter": {
        "level": 3, "function": "number_base_converter", "standard": True,
        "oracle": _ref_number_base_converter, "fuzz": _fuzz_number_base_converter,
        "hint": ("\"ERROR\" covers three separate things — check them "
                "all: a base outside 2..36, an empty digit body "
                "(including a lone '-' with nothing after it), and any "
                "digit character that isn't valid in from_base (e.g. "
                "'2' in base 2, or a letter whose value is >= "
                "from_base). Also compute the decimal value first and "
                "check whether it's zero BEFORE reattaching the '-' "
                "sign — \"-0\" as input must come back as \"0\", not "
                "\"-0\"."),
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
        "level": 3, "function": "pattern_tracker", "standard": True,
        "oracle": _ref_pattern_tracker, "fuzz": _fuzz_pattern_tracker,
        "hint": ("This does NOT wrap around — '9' followed by '0' is "
                "not a valid pair even though 9 + 1 mod 10 == 0, so "
                "don't build the check with modular arithmetic. Also "
                "make sure both characters in a pair are digits before "
                "comparing their values, rather than assuming the "
                "whole string is numeric."),
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
        "level": 3, "function": "hidenp", "standard": True,
        "oracle": _ref_hidenp, "fuzz": _fuzz_hidenp,
        "hint": ("Membership alone isn't enough — just checking that "
                "every character of 'small' exists somewhere in 'big' "
                "would wrongly accept hidenp('aec', 'abcde'), which "
                "must be False because the order doesn't match. Walk "
                "through 'big' with a pointer that only ever moves "
                "forward, advancing it past each character of 'small' "
                "in turn."),
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

    "py_word_reverser": {
        "level": 3, "function": "word_reverser",
        "oracle": _ref_word_reverser, "fuzz": _fuzz_word_reverser,
        "hint": ("Split on \" \" specifically, not a bare .split() — a "
                "bare split collapses consecutive spaces and drops the "
                "empty 'words' they create, which this exercise expects "
                "you to keep (an empty word reversed is still empty). "
                "Reverse each piece independently, then rejoin with "
                "single spaces."),
        "subject": _sub("py_word_reverser", """
        Write a function that reverses each word in a sentence but keeps
        the words in their original order. Words are separated by single
        spaces; runs of several spaces produce empty words that stay empty.

            def word_reverser(text: str) -> str:

        Examples:
            word_reverser("hello world")  -> "olleh dlrow"
            word_reverser("Python Exam")  -> "nohtyP maxE"
            word_reverser("")             -> ""
        """),
        "cases": [
            ["hello world"], [""], ["a"], ["  "], ["one  two   three"],
            ["Python Exam"], [" leading"], ["trailing "],
            ["madam racecar"], ["x y z"],
        ],
    },

    "py_run_length_decoder": {
        "level": 3, "function": "run_length_decoder",
        "oracle": _ref_run_length_decoder, "fuzz": _fuzz_run_length_decoder,
        "hint": ("Counts can be more than one digit long — after each "
                "character, keep consuming digit characters greedily "
                "(a while loop, not just peeking at one) until you hit "
                "a non-digit or the end of the string; 'z10' means ten "
                "z's, not 'z1' followed by a stray '0'."),
        "subject": _sub("py_run_length_decoder", """
        Write a function that decodes a run-length-encoded string: each
        character is followed by a run of digits giving its repeat count
        (the count can be more than one digit long).

            def run_length_decoder(text: str) -> str:

        Examples:
            run_length_decoder("a3b2c1")  -> "aaabbc"
            run_length_decoder("z10")     -> "zzzzzzzzzz"
            run_length_decoder("")        -> ""
        """),
        "cases": [
            ["a3b2c1"], [""], ["a1"], ["z10"], ["a2b2c2"], ["x5"],
            ["a1b1c1d1"], ["m12"], ["a9a9"], ["b100"],
        ],
    },
    "py_binary_gap": {
        "level": 3, "function": "binary_gap",
        "oracle": _ref_binary_gap, "fuzz": _fuzz_binary_gap,
        "hint": ("Only zeros with a 1 on BOTH sides count — zeros "
                "trailing after the last 1 bit (like in 32 -> 100000) "
                "must be ignored even though they're the longest run of "
                "zeros in the binary string. bin(n)[2:] plus splitting "
                "on '1' isolates each internal run cleanly, but drop "
                "the first and last piece of that split — those sit "
                "before the first 1 and after the last 1, not between "
                "two of them."),
        "subject": _sub("py_binary_gap", """
        Write a function that finds the longest run of consecutive zeros
        that is surrounded by ones on both sides in the binary
        representation of a non-negative integer n. Trailing zeros (with
        no closing 1) do not count.

            def binary_gap(n: int) -> int:

        Examples:
            binary_gap(9)   -> 2   # 1001
            binary_gap(529) -> 4   # 1000010001
            binary_gap(20)  -> 1   # 10100
            binary_gap(32)  -> 0   # 100000 (trailing zeros don't count)
        """),
        "cases": [
            [9], [529], [20], [15], [0], [1], [32], [1041], [7],
            [1000000], [2], [16],
        ],
    },
    "py_string_rotation_checker": {
        "level": 3, "function": "string_rotation_checker",
        "oracle": _ref_string_rotation_checker,
        "fuzz": _fuzz_string_rotation_checker,
        "hint": ("Check that s1 and s2 have the same length FIRST — "
                "the classic 's2 in (s1 + s1)' trick only works once "
                "you already know the lengths match. Skip that check "
                "and a shorter string like 'ab' would look like it's "
                "'inside' the doubled longer string and wrongly pass as "
                "a rotation of 'abc'."),
        "subject": _sub("py_string_rotation_checker", """
        Write a function that checks whether s2 is a rotation of s1 — i.e.
        s2 can be obtained by moving some prefix of s1 to its end (zero
        rotation, s2 == s1, counts too). Case-sensitive; two strings of
        different lengths are never rotations of each other.

            def string_rotation_checker(s1: str, s2: str) -> bool:

        Examples:
            string_rotation_checker("waterbottle", "erbottlewat") -> True
            string_rotation_checker("abcd", "abdc")                -> False
            string_rotation_checker("", "")                        -> True
        """),
        "cases": [
            ["waterbottle", "erbottlewat"], ["abcd", "abdc"],
            ["abcd", "abcd"], ["abcd", "dabc"], ["", ""], ["a", ""],
            ["", "a"], ["aa", "aa"], ["ab", "ba"],
            ["abcde", "cdeab"], ["abcde", "cdaeb"], ["abc", "ab"],
            ["aaab", "abaa"],
        ],
    },

    # ── LEVEL 4 ────────────────────────────────────────────────
    "py_anagram": {
        "level": 4, "function": "anagram", "standard": True,
        "oracle": _ref_anagram, "fuzz": _fuzz_anagram,
        "hint": ("Don't compare using set() — a set collapses "
                "duplicate letters, so 'abc' and 'abcc' would "
                "incorrectly look equal even though the counts differ "
                "(this exercise tests exactly that case). Sort each "
                "cleaned string, or count letters with a dict/Counter, "
                "so multiplicities are preserved; lowercase and strip "
                "spaces from both first."),
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
        "level": 4, "function": "shadow_merge", "standard": True,
        "oracle": _ref_shadow_merge, "fuzz": _fuzz_shadow_merge,
        "hint": ("If you're doing a manual two-pointer merge (rather "
                "than just concatenating and sorting), remember to "
                "append whatever's left over in the other list once one "
                "pointer runs off the end — a common bug is stopping as "
                "soon as either list is exhausted and silently dropping "
                "the remaining tail of the other one."),
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
        "level": 4, "function": "string_permutation_checker", "standard": True,
        "oracle": _ref_string_permutation_checker,
        "fuzz": _fuzz_string_permutation_checker,
        "hint": ("Unlike a typical anagram check, this one is fully "
                "case-sensitive — don't lowercase the strings first, "
                "'Abc' and 'abc' must NOT count as permutations of each "
                "other. Otherwise it's the same idea: compare sorted "
                "character sequences (or counts) rather than sets, so "
                "repeated characters are handled correctly too."),
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

    "py_unique_elements": {
        "level": 4, "function": "unique_elements",
        "oracle": _ref_unique_elements, "fuzz": _fuzz_unique_elements,
        "hint": ("This is not the same as deduping a list — an item "
                "that appears more than once must be dropped entirely, "
                "including its first occurrence, not just its later "
                "repeats (unique_elements([1,2,2,3,4,4,5]) is [1, 3, "
                "5], not [1, 2, 3, 4, 5]). Count occurrences first, "
                "then filter the original list keeping only items "
                "whose total count is exactly 1."),
        "subject": _sub("py_unique_elements", """
        Write a function that returns the elements that appear exactly once
        in a list, in their original order. Elements that repeat are
        dropped entirely, including their first occurrence.

            def unique_elements(lst: list[int]) -> list[int]:

        Examples:
            unique_elements([1,2,2,3,4,4,5]) -> [1, 3, 5]
            unique_elements([1,1,1])         -> []
            unique_elements([])              -> []
        """),
        "cases": [
            [[1, 2, 2, 3, 4, 4, 5]], [[]], [[1]], [[1, 1, 1]], [[1, 2, 3]],
            [[5, 5, 5, 5]], [[-1, -1, 2, 3, -1]], [[0, 0, 0, 1]],
            [[9, 8, 7, 9, 8, 7]], [[1, 2, 3, 4, 5, 6, 7]],
        ],
    },

    "py_pangram_checker": {
        "level": 4, "function": "pangram_checker",
        "oracle": _ref_pangram_checker, "fuzz": _fuzz_pangram_checker,
        "hint": ("Filter down to alphabetic characters before counting "
                "distinct letters (ch.isalpha()) — otherwise digits, "
                "spaces and punctuation inflate the count of unique "
                "symbols, and a genuine pangram like 'The 5 boxing "
                "wizards jump quickly!' could fail the ==26 check even "
                "though every letter is actually present."),
        "subject": _sub("py_pangram_checker", """
        Write a function that checks whether a string is a pangram: it
        must contain every letter of the alphabet at least once,
        case-insensitively. Non-letter characters are ignored.

            def pangram_checker(text: str) -> bool:

        Examples:
            pangram_checker("The quick brown fox jumps over the lazy dog") -> True
            pangram_checker("hello world")                                -> False
            pangram_checker("")                                           -> False
        """),
        "cases": [
            ["The quick brown fox jumps over the lazy dog"], [""],
            ["abc"], ["abcdefghijklmnopqrstuvwxy"],
            ["ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
            ["Pack my box with five dozen liquor jugs"], ["   "],
            ["aaaaaaaaaaaaaaaaaaaaaaaaaa"],
            ["The 5 boxing wizards jump quickly!"], ["hello world"],
        ],
    },
    "py_max_subarray_sum": {
        "level": 4, "function": "max_subarray_sum",
        "oracle": _ref_max_subarray_sum, "fuzz": _fuzz_max_subarray_sum,
        "hint": ("Initialize your running/best sums to the first "
                "element, not 0 — starting from 0 breaks the "
                "all-negative case (max_subarray_sum([-1,-2,-3]) must "
                "be -1, the largest single element, since 0 isn't a "
                "sum any contiguous non-empty subarray can actually "
                "produce there)."),
        "subject": _sub("py_max_subarray_sum", """
        Write a function that returns the largest possible sum of a
        contiguous (non-empty) subarray of a list of integers. If every
        number is negative, return the largest single number. An empty
        list returns 0.

            def max_subarray_sum(lst: list[int]) -> int:

        Examples:
            max_subarray_sum([-2,1,-3,4,-1,2,1,-5,4]) -> 6   # [4,-1,2,1]
            max_subarray_sum([-1,-2,-3])               -> -1
            max_subarray_sum([])                        -> 0
        """),
        "cases": [
            [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], [[]], [[5]], [[-5]],
            [[-1, -2, -3]], [[1, 2, 3, 4]], [[0, 0, 0]], [[-2, -1]],
            [[3, -2, 5, -1]], [[10, -1, 10]],
        ],
    },
    "py_roman_numeral": {
        "level": 4, "function": "roman_numeral",
        "oracle": _ref_roman_numeral, "fuzz": _fuzz_roman_numeral,
        "hint": ("Don't build this with just the seven base symbols "
                "(I, V, X, L, C, D, M) — you also need the six "
                "subtractive combinations (CM=900, CD=400, XC=90, "
                "XL=40, IX=9, IV=4), or numbers like 1994 (which needs "
                "CM, XC and IV all in the same result) will come out "
                "wrong. A greedy loop over a value/symbol table ordered "
                "largest-to-smallest, including those combos, handles "
                "every case in one pass."),
        "subject": _sub("py_roman_numeral", """
        Write a function that converts an integer (always between 1 and
        3999 inclusive) to its Roman numeral representation.

            def roman_numeral(n: int) -> str:

        Examples:
            roman_numeral(3)    -> "III"
            roman_numeral(58)   -> "LVIII"
            roman_numeral(1994) -> "MCMXCIV"
        """),
        "cases": [
            [1], [3], [4], [9], [40], [44], [49], [58], [90], [400],
            [900], [1994], [3999], [2024], [500], [1000], [3000], [8],
        ],
    },

    # ── LEVEL 5 ────────────────────────────────────────────────
    "py_string_sculptor": {
        "level": 5, "function": "string_sculptor", "standard": True,
        "oracle": _ref_string_sculptor, "fuzz": _fuzz_string_sculptor,
        "hint": ("Two different things happen for non-letters: "
                "whitespace (space/tab/newline) resets the alternation "
                "back to lowercase-next, but other non-alpha characters "
                "(digits, punctuation) are simply skipped — they "
                "neither toggle the case nor reset it, the toggle just "
                "continues across them (e.g. 'abc123def' -> "
                "'aBc123DeF', the 'd' continues the toggle state from "
                "before the digits)."),
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
        "level": 5, "function": "twist_sequence", "standard": True,
        "oracle": _ref_twist_sequence, "fuzz": _fuzz_twist_sequence,
        "hint": ("Handle the empty list first, before you do "
                "k %= len(arr) — computing that modulo when the array "
                "is empty divides by zero and crashes. Also don't skip "
                "the modulo step itself: k can be larger than (or a "
                "multiple of) the array's length, so reduce it first, "
                "and return a brand new list rather than rotating arr "
                "in place."),
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

    "py_matrix_transposer": {
        "level": 5, "function": "matrix_transposer",
        "oracle": _ref_matrix_transposer, "fuzz": _fuzz_matrix_transposer,
        "hint": ("If you use zip(*matrix) to transpose (a clean "
                "built-in trick), remember zip returns tuples — wrap "
                "each resulting row in list(...), since the expected "
                "output is a list of lists, not tuples. Also handle the "
                "empty-matrix case explicitly ([] -> [])."),
        "subject": _sub("py_matrix_transposer", """
        Write a function that transposes a matrix (rows become columns).
        The matrix is rectangular: every row has the same length.

            def matrix_transposer(matrix: list[list[int]]) -> list[list[int]]:

        Examples:
            matrix_transposer([[1,2,3],[4,5,6]]) -> [[1,4],[2,5],[3,6]]
            matrix_transposer([[7]])             -> [[7]]
            matrix_transposer([])                -> []
        """),
        "cases": [
            [[[1, 2, 3], [4, 5, 6]]], [[[1], [2], [3]]], [[[1, 2], [3, 4]]],
            [[[7]]], [[]], [[[1, 2, 3, 4, 5]]], [[[1], [2]]],
            [[[-1, -2], [-3, -4]]], [[[0, 0], [0, 0]]],
            [[[1, 2], [3, 4], [5, 6]]],
        ],
    },
    "py_longest_word": {
        "level": 5, "function": "longest_word",
        "oracle": _ref_longest_word, "fuzz": _fuzz_longest_word,
        "hint": ("When several words are tied for longest, keep the "
                "FIRST one you saw — use strict '>' (not '>=') when "
                "comparing a new candidate against your current best, "
                "otherwise a later tied word overwrites the correct "
                "answer (longest_word('aaa bbb ccc') must stay 'aaa', "
                "not 'ccc')."),
        "subject": _sub("py_longest_word", """
        Write a function that returns the longest word in a sentence.
        Words are separated by (possibly several) spaces; if two words are
        tied for longest, return the first one. An empty string, or one
        with no words at all, returns "".

            def longest_word(text: str) -> str:

        Examples:
            longest_word("the quick brown fox") -> "quick"
            longest_word("aaa bbb ccc")          -> "aaa"
            longest_word("")                     -> ""
        """),
        "cases": [
            ["the quick brown fox"], [""], ["a"], ["equal ab cd"],
            ["   "], ["one"], ["aaa bbb ccc"], ["Python is fun"],
            ["   spaced   out   "], ["x yy zzz wwww"],
        ],
    },

    "py_zigzag_flatten": {
        "level": 5, "function": "zigzag_flatten",
        "oracle": _ref_zigzag_flatten, "fuzz": _fuzz_zigzag_flatten,
        "hint": ("It's individual rows that get reversed on every "
                "other pass, not the overall flattened list — row 0 "
                "goes left-to-right, row 1 right-to-left, row 2 "
                "left-to-right again, and so on. Use the row's own "
                "0-based index to decide direction, not a separate "
                "running counter that could drift out of sync."),
        "subject": _sub("py_zigzag_flatten", """
        Write a function that flattens a matrix into a single list in a
        zigzag (boustrophedon) order: the first row left-to-right, the
        second row right-to-left, the third left-to-right again, and so on.

            def zigzag_flatten(matrix: list[list[int]]) -> list[int]:

        Examples:
            zigzag_flatten([[1,2,3],[4,5,6],[7,8,9]]) -> [1,2,3,6,5,4,7,8,9]
            zigzag_flatten([[1,2],[3,4]])              -> [1,2,4,3]
            zigzag_flatten([])                         -> []
        """),
        "cases": [
            [[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], [[]], [[[1]]],
            [[[1, 2], [3, 4]]], [[[1, 2, 3]]], [[[1], [2], [3]]],
            [[[1, 2, 3], [4, 5]]], [[[0, 0], [0, 0], [0, 0]]],
            [[[5, 4, 3], [2, 1, 0], [9, 8, 7]]],
            [[[1, 2], [3, 4], [5, 6], [7, 8]]],
        ],
    },
    "py_pascals_triangle_row": {
        "level": 5, "function": "pascals_triangle_row",
        "oracle": _ref_pascals_triangle_row, "fuzz": _fuzz_pascals_triangle_row,
        "hint": ("Row 0 is the special case [1] — check whether your "
                "general build-up logic even runs once for n=0, or "
                "whether you need to handle it separately."),
        "subject": _sub("py_pascals_triangle_row", """
        Write a function that returns row n (0-indexed) of Pascal's
        triangle, where row 0 is [1] and every other row starts and ends
        with 1, with each inner value the sum of the two values above it.

            def pascals_triangle_row(n: int) -> list[int]:

        Examples:
            pascals_triangle_row(0) -> [1]
            pascals_triangle_row(3) -> [1, 3, 3, 1]
            pascals_triangle_row(4) -> [1, 4, 6, 4, 1]
        """),
        "cases": [
            [0], [1], [2], [3], [4], [5], [10], [15], [6], [7],
        ],
    },

    # ── LEVEL 6 ────────────────────────────────────────────────
    "py_bracket_validator": {
        "level": 6, "function": "bracket_validator", "standard": True,
        "oracle": _ref_bracket_validator, "fuzz": _fuzz_bracket_validator,
        "hint": ("Two failure modes to catch, not just one: a closing "
                "bracket that doesn't match what's on top of your stack "
                "(or with nothing on the stack at all, like '}{'), AND "
                "leftover unmatched opening brackets once you've "
                "scanned the whole string (like '((())' — three opens, "
                "two closes). Don't forget to check the stack is "
                "completely empty at the end, not just that you never "
                "hit a mismatch during the loop."),
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
        "level": 6, "function": "whisper_cipher", "standard": True,
        "oracle": _ref_whisper_cipher, "fuzz": _fuzz_whisper_cipher,
        "hint": ("Python's % already wraps negative shifts correctly "
                "(no need for an extra +26 correction like you might "
                "add in other languages) — the real trap is keeping "
                "the two alphabets separate: subtract the right base "
                "(97 for lowercase, 65 for uppercase) before applying "
                "the shift and modulo, or you'll break the case of the "
                "output while wrapping it."),
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
    "py_matrix_rotator": {
        "level": 6, "function": "matrix_rotator",
        "oracle": _ref_matrix_rotator, "fuzz": _fuzz_matrix_rotator,
        "hint": ("The matrix is rectangular, not necessarily square — "
                "an RxC matrix becomes CxR, so your row/column loop "
                "bounds need to swap, not stay the same. And handle the "
                "empty matrix ([]) separately before touching the first "
                "row."),
        "subject": _sub("py_matrix_rotator", """
        Write a function that rotates a matrix 90 degrees clockwise. The
        matrix is rectangular; the result may have different dimensions
        than the input (an RxC matrix rotates into a CxR one).

            def matrix_rotator(matrix: list[list[int]]) -> list[list[int]]:

        Examples:
            matrix_rotator([[1,2],[3,4]])     -> [[3,1],[4,2]]
            matrix_rotator([[1,2,3],[4,5,6]]) -> [[4,1],[5,2],[6,3]]
            matrix_rotator([])                -> []
        """),
        "cases": [
            [[[1, 2], [3, 4]]], [[[1, 2, 3], [4, 5, 6]]], [[[7]]], [[]],
            [[[1], [2], [3]]], [[[1, 2, 3, 4]]],
            [[[1, 2], [3, 4], [5, 6]]], [[[-1, -2], [-3, -4]]], [[[0]]],
            [[[1, 2], [3, 4], [5, 6], [7, 8]]],
        ],
    },
    "py_prime_finder": {
        "level": 6, "function": "prime_finder",
        "oracle": _ref_prime_finder, "fuzz": _fuzz_prime_finder,
        "hint": ("Think about the edge cases first: 0, 1 and negative "
                "numbers are never prime — if it's only wrong for small "
                "n, that's almost always it."),
        "subject": _sub("py_prime_finder", """
        Write a function that checks whether an integer is prime. Numbers
        less than 2 (0, 1, and every negative number) are not prime.

            def prime_finder(n: int) -> bool:

        Examples:
            prime_finder(2)   -> True
            prime_finder(17)  -> True
            prime_finder(1)   -> False
            prime_finder(100) -> False
        """),
        "cases": [
            [2], [3], [4], [1], [0], [-7], [17], [97], [100], [561],
            [104729], [999999937], [999999999],
        ],
    },
    "py_longest_palindromic_substring": {
        "level": 6, "function": "longest_palindromic_substring",
        "oracle": _ref_longest_palindromic_substring,
        "fuzz": _fuzz_longest_palindromic_substring,
        "hint": ("Expanding around a center only catches odd-length "
                "palindromes (a single middle character) unless you "
                "also try each adjacent PAIR as a center for "
                "even-length ones — 'cbbd' -> 'bb' needs that second "
                "kind of center, or you'd miss it entirely. When "
                "several substrings tie for the longest length, keep "
                "the first (leftmost) one — use strict '>' when "
                "updating your best-so-far, not '>='."),
        "subject": _sub("py_longest_palindromic_substring", """
        Write a function that returns the longest contiguous substring
        that reads the same forwards and backwards. Comparison is
        case-sensitive. If several substrings share the maximum length,
        return the one that starts first. An empty string returns "".

            def longest_palindromic_substring(text: str) -> str:

        Examples:
            longest_palindromic_substring("babad")     -> "bab"
            longest_palindromic_substring("cbbd")      -> "bb"
            longest_palindromic_substring("racecar")   -> "racecar"
            longest_palindromic_substring("")          -> ""
        """),
        "cases": [
            ["babad"], ["cbbd"], [""], ["a"], ["ac"], ["racecar"],
            ["abba"], ["abbazcddc"], ["noon"], ["aaaa"], ["xy"],
        ],
    },
    "py_two_sum_indices": {
        "level": 6, "function": "two_sum_indices",
        "oracle": _ref_two_sum_indices, "fuzz": _fuzz_two_sum_indices,
        "hint": ("i and j must be different indices (not the same "
                "element twice) — and the scan order matters: i "
                "ascending, then j ascending."),
        "subject": _sub("py_two_sum_indices", """
        Write a function that finds two DIFFERENT elements of a list that
        add up to target and returns their indices [i, j] with i < j. If
        several pairs work, return the one found first while scanning i
        ascending, then j ascending. If no pair works, return [].

            def two_sum_indices(lst: list[int], target: int) -> list[int]:

        Examples:
            two_sum_indices([2,7,11,15], 9) -> [0, 1]
            two_sum_indices([3,2,4], 6)     -> [1, 2]
            two_sum_indices([1,2,3], 100)   -> []
        """),
        "cases": [
            [[2, 7, 11, 15], 9], [[3, 2, 4], 6], [[3, 3], 6],
            [[1, 2, 3], 100], [[], 5], [[5], 5], [[0, 0, 0], 0],
            [[-3, 4, 3, 90], 0], [[1, 1, 1, 1], 2], [[5, -5, 5, -5], 0],
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
    _ex.setdefault("standard", False)

for _lvl, _pool in LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank: level %d has no exercise" % _lvl)

# The 14 exercises verified against publicly documented Rank-03 subjects
# (see README) — `make exam` draws only from this pool, so a real exam run
# only ever contains exercises confirmed to plausibly appear on the actual
# 42 exam. The other 26 ("Extra") stay reachable through practice/training
# mode for open-ended drilling, just never during a real exam emulation.
STANDARD_LEVELS = {lvl: [name for name in pool if EXERCISES[name]["standard"]]
                   for lvl, pool in LEVELS.items()}

for _lvl, _pool in STANDARD_LEVELS.items():
    if not _pool:
        raise ValueError("exam_bank: level %d has no standard exercise" % _lvl)


def signature_of(name):
    """The `def …:` line of an exercise, as shown in its subject."""
    return _signature_of(EXERCISES[name]["subject"])