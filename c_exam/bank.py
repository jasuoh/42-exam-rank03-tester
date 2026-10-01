#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bank.py  ·  42 Common Core  ·  Exam Rank 02 (C)

Exercise bank for the C tester. Two exercise "kind"s (see c_exam/grader.py
for how each is graded):

  "function"  (the default) — student writes one function, subject gives
              its exact prototype, the tester supplies main() by
              generating a harness from `args`/`returns`/`cases`.
  "program"   — student writes a full program (their own main(), argv and
              all); graded by compiling their file standalone and running
              it once per case with that case's argv.

Every "standard" exercise here mirrors a real, publicly documented Exam
Rank 02 subject (names, prototypes and behaviour cross-checked against
several independent public exam-prep repositories) — the exact pool and
level placement still varies by campus/date. Same opt-IN convention as
the Python bank (see examshell/exam_bank.py's own docstring): every entry
marks itself "standard": True explicitly, and the index-building loop
below defaults an exercise with no such key to False (Extra) — so a new
exercise a contributor forgets to mark never silently becomes eligible
for a real `make c-exam` draw. A handful of exercises are marked
"standard": False ("Extra"): these are this project's own invented
additions for broader text-manipulation practice, not verified against
any real exam sheet, and `make c-exam` never draws them — only practice
mode does.

Common fields:
  - level      : which exam level it belongs to (1..N_LEVELS)
  - function   : the exact function name ("function" kind) or the program's
                 own name ("program" kind, used only for display/messages)
  - prototype  : shown in the subject; for "function" kind also becomes the
                 harness's `extern` declaration and the stub's definition
  - subject    : the full assignment text (shown to the student)
  - oracle_c   : verified reference implementation, a *complete*,
                 self-contained C source (its own #includes — compiled as
                 its own translation unit)
  - cases      : "function" kind: one tuple of values per test case,
                 lined up with `args` (a "cmp_ascending" arg consumes no
                 value — see grader._emit_args). "program" kind: one argv
                 list (NOT including argv[0]) per test case.
  - forbidden  (optional): libc calls banned for that exercise, flagged as
                 a warning (same default posture as the Python tool's
                 import detection)

"function"-kind only:
  - args             : ordered arg kinds — "int" / "char" / "str" /
                       "int_ptr" / "int_arr" / "int_list" / "buf" /
                       "cmp_ascending" (see c_exam/grader.py)
  - returns          : "void" / "int" / "str" / "str_owned" / "str_array" /
                       "int_list" / "strcmp_sign"
  - print_after_args (optional): for a "void"-returning, mutate-in-place
                       exercise, the indexes into `args` to print after the
                       call (int_arr -> the array, int_ptr -> the scalar)

  ⚠  This file contains the reference solutions (answer key). Do not peek
     if you actually want to practice!
"""

import textwrap

N_LEVELS = 4


def _sub_c(name, prototype, allowed, body):
    head = ("Assignment name  : " + name + "\n"
            "Expected files   : " + name + ".c\n"
            "Allowed functions: " + allowed + "\n"
            + "-" * 80 + "\n\n")
    text = textwrap.dedent(body).strip("\n") + "\n\n    " + prototype + "\n"
    return head + text


# ══════════════════════════════════════════════════════════════
#  EXERCISE BANK
# ══════════════════════════════════════════════════════════════
EXERCISES = {
    # ── LEVEL 1 ────────────────────────────────────────────────
    "ft_putstr": {
        "level": 1, "function": "ft_putstr",
        "standard": True,
        "prototype": "void ft_putstr(char *str);",
        "args": ["str"], "returns": "void",
        "hint": ("write() needs an explicit byte count — walk the string "
                "yourself to find its length (or write one character at a "
                "time inside the loop) instead of guessing a fixed size; "
                "an empty string should simply write zero bytes."),
        "subject": _sub_c("ft_putstr", "void ft_putstr(char *str);", "write", """
        Write a function that displays a string on the standard output.

        The pointer passed to the function contains the address of the
        string's first character.

        Examples:
            ft_putstr("hello") -> prints: hello
            ft_putstr("")      -> prints nothing
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        void ft_putstr(char *str)
        {
            int i;

            i = 0;
            while (str[i])
                i++;
            write(1, str, i);
        }
        """),
        "cases": [["hello"], [""], ["Hello, World!"], ["   "], ["42"], ["a"]],
    },
    "ft_swap": {
        "level": 1, "function": "ft_swap",
        "standard": True,
        "prototype": "void ft_swap(int *a, int *b);",
        "args": ["int_ptr", "int_ptr"], "returns": "void",
        "print_after_args": [0, 1],
        "hint": ("Swap the VALUES the two pointers point to (*a and *b), "
                "not the pointers themselves — and save the first one "
                "into a temporary variable before you overwrite it, or "
                "you'll lose it and end up with both holding the same "
                "value."),
        "subject": _sub_c("ft_swap", "void ft_swap(int *a, int *b);", "None", """
        Write a function that swaps the contents of two integers, the
        addresses of which are passed as parameters.

        Examples:
            ft_swap(&a, &b)  where a=5, b=10 -> a becomes 10, b becomes 5
        """),
        "oracle_c": textwrap.dedent("""
        void ft_swap(int *a, int *b)
        {
            int tmp;

            tmp = *a;
            *a = *b;
            *b = tmp;
        }
        """),
        "cases": [[5, 10], [-3, 7], [0, 0], [1, -1], [100, -100], [42, 42]],
    },
    "rotone": {
        "level": 1, "function": "rotone", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Both 'z' and 'Z' need to wrap back to the start of "
                "their own case instead of just doing c + 1, which would "
                "overshoot past 'z' into '{' or past 'Z' into '['."),
        "subject": _sub_c("rotone", "int main(int argc, char **argv);", "write", """
        Write a PROGRAM (your own main(), argc/argv — not a function
        someone else calls) that takes a string and displays it, replacing
        each of its letters by the next one in alphabetical order.

        'z' becomes 'a' and 'Z' becomes 'A'. Case remains unaffected. The
        output is followed by a newline. If the number of arguments is not
        exactly 1, the program displays just a newline.

        Examples:
            ./rotone "abc"  -> bcd
            ./rotone ""     -> (just a newline)
            ./rotone a b    -> (just a newline, 2 arguments)
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'a' && c <= 'z')
                    c = (c == 'z') ? 'a' : c + 1;
                else if (c >= 'A' && c <= 'Z')
                    c = (c == 'Z') ? 'A' : c + 1;
                write(1, &c, 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["Les stagiaires du staff ne sentent pas toujours tres bon."],
            ["AkjhZ zLKIJz , 23y "], [], [""], ["a", "b"],
        ],
    },
    "fizzbuzz": {
        "level": 1, "function": "fizzbuzz", "kind": "program",
        "standard": True,
        "hint": ("Check the 'multiple of both' case before (or instead "
                "of) the separate multiple-of-3 and multiple-of-5 checks "
                "— an if/elif chain that checks %3 then %5 will never "
                "print 'fizzbuzz' for a number like 15."),
        "subject": _sub_c("fizzbuzz", "int main(void);", "write", """
        Write a PROGRAM that prints the numbers from 1 to 100, each
        separated by a newline.

        If the number is a multiple of 3, print 'fizz' instead. If it's a
        multiple of 5, print 'buzz' instead. If it's a multiple of both,
        print 'fizzbuzz' instead. Takes no arguments.

        Examples:
            ./fizzbuzz -> 1\\n2\\nfizz\\n4\\nbuzz\\nfizz\\n7\\n8\\nfizz\\nbuzz\\n...
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static void put_nbr(int n)
        {
            char digit;

            if (n >= 10)
                put_nbr(n / 10);
            digit = '0' + n % 10;
            write(1, &digit, 1);
        }

        int main(void)
        {
            int i;

            i = 1;
            while (i <= 100)
            {
                if (i % 15 == 0)
                    write(1, "fizzbuzz\\n", 9);
                else if (i % 3 == 0)
                    write(1, "fizz\\n", 5);
                else if (i % 5 == 0)
                    write(1, "buzz\\n", 5);
                else
                {
                    put_nbr(i);
                    write(1, "\\n", 1);
                }
                i++;
            }
            return (0);
        }
        """),
        "cases": [[]],
    },
    "first_word": {
        "level": 1, "function": "first_word", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Skip any leading spaces/tabs before you start copying "
                "the word, and stop the moment you hit the next "
                "separator (or the end of the string) — a string of only "
                "whitespace has no first word, so the output is just a "
                "newline."),
        "subject": _sub_c("first_word", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays its first
        whitespace-delimited word, followed by a newline. A word is a run
        of characters between spaces/tabs (or the start/end of the
        string). If argc != 2, or there are no words, just a newline.

        Examples:
            ./first_word "hello world" -> hello
            ./first_word "   "          -> (just a newline)
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int i;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i] && is_sep(argv[1][i]))
                i++;
            while (argv[1][i] && !is_sep(argv[1][i]))
            {
                write(1, &argv[1][i], 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["hello world"], ["   leading spaces here"], ["   "], [],
            ["a", "b"], ["onlyword"],
        ],
    },
    "ft_strcpy": {
        "level": 1, "function": "ft_strcpy",
        "standard": True,
        "prototype": "char *ft_strcpy(char *s1, char *s2);",
        "args": ["buf", "str"], "returns": "str", "forbidden": ["strcpy"],
        "hint": ("The terminating null byte has to be copied too, not "
                "just the visible characters — and the function must "
                "return s1 itself, not whatever pointer you were using "
                "to walk through it."),
        "subject": _sub_c("ft_strcpy", "char *ft_strcpy(char *s1, char *s2);",
                         "None", """
        Reproduce the behaviour of the standard strcpy(): copy the string
        s2 (including its terminating null byte) into s1, and return s1.

        Examples:
            ft_strcpy(dest, "hello") -> dest becomes "hello", returns dest
        """),
        "oracle_c": textwrap.dedent("""
        char *ft_strcpy(char *s1, char *s2)
        {
            int i;

            i = 0;
            while (s2[i])
            {
                s1[i] = s2[i];
                i++;
            }
            s1[i] = '\\0';
            return (s1);
        }
        """),
        "cases": [
            ["", "hello"], ["", ""], ["", "a"], ["", "Testing 123"],
            ["", "x"],
        ],
    },
    "ft_strlen": {
        "level": 1, "function": "ft_strlen",
        "standard": True,
        "prototype": "int ft_strlen(char *str);",
        "args": ["str"], "returns": "int", "forbidden": ["strlen"],
        "hint": ("Your counter must stop at the terminating null byte "
                "without counting it — advance while the current "
                "character is non-zero rather than looping to a fixed "
                "bound, and check the empty string by hand: the loop "
                "body should never execute, so the answer is already 0."),
        "subject": _sub_c("ft_strlen", "int ft_strlen(char *str);", "None", """
        Write a function that returns the length of a string.

        Examples:
            ft_strlen("hello") -> 5
            ft_strlen("")      -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int ft_strlen(char *str)
        {
            int i;

            i = 0;
            while (str[i])
                i++;
            return (i);
        }
        """),
        "cases": [["hello"], [""], ["a"], ["Testing 123"], ["   "]],
    },
    "rev_print": {
        "level": 1, "function": "rev_print", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Find the string's length first, then walk backwards "
                "starting from the LAST character (index length - 1) "
                "down to 0 — starting the backward walk at `length` "
                "itself reads one byte past the string as your first "
                "output character."),
        "subject": _sub_c("rev_print", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays it reversed,
        followed by a newline. If argc != 2, just a newline.

        Examples:
            ./rev_print "abc"         -> cba
            ./rev_print "hello world" -> dlrow olleh
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
                i++;
            while (i > 0)
            {
                i--;
                write(1, &argv[1][i], 1);
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["hello world"], [""], [], ["a", "b"], ["racecar"],
        ],
    },
    "search_and_replace": {
        "level": 1, "function": "search_and_replace", "kind": "program",
        "fuzz_argv": "search_and_replace",
        "standard": True,
        "hint": ("Only the FIRST character of the search and replacement "
                "arguments matters, even if a longer string is passed "
                "for either one — and argc must be exactly 4 (program "
                "name, string, search-char, replace-char), not 3."),
        "subject": _sub_c("search_and_replace",
                         "int main(int argc, char **argv);", "write", """
        Write a PROGRAM called search_and_replace that takes 3 arguments:
        a string, a single character to search for, and a single
        character to replace it with. Every occurrence of the 2nd
        argument's first character in the string is replaced by the 3rd
        argument's first character; the result is displayed followed by a
        newline. If argc != 4, just a newline.

        Examples:
            ./search_and_replace "hello world" "o" "0" -> hell0 w0rld
            ./search_and_replace "banana" "a" "e"        -> benene
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            char from;
            char to;

            if (argc != 4)
            {
                write(1, "\\n", 1);
                return (0);
            }
            from = argv[2][0];
            to = argv[3][0];
            i = 0;
            while (argv[1][i])
            {
                if (argv[1][i] == from)
                    write(1, &to, 1);
                else
                    write(1, &argv[1][i], 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["hello world", "o", "0"], ["banana", "a", "e"],
            ["test", "z", "x"], ["abc", "b", "B"], [],
            ["a", "b", "c", "d"],
        ],
    },
    "ulstr": {
        "level": 1, "function": "ulstr", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Case-swap only actual letters — leave digits, spaces "
                "and punctuation untouched — and make sure your two "
                "range checks ('a'-'z' and 'A'-'Z') are mutually "
                "exclusive, or a character could get flipped back to its "
                "original case in the same pass."),
        "subject": _sub_c("ulstr", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and reverses the case of
        every letter (other characters unchanged), followed by a newline.
        If argc != 2, just a newline.

        Examples:
            ./ulstr "Hello World" -> hELLO wORLD
            ./ulstr "ABCabc123"   -> abcABC123
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'a' && c <= 'z')
                    c = c - 'a' + 'A';
                else if (c >= 'A' && c <= 'Z')
                    c = c - 'A' + 'a';
                write(1, &c, 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["Hello World"], ["ABCabc123"], [""], [], ["a", "b"],
            ["MiXeD CaSe"],
        ],
    },

    # ── LEVEL 2 ────────────────────────────────────────────────
    "ft_atoi": {
        "level": 2, "function": "ft_atoi",
        "standard": True,
        "prototype": "int ft_atoi(const char *str);",
        "args": ["str"], "returns": "int", "forbidden": ["atoi"],
        "hint": ("Order matters: skip whitespace FIRST, then look for a "
                "single optional sign, then digits — a sign check before "
                "the whitespace skip misses inputs like '   -17'."),
        "subject": _sub_c("ft_atoi", "int ft_atoi(const char *str);", "None", """
        Write your own version of atoi(): convert the initial portion of
        the string to an int, skipping leading whitespace and honouring an
        optional leading '+' or '-'.

        Examples:
            ft_atoi("42")       -> 42
            ft_atoi("   -17")   -> -17
            ft_atoi("+123abc")  -> 123
            ft_atoi("abc")      -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int ft_atoi(const char *str)
        {
            int i;
            int sign;
            long res;

            i = 0;
            sign = 1;
            res = 0;
            while (str[i] == ' ' || (str[i] >= 9 && str[i] <= 13))
                i++;
            if (str[i] == '+' || str[i] == '-')
            {
                if (str[i] == '-')
                    sign = -1;
                i++;
            }
            while (str[i] >= '0' && str[i] <= '9')
            {
                res = res * 10 + (str[i] - '0');
                i++;
            }
            return ((int)(res * sign));
        }
        """),
        "cases": [
            ["42"], ["   -17"], ["+123abc"], ["abc"], [""], ["  0"],
            ["2147483647"], ["-2147483648"], ["   +  5"],
        ],
    },
    "is_power_of_2": {
        "level": 2, "function": "is_power_of_2",
        "standard": True,
        "prototype": "int is_power_of_2(unsigned int n);",
        "args": ["int"], "returns": "int",
        "hint": ("The classic n & (n - 1) trick breaks for n = 0, since "
                "n is unsigned: 0 - 1 underflows to UINT_MAX, and 0 & "
                "UINT_MAX is 0 — which looks like a power of 2 unless "
                "you special-case it."),
        "subject": _sub_c("is_power_of_2", "int is_power_of_2(unsigned int n);",
                         "None", """
        Write a function that determines if a given number is a power of
        2. Returns 1 if it is, 0 otherwise.

        Examples:
            is_power_of_2(16) -> 1
            is_power_of_2(15) -> 0
            is_power_of_2(0)  -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int is_power_of_2(unsigned int n)
        {
            if (n == 0)
                return (0);
            return ((n & (n - 1)) == 0);
        }
        """),
        "cases": [[0], [1], [2], [3], [4], [15], [16], [1024], [1023], [2147483647]],
    },
    "max": {
        "level": 2, "function": "max",
        "standard": True,
        "prototype": "int max(int *tab, unsigned int len);",
        "args": ["int_arr"], "returns": "int",
        "hint": ("Initialize your running best to tab[0], not to 0 — "
                "starting from 0 gives the wrong answer whenever every "
                "element is negative. Handle len == 0 as its own special "
                "case before touching tab[0], since there's no element "
                "there to read."),
        "subject": _sub_c("max", "int max(int *tab, unsigned int len);", "None", """
        Write a function that returns the largest number in an array of
        `len` integers. An empty array (len == 0) returns 0.

        Examples:
            max([3,7,2,9,4], 5) -> 9
            max([], 0)          -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int max(int *tab, unsigned int len)
        {
            unsigned int i;
            int best;

            if (len == 0)
                return (0);
            best = tab[0];
            i = 1;
            while (i < len)
            {
                if (tab[i] > best)
                    best = tab[i];
                i++;
            }
            return (best);
        }
        """),
        "cases": [
            [[3, 7, 2, 9, 4]], [[]], [[5]], [[-1, -5, -2]], [[0, 0, 0]],
            [[100, -100, 50]],
        ],
    },
    "rot_13": {
        "level": 1, "function": "rot_13", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Only letters shift — everything else (digits, spaces, "
                "punctuation) passes through untouched. And the shift "
                "has to wrap around within its own case ('z' -> 'm', "
                "'Z' -> 'M'), so a plain += 13 without a modulo will "
                "overshoot past 'z'/'Z'."),
        "subject": _sub_c("rot_13", "int main(int argc, char **argv);", "write", """
        Write a PROGRAM that takes a string and displays it, replacing
        each of its letters by the letter 13 spaces ahead in alphabetical
        order (ROT13). 'z' becomes 'm', 'Z' becomes 'M', case unaffected.
        Followed by a newline. If argc != 2, just a newline.

        Examples:
            ./rot_13 "abc"  -> nop
            ./rot_13 ""     -> (just a newline)
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'a' && c <= 'z')
                    c = 'a' + (c - 'a' + 13) % 26;
                else if (c >= 'A' && c <= 'Z')
                    c = 'A' + (c - 'A' + 13) % 26;
                write(1, &c, 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["My horse is Amazing."], ["AkjhZ zLKIJz , 23y "],
            [], [""], ["a", "b"],
        ],
    },
    "alpha_mirror": {
        "level": 2, "function": "alpha_mirror", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("The mirror formula is 'z' - (c - 'a') for lowercase "
                "letters (and the 'Z'/'A' equivalent for uppercase) — "
                "check it against a couple of pairs by hand ('a' should "
                "become 'z', 'm' should become 'n') since a sign flip "
                "here silently mirrors the wrong direction instead of "
                "crashing."),
        "subject": _sub_c("alpha_mirror", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays it with every
        letter mirrored in the alphabet ('a' <-> 'z', 'b' <-> 'y', ...),
        case unchanged, followed by a newline. If argc != 2, just a
        newline.

        Examples:
            ./alpha_mirror "abc" -> zyx
            ./alpha_mirror "Hi!" -> Sr!
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'a' && c <= 'z')
                    c = 'z' - (c - 'a');
                else if (c >= 'A' && c <= 'Z')
                    c = 'Z' - (c - 'A');
                write(1, &c, 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["My Test String."], [""], [], ["a", "b"], ["Hello"],
        ],
    },
    "camel_to_snake": {
        "level": 2, "function": "camel_to_snake", "kind": "program",
        "fuzz_argv": "camel",
        "standard": True,
        "hint": ("Each uppercase letter becomes an underscore PLUS its "
                "lowercase self, in that order — insert the '_' right "
                "before the letter, not after, or every word boundary "
                "ends up shifted by one character."),
        "subject": _sub_c("camel_to_snake", "int main(int argc, char **argv);",
                         "malloc, realloc, write", """
        Write a PROGRAM that takes a single lowerCamelCase string (each
        word capitalized except the first) and converts it to
        snake_case (words lowercase, joined by '_'), followed by a
        newline. If argc != 2, just a newline.

        Examples:
            ./camel_to_snake "helloWorld"   -> hello_world
            ./camel_to_snake "thisIsATest"  -> this_is_a_test
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'A' && c <= 'Z')
                {
                    write(1, "_", 1);
                    c = c - 'A' + 'a';
                    write(1, &c, 1);
                }
                else
                    write(1, &c, 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["helloWorld"], ["thisIsATest"], ["single"], [""], [],
            ["a", "b"],
        ],
    },
    "do_op": {
        "level": 2, "function": "do_op", "kind": "program",
        "fuzz_argv": "do_op",
        "standard": True,
        "hint": ("The operator is a single character — read it with "
                "argv[2][0], not by comparing the whole argv[2] string — "
                "and since the subject guarantees valid inputs that fit "
                "in an int, a plain if/else if chain over '+', '-', '*', "
                "'/', '%' is all you need, no overflow handling "
                "required."),
        "subject": _sub_c("do_op", "int main(int argc, char **argv);",
                         "atoi, printf, write", """
        Write a PROGRAM that takes three arguments: a base-10 integer, an
        arithmetic operator (one of + - * / %), and another integer. It
        displays the result of that operation, followed by a newline.
        Inputs are always valid and the result always fits in an int. If
        argc != 4, just a newline.

        Examples:
            ./do_op 3 + 4  -> 7
            ./do_op 20 / 4 -> 5
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdio.h>
        #include <stdlib.h>

        int main(int argc, char **argv)
        {
            int a;
            int b;
            char op;

            if (argc != 4)
            {
                printf("\\n");
                return (0);
            }
            a = atoi(argv[1]);
            op = argv[2][0];
            b = atoi(argv[3]);
            if (op == '+')
                printf("%d\\n", a + b);
            else if (op == '-')
                printf("%d\\n", a - b);
            else if (op == '*')
                printf("%d\\n", a * b);
            else if (op == '/')
                printf("%d\\n", a / b);
            else if (op == '%')
                printf("%d\\n", a % b);
            return (0);
        }
        """),
        "cases": [
            ["3", "+", "4"], ["10", "-", "6"], ["6", "*", "7"],
            ["20", "/", "4"], ["10", "%", "3"], ["-5", "+", "5"], [],
        ],
    },
    "ft_strcmp": {
        "level": 2, "function": "ft_strcmp",
        "standard": True,
        "prototype": "int ft_strcmp(char *s1, char *s2);",
        "args": ["str", "str"], "returns": "strcmp_sign",
        "forbidden": ["strcmp"],
        "hint": ("Cast each character to `unsigned char` before "
                "subtracting — comparing them as plain (signed) `char` "
                "gives the wrong sign whenever a string contains a byte "
                ">= 128 — and only the SIGN of your return value is "
                "checked, so you don't need to reproduce glibc's exact "
                "magnitude."),
        "subject": _sub_c("ft_strcmp", "int ft_strcmp(char *s1, char *s2);",
                         "None", """
        Reproduce the behaviour of the standard strcmp(): compare two
        strings. (Only the SIGN of your return value is graded, exactly
        like the real moulinette.)

        Examples:
            ft_strcmp("abc", "abc") -> 0
            ft_strcmp("abc", "abd") -> negative
        """),
        "oracle_c": textwrap.dedent("""
        int ft_strcmp(char *s1, char *s2)
        {
            int i;

            i = 0;
            while (s1[i] && s1[i] == s2[i])
                i++;
            return ((unsigned char)s1[i] - (unsigned char)s2[i]);
        }
        """),
        "cases": [
            ["abc", "abc"], ["abc", "abd"], ["abd", "abc"], ["", ""],
            ["a", ""], ["Hello", "hello"],
        ],
    },
    "ft_strcspn": {
        "level": 2, "function": "ft_strcspn",
        "standard": True,
        "prototype": "size_t ft_strcspn(const char *s, const char *reject);",
        "args": ["str", "str"], "returns": "int", "forbidden": ["strcspn"],
        "hint": ("ft_strcspn stops at the first character of `s` that "
                "DOES appear in `reject` — it's the complement of "
                "strspn, so a natural bug is copying strspn's stop "
                "condition and forgetting to flip found/not-found."),
        "subject": _sub_c("ft_strcspn",
                         "size_t ft_strcspn(const char *s, const char *reject);",
                         "None", """
        Reproduce the behaviour of the standard strcspn(): return the
        length of the initial segment of `s` made up of characters that
        do NOT appear in `reject`.

        Examples:
            ft_strcspn("hello", "l") -> 2
            ft_strcspn("hello", "xyz") -> 5
        """),
        "oracle_c": textwrap.dedent("""
        int ft_strcspn(char *s, char *reject)
        {
            int i;
            int j;
            int found;

            i = 0;
            while (s[i])
            {
                j = 0;
                found = 0;
                while (reject[j])
                {
                    if (s[i] == reject[j])
                        found = 1;
                    j++;
                }
                if (found)
                    return (i);
                i++;
            }
            return (i);
        }
        """),
        "cases": [
            ["hello", "l"], ["hello", "xyz"], ["", "abc"], ["abc", ""],
            ["hello world", "ow"],
        ],
    },
    "ft_strdup": {
        "level": 2, "function": "ft_strdup",
        "standard": True,
        "prototype": "char *ft_strdup(char *src);",
        "args": ["str"], "returns": "str_owned", "forbidden": ["strdup"],
        "hint": ("The malloc size needs room for the null terminator too "
                "— strlen(src) alone is one byte too small; it's "
                "strlen(src) + 1."),
        "subject": _sub_c("ft_strdup", "char *ft_strdup(char *src);",
                         "malloc", """
        Reproduce the behaviour of the standard strdup(): return a newly
        malloc'd copy of the string.

        Examples:
            ft_strdup("hello") -> a new, independent "hello" string
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        char *ft_strdup(char *src)
        {
            char *dst;
            int i;
            int len;

            len = 0;
            while (src[len])
                len++;
            dst = malloc(sizeof(char) * (len + 1));
            if (!dst)
                return (0);
            i = 0;
            while (src[i])
            {
                dst[i] = src[i];
                i++;
            }
            dst[i] = '\\0';
            return (dst);
        }
        """),
        "cases": [["hello"], [""], ["a"], ["Testing 123"]],
    },
    "ft_strpbrk": {
        "level": 2, "function": "ft_strpbrk",
        "standard": True,
        "prototype": "char *ft_strpbrk(const char *s1, const char *s2);",
        "args": ["str", "str"], "returns": "str", "forbidden": ["strpbrk"],
        "hint": ("Return a POINTER into s1 (s1 + i), not an index or the "
                "matched character itself — and if nothing in s1 "
                "matches anything in s2 (including when s2 is empty), "
                "you must return NULL rather than s1 or a pointer past "
                "its end."),
        "subject": _sub_c("ft_strpbrk",
                         "char *ft_strpbrk(const char *s1, const char *s2);",
                         "None", """
        Reproduce the behaviour of the standard strpbrk(): return a
        pointer to the first character in s1 that also appears anywhere
        in s2 (NULL if none does).

        Examples:
            ft_strpbrk("hello", "lo") -> "llo" (points at the first 'l')
            ft_strpbrk("hello", "xyz") -> NULL
        """),
        "oracle_c": textwrap.dedent("""
        char *ft_strpbrk(char *s1, char *s2)
        {
            int i;
            int j;

            i = 0;
            while (s1[i])
            {
                j = 0;
                while (s2[j])
                {
                    if (s1[i] == s2[j])
                        return (s1 + i);
                    j++;
                }
                i++;
            }
            return (0);
        }
        """),
        "cases": [
            ["hello", "lo"], ["hello", "xyz"], ["abcdef", "fed"],
            ["", "abc"], ["abc", ""],
        ],
    },
    "ft_strrev": {
        "level": 2, "function": "ft_strrev",
        "standard": True,
        "prototype": "char *ft_strrev(char *str);",
        "args": ["buf"], "returns": "str",
        "hint": ("Watch the empty-string case: computing the last index "
                "as strlen(str) - 1 without checking for length 0 first "
                "walks off the front of the buffer with a negative "
                "index instead of leaving an empty string untouched."),
        "subject": _sub_c("ft_strrev", "char *ft_strrev(char *str);", "None", """
        Write a function that reverses a string IN PLACE and returns it.

        Examples:
            ft_strrev("hello") -> "olleh" (str itself is modified)
        """),
        "oracle_c": textwrap.dedent("""
        char *ft_strrev(char *str)
        {
            int i;
            int j;
            char tmp;

            i = 0;
            j = 0;
            while (str[j])
                j++;
            if (j > 0)
                j--;
            while (i < j)
            {
                tmp = str[i];
                str[i] = str[j];
                str[j] = tmp;
                i++;
                j--;
            }
            return (str);
        }
        """),
        "cases": [
            ["hello"], [""], ["a"], ["ab"], ["racecar"], ["Testing"],
        ],
    },
    "ft_strspn": {
        "level": 2, "function": "ft_strspn",
        "standard": True,
        "prototype": "size_t ft_strspn(const char *s, const char *accept);",
        "args": ["str", "str"], "returns": "int", "forbidden": ["strspn"],
        "hint": ("ft_strspn measures how many characters from the START "
                "of `s` are ALL found in `accept` — stop at the very "
                "first character that ISN'T in `accept`, the opposite "
                "check from strcspn's 'first character that IS in "
                "reject'."),
        "subject": _sub_c("ft_strspn",
                         "size_t ft_strspn(const char *s, const char *accept);",
                         "None", """
        Reproduce the behaviour of the standard strspn(): return the
        length of the initial segment of `s` made up entirely of
        characters from `accept`.

        Examples:
            ft_strspn("aabbcc", "ab") -> 4
            ft_strspn("hello", "xyz") -> 0
        """),
        "oracle_c": textwrap.dedent("""
        int ft_strspn(char *s, char *accept)
        {
            int i;
            int j;
            int ok;

            i = 0;
            while (s[i])
            {
                j = 0;
                ok = 0;
                while (accept[j])
                {
                    if (s[i] == accept[j])
                        ok = 1;
                    j++;
                }
                if (!ok)
                    return (i);
                i++;
            }
            return (i);
        }
        """),
        "cases": [
            ["aabbcc", "ab"], ["hello", "xyz"], ["", "abc"], ["abc", ""],
            ["112233", "123"],
        ],
    },
    "last_word": {
        "level": 2, "function": "last_word", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Scan from the END of the string: first skip past any "
                "trailing spaces/tabs, then walk backward while you're "
                "still inside the last word — only skipping LEADING "
                "whitespace (like first_word does) breaks as soon as "
                "the input has trailing spaces."),
        "subject": _sub_c("last_word", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays its last
        whitespace-delimited word, followed by a newline. If argc != 2,
        or there are no words, just a newline.

        Examples:
            ./last_word "hello world" -> world
            ./last_word "   "          -> (just a newline)
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int end;
            int start;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            end = 0;
            while (argv[1][end])
                end++;
            while (end > 0 && is_sep(argv[1][end - 1]))
                end--;
            start = end;
            while (start > 0 && !is_sep(argv[1][start - 1]))
                start--;
            while (start < end)
            {
                write(1, &argv[1][start], 1);
                start++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["hello world"], ["   trailing spaces   "], ["   "], [],
            ["a", "b"], ["oneword"],
        ],
    },
    "print_bits": {
        "level": 2, "function": "print_bits",
        "standard": True,
        "prototype": "void print_bits(unsigned char octet);",
        "args": ["int"], "returns": "void",
        "hint": ("Print from bit 7 down to bit 0 (most significant "
                "first): test `(octet >> i) & 1` with i counting DOWN "
                "from 7 to 0 — counting i up from 0 instead prints the "
                "bits in reverse order."),
        "subject": _sub_c("print_bits", "void print_bits(unsigned char octet);",
                         "write", """
        Write a function that prints a byte in binary (8 characters, '0'
        or '1'), most significant bit first, with NO trailing newline.

        Examples:
            print_bits(2)   -> prints: 00000010
            print_bits(255) -> prints: 11111111
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        void print_bits(unsigned char octet)
        {
            int i;
            char c;

            i = 7;
            while (i >= 0)
            {
                c = ((octet >> i) & 1) ? '1' : '0';
                write(1, &c, 1);
                i--;
            }
        }
        """),
        "cases": [[2], [0], [255], [128], [170], [1]],
    },
    "snake_to_camel": {
        "level": 2, "function": "snake_to_camel", "kind": "program",
        "fuzz_argv": "snake",
        "standard": True,
        "hint": ("Underscores themselves must never appear in the "
                "output — consume each '_' silently and just remember, "
                "with a flag, that the NEXT letter needs to be "
                "uppercased, then clear that flag once you've used it "
                "so only the letter right after an underscore gets "
                "capitalized."),
        "subject": _sub_c("snake_to_camel", "int main(int argc, char **argv);",
                         "malloc, free, realloc, write", """
        Write a PROGRAM that takes a single snake_case string (words
        lowercase, joined by '_') and converts it to lowerCamelCase (each
        word capitalized except the first, no separators), followed by a
        newline. If argc != 2, just a newline.

        Examples:
            ./snake_to_camel "hello_world"    -> helloWorld
            ./snake_to_camel "this_is_a_test" -> thisIsATest
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            int upnext;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            upnext = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c == '_')
                    upnext = 1;
                else
                {
                    if (upnext && c >= 'a' && c <= 'z')
                        c = c - 'a' + 'A';
                    write(1, &c, 1);
                    upnext = 0;
                }
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["hello_world"], ["this_is_a_test"], ["single"], [""], [],
            ["a", "b"],
        ],
    },
    "swap_bits": {
        "level": 2, "function": "swap_bits",
        "standard": True,
        "prototype": "unsigned char swap_bits(unsigned char octet);",
        "args": ["int"], "returns": "int",
        "hint": ("Mask out each nibble before you shift it: "
                "(octet & 0xF0) >> 4 for the upper half, "
                "(octet & 0x0F) << 4 for the lower half — shifting "
                "first and masking after (or not masking at all) lets "
                "bits from one half bleed into the other."),
        "subject": _sub_c("swap_bits",
                         "unsigned char swap_bits(unsigned char octet);",
                         "None", """
        Write a function that takes a byte, swaps its two 4-bit halves
        (nibbles), and returns the result.

        Examples:
            swap_bits(0x41) -> 0x14   # 0100 0001 -> 0001 0100
            swap_bits(0)    -> 0
        """),
        "oracle_c": textwrap.dedent("""
        unsigned char swap_bits(unsigned char octet)
        {
            unsigned char upper;
            unsigned char lower;

            upper = (octet & 0xF0) >> 4;
            lower = (octet & 0x0F) << 4;
            return (lower | upper);
        }
        """),
        "cases": [[65], [0], [255], [15], [240], [18]],
    },
    "inter": {
        "level": 2, "function": "inter", "kind": "program",
        "fuzz_argv": "two_strings",
        "standard": True,
        "hint": ("Two conditions per character of the FIRST string: it must "
                "appear somewhere in the second string, and it must not have "
                "appeared earlier in the first string (that's the 'no "
                "doubles' part — check positions before the current one, "
                "not what you've printed from the second string)."),
        "subject": _sub_c("inter", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes two strings and displays, without
        doubles, the characters that appear in BOTH strings, in the order
        they appear in the first one, followed by a newline. If argc != 3,
        just a newline.

        Examples:
            ./inter "padinton" "paqefwtdjetyiytjneytjoeyjnejeyj" -> padinto
            ./inter "ddf6vewg64f" "gtwthgdwthdwfteewhrtag6h4ffdhsd" -> df6ewg4
            ./inter "rien" "cette phrase ne cache rien" -> rien
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int in_str(char *s, char c, int limit)
        {
            int i;

            i = 0;
            while (s[i] && (limit < 0 || i < limit))
            {
                if (s[i] == c)
                    return (1);
                i++;
            }
            return (0);
        }

        int main(int argc, char **argv)
        {
            int i;

            if (argc == 3)
            {
                i = 0;
                while (argv[1][i])
                {
                    if (!in_str(argv[1], argv[1][i], i)
                        && in_str(argv[2], argv[1][i], -1))
                        write(1, &argv[1][i], 1);
                    i++;
                }
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["padinton", "paqefwtdjetyiytjneytjoeyjnejeyj"],
            ["ddf6vewg64f", "gtwthgdwthdwfteewhrtag6h4ffdhsd"],
            ["rien", "cette phrase ne cache rien"],
            ["abc", "xyz"], ["aaa", "a"], ["", "abc"], ["abc", ""],
            [], ["only one"], ["a", "b", "c"],
        ],
    },
    "union": {
        "level": 2, "function": "union", "kind": "program",
        "fuzz_argv": "two_strings",
        "standard": True,
        "hint": ("Dedup against everything printed so far, not just "
                "within the string you're currently scanning — a "
                "character repeated inside the SAME string (e.g. 'aaa') "
                "must still only print once."),
        "subject": _sub_c("union", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes two strings and displays, without
        duplicates, every character that appears in either one, in the
        order each first appears (scanning the first string then the
        second), followed by a newline. If argc != 3, just a newline.

        Examples:
            ./union "abc" "bcd" -> abcd
            ./union "aaa" "aaa" -> a
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int seen(char *buf, int n, char c)
        {
            int i;

            i = 0;
            while (i < n)
            {
                if (buf[i] == c)
                    return (1);
                i++;
            }
            return (0);
        }

        int main(int argc, char **argv)
        {
            char buf[512];
            int n;
            int k;
            int i;

            if (argc != 3)
            {
                write(1, "\\n", 1);
                return (0);
            }
            n = 0;
            k = 0;
            while (argv[1][k])
            {
                if (!seen(buf, n, argv[1][k]))
                    buf[n++] = argv[1][k];
                k++;
            }
            k = 0;
            while (argv[2][k])
            {
                if (!seen(buf, n, argv[2][k]))
                    buf[n++] = argv[2][k];
                k++;
            }
            i = 0;
            while (i < n)
            {
                write(1, &buf[i], 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc", "bcd"], ["hello", "world"], ["aaa", "aaa"],
            ["", "abc"], ["abc", ""], [], ["x"],
        ],
    },
    "wdmatch": {
        "level": 2, "function": "wdmatch", "kind": "program",
        "fuzz_argv": "subsequence",
        "standard": True,
        "hint": ("This is a subsequence check, not 'do these characters "
                "appear somewhere' — walk both strings with two "
                "indices, only advancing the first string's index on a "
                "match, and it's a match only if that index reaches the "
                "end of the first string by the time the second one "
                "runs out."),
        "subject": _sub_c("wdmatch", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes two strings and checks whether the
        first can be spelled out using characters from the second, in
        order (not necessarily consecutively — i.e. the first is a
        subsequence of the second). If so, display the first string,
        followed by a newline; otherwise just a newline. If argc != 3,
        just a newline.

        Examples:
            ./wdmatch "abc" "xaxbxc" -> abc
            ./wdmatch "abc" "xbxax"  -> (just a newline)
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            int j;

            if (argc != 3)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            j = 0;
            while (argv[1][i] && argv[2][j])
            {
                if (argv[1][i] == argv[2][j])
                    i++;
                j++;
            }
            if (argv[1][i] == '\\0')
            {
                j = 0;
                while (argv[1][j])
                    j++;
                write(1, argv[1], j);
                write(1, "\\n", 1);
            }
            else
                write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc", "xaxbxc"], ["abc", "xbxax"], ["", "abc"], ["abc", ""],
            [], ["a"],
        ],
    },
    "epur_str": {
        "level": 3, "function": "epur_str", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Don't write a space the instant you see one — set a "
                "'need a space before the next word' flag instead, and "
                "only emit it once you actually reach the next "
                "non-space character. That naturally collapses runs of "
                "whitespace and avoids a trailing space when the input "
                "ends in whitespace."),
        "subject": _sub_c("epur_str", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays it with exactly
        one space between words and no leading/trailing whitespace,
        followed by a newline. A word is a run of non-space/tab
        characters. If argc != 2, or there are no words, just a newline.

        Examples:
            ./epur_str "  hello    world  " -> hello world
            ./epur_str "a   b   c"           -> a b c
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int i;
            int need_space;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i] && is_sep(argv[1][i]))
                i++;
            need_space = 0;
            while (argv[1][i])
            {
                if (is_sep(argv[1][i]))
                {
                    need_space = 1;
                    i++;
                    continue ;
                }
                if (need_space)
                {
                    write(1, " ", 1);
                    need_space = 0;
                }
                write(1, &argv[1][i], 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["  hello    world  "], ["a   b   c"], ["single"], ["   "],
            [""], [], ["a", "b"],
        ],
    },
    "expand_str": {
        "level": 3, "function": "expand_str", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("Same idea as collapsing whitespace to a single space, "
                "except each boundary between words prints exactly "
                "three spaces — track a 'separator pending' flag and "
                "only emit those three spaces once you reach the start "
                "of the next word, so trailing whitespace at the end "
                "never produces a dangling separator."),
        "subject": _sub_c("expand_str", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays it with exactly
        three spaces between words and no leading/trailing whitespace,
        followed by a newline. A word is a run of non-space/tab
        characters. If argc != 2, or there are no words, just a newline.

        Examples:
            ./expand_str "hello world" -> hello   world
            ./expand_str "a b"          -> a   b
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int i;
            int need_space;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i] && is_sep(argv[1][i]))
                i++;
            need_space = 0;
            while (argv[1][i])
            {
                if (is_sep(argv[1][i]))
                {
                    need_space = 1;
                    i++;
                    continue ;
                }
                if (need_space)
                {
                    write(1, "   ", 3);
                    need_space = 0;
                }
                write(1, &argv[1][i], 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["  hello    world  "], ["a   b   c"], ["single"], ["   "],
            [""], [], ["a", "b"],
        ],
    },
    "ft_atoi_base": {
        "level": 3, "function": "ft_atoi_base",
        "standard": True,
        "prototype": "int ft_atoi_base(const char *str, int str_base);",
        "args": ["str", "int"], "returns": "int",
        "hint": ("A '-' only counts as the sign if it's the very first "
                "character — one later in the string just means an "
                "invalid digit, ending the parse right there. Also make "
                "sure you reject a digit character that's valid in "
                "general but too large for THIS base (e.g. '2' in base "
                "2)."),
        "subject": _sub_c("ft_atoi_base",
                         "int ft_atoi_base(const char *str, int str_base);",
                         "None", """
        Write a function that converts a string written in base
        `str_base` (2 to 16, digits "0123456789abcdef", case-insensitive)
        into a base-10 int. A leading '-' is only recognized as the very
        first character. Stop at the first character that isn't a valid
        digit for that base.

        Examples:
            ft_atoi_base("ff", 16)   -> 255
            ft_atoi_base("101", 2)   -> 5
            ft_atoi_base("-101", 2)  -> -5
        """),
        "oracle_c": textwrap.dedent("""
        int ft_atoi_base(char *str, int str_base)
        {
            char digits[] = "0123456789abcdef";
            int i;
            int sign;
            long res;
            int d;
            int j;
            char c;

            i = 0;
            sign = 1;
            res = 0;
            if (str[i] == '-')
            {
                sign = -1;
                i++;
            }
            while (str[i])
            {
                c = str[i];
                if (c >= 'A' && c <= 'F')
                    c = c - 'A' + 'a';
                d = -1;
                j = 0;
                while (digits[j])
                {
                    if (digits[j] == c)
                        d = j;
                    j++;
                }
                if (d < 0 || d >= str_base)
                    break ;
                res = res * str_base + d;
                i++;
            }
            return ((int)(res * sign));
        }
        """),
        "cases": [
            ["101", 2], ["ff", 16], ["FF", 16], ["777", 8],
            ["-101", 2], ["z", 16], ["123", 10],
        ],
    },
    "ft_range": {
        "level": 3, "function": "ft_range",
        "standard": True,
        "prototype": "int *ft_range(int start, int end);",
        "args": ["int", "int"], "returns": "int_arr",
        "return_len": lambda a: abs(a[1] - a[0]) + 1,
        "hint": ("The element count is abs(end - start) + 1, not "
                "end - start + 1 — that goes negative (or too small) "
                "the moment start > end."),
        "subject": _sub_c("ft_range", "int *ft_range(int start, int end);",
                         "malloc", """
        Write a function that mallocs an array of ints filled with every
        consecutive value from `start` to `end` inclusive (in ascending
        order even if start > end — that's ft_rrange's job), and returns
        a pointer to it.

        Examples:
            ft_range(1, 3)  -> [1, 2, 3]
            ft_range(-1, 2) -> [-1, 0, 1, 2]
            ft_range(0, 0)  -> [0]
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        int *ft_range(int start, int end)
        {
            int *res;
            int n;
            int i;
            int step;

            n = (end >= start) ? (end - start + 1) : (start - end + 1);
            step = (end >= start) ? 1 : -1;
            res = malloc(sizeof(int) * n);
            if (!res)
                return (0);
            i = 0;
            while (i < n)
            {
                res[i] = start + i * step;
                i++;
            }
            return (res);
        }
        """),
        "cases": [[1, 3], [-1, 2], [0, 0], [0, -3], [5, 5]],
    },
    "ft_rrange": {
        "level": 3, "function": "ft_rrange",
        "standard": True,
        "prototype": "int *ft_rrange(int start, int end);",
        "args": ["int", "int"], "returns": "int_arr",
        "return_len": lambda a: abs(a[1] - a[0]) + 1,
        "hint": ("Don't just call ft_range and reverse it — ft_range's "
                "own contract stays ascending even when start > end, so "
                "the two functions need independent fill directions, "
                "not a shared helper that assumes one order."),
        "subject": _sub_c("ft_rrange", "int *ft_rrange(int start, int end);",
                         "malloc", """
        Like ft_range, but the array runs from `end` down to `start`
        (still inclusive of both ends).

        Examples:
            ft_rrange(1, 3)  -> [3, 2, 1]
            ft_rrange(0, -3) -> [-3, -2, -1, 0]
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        int *ft_rrange(int start, int end)
        {
            int *res;
            int n;
            int i;
            int step;
            int cur;

            n = (end >= start) ? (end - start + 1) : (start - end + 1);
            step = (end >= start) ? 1 : -1;
            res = malloc(sizeof(int) * n);
            if (!res)
                return (0);
            cur = end;
            i = 0;
            while (i < n)
            {
                res[i] = cur;
                cur -= step;
                i++;
            }
            return (res);
        }
        """),
        "cases": [[1, 3], [-1, 2], [0, 0], [0, -3], [5, 5]],
    },
    "paramsum": {
        "level": 3, "function": "paramsum", "kind": "program",
        "fuzz_argv": "any_args",
        "standard": True,
        "hint": ("argc counts the program's own name too — the number "
                "of actual arguments passed is argc - 1, not argc "
                "itself."),
        "subject": _sub_c("paramsum", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that displays the number of arguments passed to
        it, followed by a newline. No arguments displays 0.

        Examples:
            ./paramsum a b c -> 3
            ./paramsum        -> 0
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static void put_nbr(int n)
        {
            char digit;

            if (n >= 10)
                put_nbr(n / 10);
            digit = '0' + n % 10;
            write(1, &digit, 1);
        }

        int main(int argc, char **argv)
        {
            (void)argv;
            put_nbr(argc - 1);
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [["1", "2", "3"], [], ["a"], ["a", "b", "c", "d", "e"]],
    },
    "print_hex": {
        "level": 3, "function": "print_hex", "kind": "program",
        "fuzz_argv": "non_negative_int",
        "standard": True,
        "forbidden": ["atoi"],
        "hint": ("atoi is forbidden, so parse the decimal argument "
                "yourself before converting it to hex. Peeling off "
                "digits with n % 16 and n /= 16 produces them "
                "least-significant first, so collect them into a buffer "
                "and print it backwards — and n == 0 needs its own "
                "special case, since that peeling loop produces zero "
                "digits for it."),
        "subject": _sub_c("print_hex", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a non-negative base-10 number and
        displays it in base 16 (lowercase digits, no leading zeros),
        followed by a newline. If argc != 2, just a newline.

        Examples:
            ./print_hex 255  -> ff
            ./print_hex 4096 -> 1000
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            long n;
            char buf[32];
            int i;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            n = atol(argv[1]);
            if (n == 0)
            {
                write(1, "0\\n", 2);
                return (0);
            }
            i = 0;
            while (n > 0)
            {
                buf[i] = "0123456789abcdef"[n % 16];
                n /= 16;
                i++;
            }
            while (i > 0)
            {
                i--;
                write(1, &buf[i], 1);
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [["10"], ["255"], ["0"], ["16"], [], ["4096"]],
    },
    "rstr_capitalizer": {
        "level": 3, "function": "rstr_capitalizer", "kind": "program",
        "fuzz_argv": "sentences",
        "standard": True,
        "hint": ("'Last letter' means the last ALPHABETIC character of "
                "the word, not simply its last character — a word like "
                "'test.' or 'end!' needs a first pass to locate its last "
                "actual letter before you can safely uppercase that one "
                "and lowercase the rest."),
        "subject": _sub_c("rstr_capitalizer",
                         "int main(int argc, char **argv);", "write", """
        Write a PROGRAM that takes one or more strings and, for each one,
        uppercases the LAST letter of every word and lowercases the rest
        (a single-letter word is uppercased), printing each argument's
        result on its own line. No arguments: just a newline.

        Examples:
            ./rstr_capitalizer "a first test" -> a firsT tesT
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        static int is_alpha(char c)
        {
            return ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'));
        }

        static void process(char *word, int len)
        {
            int i;
            int last_alpha;
            char c;

            last_alpha = -1;
            i = 0;
            while (i < len)
            {
                if (is_alpha(word[i]))
                    last_alpha = i;
                i++;
            }
            i = 0;
            while (i < len)
            {
                c = word[i];
                if (is_alpha(c))
                {
                    if (i == last_alpha && c >= 'a' && c <= 'z')
                        c = c - 'a' + 'A';
                    else if (i != last_alpha && c >= 'A' && c <= 'Z')
                        c = c - 'A' + 'a';
                }
                write(1, &c, 1);
                i++;
            }
        }

        int main(int argc, char **argv)
        {
            int a;
            int i;
            int start;

            if (argc < 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            a = 1;
            while (a < argc)
            {
                i = 0;
                while (argv[a][i])
                {
                    start = i;
                    while (argv[a][i] && !is_sep(argv[a][i]))
                        i++;
                    process(argv[a] + start, i - start);
                    while (argv[a][i] && is_sep(argv[a][i]))
                    {
                        write(1, &argv[a][i], 1);
                        i++;
                    }
                }
                write(1, "\\n", 1);
                a++;
            }
            return (0);
        }
        """),
        "cases": [
            ["a first little test"], ["ALREADY DONE"],
            ["  double  spaced  "], [], ["one"],
            ["hello world", "second string"],
        ],
    },
    "str_capitalizer": {
        "level": 3, "function": "str_capitalizer", "kind": "program",
        "fuzz_argv": "sentences",
        "standard": True,
        "hint": ("Track a 'start of a new word' flag that gets set on "
                "every separator character and cleared right after you "
                "write the first letter of the next word — that way "
                "multiple separators in a row (or the very start of the "
                "string) don't cause you to lose track of where a word "
                "begins."),
        "subject": _sub_c("str_capitalizer",
                         "int main(int argc, char **argv);", "write", """
        Write a PROGRAM that takes one or more strings and, for each one,
        uppercases the FIRST letter of every word and lowercases the
        rest, printing each argument's result on its own line. No
        arguments: just a newline.

        Examples:
            ./str_capitalizer "a first test" -> A First Test
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int a;
            int i;
            int start_of_word;
            char c;

            if (argc < 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            a = 1;
            while (a < argc)
            {
                i = 0;
                start_of_word = 1;
                while (argv[a][i])
                {
                    c = argv[a][i];
                    if (is_sep(c))
                        start_of_word = 1;
                    else
                    {
                        if (start_of_word && c >= 'a' && c <= 'z')
                            c = c - 'a' + 'A';
                        else if (!start_of_word && c >= 'A' && c <= 'Z')
                            c = c - 'A' + 'a';
                        start_of_word = 0;
                    }
                    write(1, &c, 1);
                    i++;
                }
                write(1, "\\n", 1);
                a++;
            }
            return (0);
        }
        """),
        "cases": [
            ["a first little test"], ["ALREADY DONE"],
            ["  double  spaced  "], [], ["one"],
            ["hello world", "second string"],
        ],
    },
    "tab_mult": {
        "level": 3, "function": "tab_mult", "kind": "program",
        "fuzz_argv": "small_positive_int",
        "standard": True,
        "forbidden": ["atoi"],
        "hint": ("atoi is forbidden, so you need your own "
                "decimal-string-to-int conversion for the argument — "
                "and since i * n can need more digits than n itself (up "
                "to two digits more), make sure your own "
                "number-printing routine handles multi-digit values "
                "correctly, not just single digits."),
        "subject": _sub_c("tab_mult", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a strictly positive int and displays
        its multiplication table from 1x to 9x, one line each, formatted
        as "i x n = i*n". No arguments: just a newline.

        Examples:
            ./tab_mult 9 -> 1 x 9 = 9 ... 9 x 9 = 81 (9 lines)
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>
        #include <unistd.h>

        static void put_unbr(unsigned int n)
        {
            char digit;

            if (n >= 10)
                put_unbr(n / 10);
            digit = '0' + n % 10;
            write(1, &digit, 1);
        }

        static void put_nbr(int n)
        {
            if (n < 0)
            {
                write(1, "-", 1);
                put_unbr(-(unsigned int)n);
            }
            else
                put_unbr((unsigned int)n);
        }

        int main(int argc, char **argv)
        {
            int n;
            int i;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            n = atoi(argv[1]);
            i = 1;
            while (i <= 9)
            {
                put_nbr(i);
                write(1, " x ", 3);
                put_nbr(n);
                write(1, " = ", 3);
                put_nbr(i * n);
                write(1, "\\n", 1);
                i++;
            }
            return (0);
        }
        """),
        "cases": [["9"], ["19"], ["1"], [], ["5"]],
    },

    # ── LEVEL 4 ────────────────────────────────────────────────
    "ft_split": {
        "level": 4, "function": "ft_split",
        "standard": True,
        "prototype": "char **ft_split(char *str);",
        "args": ["str"], "returns": "str_array",
        "hint": {
            "crash": ("Your pointer array needs room for a trailing "
                     "NULL too — count_words words means count_words + 1 "
                     "pointers. Same for each word's own buffer: malloc "
                     "its length plus one for its null terminator."),
            "leak": ("If you bail out partway through (a failed malloc, "
                     "an early return) you need to free every word "
                     "you've already allocated before that point, not "
                     "just leave them — a leak here almost always means "
                     "an error path that returns without cleaning up."),
            "default": ("Count your words (count_words or similar) with "
                        "exactly the same logic you later use to extract "
                        "them — a mismatch on multiple consecutive "
                        "separators is the most common bug here."),
        },
        "subject": _sub_c("ft_split", "char **ft_split(char *str);", "malloc", """
        Write a function that takes a string, splits it into words, and
        returns them as a NULL-terminated array of strings. A "word" is a
        part of the string delimited by spaces/tabs/newlines, or by the
        start/end of the string.

        Examples:
            ft_split("hello world") -> ["hello", "world"]
            ft_split("   ")          -> []
            ft_split("")             -> []
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t' || c == '\\n');
        }

        static int count_words(char *str)
        {
            int count;
            int in_word;

            count = 0;
            in_word = 0;
            while (*str)
            {
                if (!is_sep(*str) && !in_word)
                {
                    in_word = 1;
                    count++;
                }
                else if (is_sep(*str))
                    in_word = 0;
                str++;
            }
            return (count);
        }

        static char *dup_word(char *start, int len)
        {
            char *word;
            int i;

            word = malloc(sizeof(char) * (len + 1));
            if (!word)
                return (0);
            i = 0;
            while (i < len)
            {
                word[i] = start[i];
                i++;
            }
            word[i] = '\\0';
            return (word);
        }

        char **ft_split(char *str)
        {
            char **res;
            int n;
            int i;
            int len;
            int j;

            n = count_words(str);
            res = malloc(sizeof(char *) * (n + 1));
            if (!res)
                return (0);
            i = 0;
            while (*str)
            {
                while (*str && is_sep(*str))
                    str++;
                len = 0;
                while (str[len] && !is_sep(str[len]))
                    len++;
                if (len > 0)
                {
                    res[i] = dup_word(str, len);
                    if (!res[i])
                    {
                        j = 0;
                        while (j < i)
                        {
                            free(res[j]);
                            j++;
                        }
                        free(res);
                        return (0);
                    }
                    i++;
                    str += len;
                }
            }
            res[i] = NULL;
            return (res);
        }
        """),
        "cases": [
            ["hello world"], [""], ["   "], ["a"],
            ["  lorem   ipsum  dolor  "], ["one\ttwo\nthree"], ["single"],
        ],
    },
    "ft_list_size": {
        "level": 3, "function": "ft_list_size",
        "standard": True,
        "prototype": "int ft_list_size(t_list *begin_list);",
        "args": ["int_list"], "returns": "int",
        "hint": ("Walk the list with a counter that increments once per "
                "node until you hit NULL — an empty list (begin_list "
                "itself NULL) should return 0 immediately, without "
                "dereferencing anything."),
        "subject": _sub_c("ft_list_size",
                         "int ft_list_size(t_list *begin_list);", "None", """
        Write a function that returns the number of elements in the
        linked list passed to it. You must use the t_list type described
        in list.h (provided): a node holds an int `data` and a `next`
        pointer to the following node (NULL at the end of the list).

        Examples:
            ft_list_size([1,2,3]) -> 3
            ft_list_size([])       -> 0
        """),
        "oracle_c": textwrap.dedent("""
        #include "list.h"

        int ft_list_size(t_list *begin_list)
        {
            int count;

            count = 0;
            while (begin_list)
            {
                count++;
                begin_list = begin_list->next;
            }
            return (count);
        }
        """),
        "cases": [[[1, 2, 3]], [[]], [[5]], [[1, 2, 3, 4, 5, 6, 7]], [[0, 0, 0]]],
    },
    "hidenp": {
        "level": 3, "function": "hidenp", "kind": "program",
        "fuzz_argv": "subsequence",
        "standard": True,
        "hint": ("Same subsequence idea as wdmatch: advance through s2 "
                "one character at a time, but only advance your "
                "position in s1 when the characters match. The "
                "empty-string case falls out naturally as 'hidden' "
                "since your s1 index never has to move to reach its own "
                "end — don't special-case it away by mistake."),
        "subject": _sub_c("hidenp", "int main(int argc, char **argv);", "write", """
        Write a PROGRAM named hidenp that takes two strings and displays 1
        followed by a newline if the first string is "hidden" in the
        second one, 0 otherwise. s1 is hidden in s2 if every character of
        s1 can be found in s2, in the same order (not necessarily
        consecutively). The empty string is hidden in any string. If argc
        != 3, just a newline.

        Examples:
            ./hidenp "abc" "2altrb53c.sse" -> 1
            ./hidenp "abc" "btarc"          -> 0
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            int j;
            char result;

            if (argc != 3)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            j = 0;
            while (argv[1][i] && argv[2][j])
            {
                if (argv[1][i] == argv[2][j])
                    i++;
                j++;
            }
            result = (argv[1][i] == '\\0') ? '1' : '0';
            write(1, &result, 1);
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["fgex.;", "tyf34gdgf;'ektufjhgdgex.;.;rtjynur6"],
            ["abc", "2altrb53c.sse"], ["abc", "btarc"], ["", "abc"],
            ["abc", ""], ["only_one"],
        ],
    },
    "pgcd": {
        "level": 3, "function": "pgcd", "kind": "program",
        "fuzz_argv": "two_positive_ints",
        "standard": True,
        "hint": ("Classic Euclidean algorithm: repeatedly replace (a, b) "
                "with (b, a % b) until b hits 0 — a common slip is "
                "overwriting a with b's value before you've saved a's "
                "OLD value into a temporary, which corrupts the very "
                "modulo you still needed to compute."),
        "subject": _sub_c("pgcd", "int main(int argc, char **argv);",
                         "printf, atoi, malloc, free", """
        Write a PROGRAM that takes two strings representing two strictly
        positive integers and displays their greatest common divisor,
        followed by a newline. If argc != 3, just a newline.

        Examples:
            ./pgcd 42 10 -> 2
            ./pgcd 42 12 -> 6
            ./pgcd 17 3  -> 1
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdio.h>
        #include <stdlib.h>

        int main(int argc, char **argv)
        {
            int a;
            int b;
            int tmp;

            if (argc != 3)
            {
                printf("\\n");
                return (0);
            }
            a = atoi(argv[1]);
            b = atoi(argv[2]);
            while (b != 0)
            {
                tmp = b;
                b = a % b;
                a = tmp;
            }
            printf("%d\\n", a);
            return (0);
        }
        """),
        "cases": [
            ["42", "10"], ["42", "12"], ["14", "77"], ["17", "3"], [],
            ["100", "100"], ["1", "1"],
        ],
    },
    "lcm": {
        "level": 3, "function": "lcm",
        "standard": True,
        "prototype": "unsigned int lcm(unsigned int a, unsigned int b);",
        "args": ["int", "int"], "returns": "int",
        "hint": ("Compute a / gcd(a, b) * b, not (a * b) / gcd(a, b) — "
                "dividing first keeps the intermediate value smaller and "
                "avoids needless overflow. And treat a == 0 or b == 0 as "
                "its own special case returning 0, rather than feeding "
                "a 0 into your GCD loop."),
        "subject": _sub_c("lcm",
                         "unsigned int lcm(unsigned int a, unsigned int b);",
                         "None", """
        Write a function that returns the LCM (Lowest Common Multiple) of
        two unsigned ints: the smallest positive integer divisible by
        both. If either is 0, the LCM is 0.

        Examples:
            lcm(4, 6)  -> 12
            lcm(21, 6) -> 42
            lcm(0, 5)  -> 0
        """),
        "oracle_c": textwrap.dedent("""
        unsigned int lcm(unsigned int a, unsigned int b)
        {
            unsigned int x;
            unsigned int y;
            unsigned int tmp;

            if (a == 0 || b == 0)
                return (0);
            x = a;
            y = b;
            while (y != 0)
            {
                tmp = y;
                y = x % y;
                x = tmp;
            }
            return (a / x * b);
        }
        """),
        "cases": [[4, 6], [21, 6], [0, 5], [7, 7], [1, 1], [8, 12], [9, 0]],
    },
    "add_prime_sum": {
        "level": 3, "function": "add_prime_sum", "kind": "program",
        "fuzz_argv": "small_positive_int",
        "standard": True,
        "forbidden": ["atoi"],
        "hint": ("atoi is forbidden, so you need your own decimal "
                "parser for argv[1] — and both a missing argument and "
                "something that doesn't parse as a valid positive "
                "number must fall back to printing plain '0' plus a "
                "newline, not a crash or a garbage sum. Also make sure "
                "your primality check explicitly rules out values below "
                "2, since the trial-division loop alone won't naturally "
                "exclude 0 or 1."),
        "subject": _sub_c("add_prime_sum", "int main(int argc, char **argv);",
                         "write, exit", """
        Write a PROGRAM that takes a positive integer as argument and
        displays the sum of all prime numbers <= it, followed by a
        newline. If argc != 2, or the argument is not a positive number,
        just display 0 followed by a newline.

        Examples:
            ./add_prime_sum 5 -> 10   # 2 + 3 + 5
            ./add_prime_sum 7 -> 17   # 2 + 3 + 5 + 7
            ./add_prime_sum   -> 0
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>
        #include <unistd.h>

        static int is_prime(int n)
        {
            int i;

            if (n < 2)
                return (0);
            i = 2;
            while (i * i <= n)
            {
                if (n % i == 0)
                    return (0);
                i++;
            }
            return (1);
        }

        static void put_ulnbr(unsigned long n)
        {
            char digit;

            if (n >= 10)
                put_ulnbr(n / 10);
            digit = '0' + n % 10;
            write(1, &digit, 1);
        }

        static void put_lnbr(long n)
        {
            if (n < 0)
            {
                write(1, "-", 1);
                put_ulnbr(-(unsigned long)n);
            }
            else
                put_ulnbr((unsigned long)n);
        }

        int main(int argc, char **argv)
        {
            int n;
            int i;
            long sum;

            if (argc != 2 || atoi(argv[1]) <= 0)
            {
                write(1, "0\\n", 2);
                return (0);
            }
            n = atoi(argv[1]);
            sum = 0;
            i = 2;
            while (i <= n)
            {
                if (is_prime(i))
                    sum += i;
                i++;
            }
            put_lnbr(sum);
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["5"], ["7"], [], ["-3"], ["abc"], ["1"], ["2"], ["20"],
        ],
    },

    # ── LEVEL 4 ────────────────────────────────────────────────
    "sort_list": {
        "level": 4, "function": "sort_list",
        "standard": True,
        "prototype": "t_list *sort_list(t_list *lst, int (*cmp)(int, int));",
        "args": ["int_list", "cmp_ascending"], "returns": "int_list",
        "hint": ("cmp returns non-zero when its two arguments are "
                "ALREADY in the right order — swap only when it returns "
                "0, which is easy to get backwards (swapping when it "
                "returns non-zero instead) and quietly sorts everything "
                "the wrong way. Swap the node `data` values in place "
                "rather than relinking `next` pointers, so the list's "
                "structure never has to change."),
        "subject": _sub_c("sort_list",
                         "t_list *sort_list(t_list *lst, int (*cmp)(int, int));",
                         "None", """
        Write a function that sorts the list given as a parameter, using
        the function pointer `cmp` to select the order, and returns a
        pointer to the first element of the sorted list. Duplicates must
        remain. `cmp` returns a value != 0 when its two arguments are
        already in the right order, 0 otherwise — e.g. this sorts
        ascending:

            int ascending(int a, int b) { return (a <= b); }

        You must use the t_list type described in list.h (provided).

        Examples:
            sort_list([5,3,1,4,2], ascending) -> [1,2,3,4,5]
            sort_list([], ascending)           -> []
        """),
        "oracle_c": textwrap.dedent("""
        #include "list.h"

        t_list *sort_list(t_list *lst, int (*cmp)(int, int))
        {
            t_list *ptr;
            int swap;

            if (!lst)
                return (lst);
            ptr = lst;
            while (ptr->next)
            {
                if ((*cmp)(ptr->data, ptr->next->data) == 0)
                {
                    swap = ptr->data;
                    ptr->data = ptr->next->data;
                    ptr->next->data = swap;
                    ptr = lst;
                }
                else
                    ptr = ptr->next;
            }
            return (lst);
        }
        """),
        "cases": [
            [[5, 3, 1, 4, 2]], [[]], [[1]], [[2, 1]], [[3, 3, 3]],
            [[-1, -5, 2, 0]],
        ],
    },
    "sort_int_tab": {
        "level": 4, "function": "sort_int_tab",
        "standard": True,
        "prototype": "void sort_int_tab(int *tab, unsigned int size);",
        "args": ["int_arr"], "returns": "void", "print_after_args": [0],
        "hint": ("size is unsigned — if your inner loop bound is "
                "written as `size - 1` on its own (instead of "
                "`size - i`, shrinking each pass), that expression "
                "underflows to a huge number the instant size is 0, and "
                "you'll read/write past the end of an empty array "
                "instead of doing nothing."),
        "subject": _sub_c("sort_int_tab",
                         "void sort_int_tab(int *tab, unsigned int size);",
                         "None", """
        Write a function that sorts (in place) an int array of `size`
        elements, in ascending order. Duplicates must be preserved.

        Examples:
            sort_int_tab([5,3,1,4,2], 5) -> tab becomes [1,2,3,4,5]
            sort_int_tab([], 0)          -> tab stays []
        """),
        "oracle_c": textwrap.dedent("""
        void sort_int_tab(int *tab, unsigned int size)
        {
            unsigned int i;
            unsigned int j;
            int tmp;

            i = 0;
            while (i < size)
            {
                j = 0;
                while (j + 1 < size - i)
                {
                    if (tab[j] > tab[j + 1])
                    {
                        tmp = tab[j];
                        tab[j] = tab[j + 1];
                        tab[j + 1] = tmp;
                    }
                    j++;
                }
                i++;
            }
        }
        """),
        "cases": [
            [[5, 3, 1, 4, 2]], [[]], [[1]], [[2, 1]], [[3, 3, 3]],
            [[-1, -5, 2, 0]],
        ],
    },
    "reverse_bits": {
        "level": 2, "function": "reverse_bits",
        "standard": True,
        "prototype": "unsigned char reverse_bits(unsigned char octet);",
        "args": ["int"], "returns": "int",
        "hint": ("Build the result one bit at a time: take octet's "
                "lowest bit, shift it into the result from the right "
                "with `(res << 1) | (octet & 1)`, then shift octet "
                "right and repeat for exactly 8 iterations — get either "
                "shift direction backwards and you un-reverse it "
                "instead."),
        "subject": _sub_c("reverse_bits",
                         "unsigned char reverse_bits(unsigned char octet);",
                         "None", """
        Write a function that takes a byte, reverses it bit by bit, and
        returns the result. E.g. 0010 0110 becomes 0110 0100.

        Examples:
            reverse_bits(38)  -> 100   # 00100110 -> 01100100
            reverse_bits(170) -> 85    # 10101010 -> 01010101
            reverse_bits(0)   -> 0
        """),
        "oracle_c": textwrap.dedent("""
        unsigned char reverse_bits(unsigned char octet)
        {
            unsigned char res;
            int i;

            res = 0;
            i = 0;
            while (i < 8)
            {
                res = (res << 1) | (octet & 1);
                octet = octet >> 1;
                i++;
            }
            return (res);
        }
        """),
        "cases": [[38], [170], [0], [255], [1], [128]],
    },
    "repeat_alpha": {
        "level": 1, "function": "repeat_alpha", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": ("The repeat count is the letter's 1-based alphabet "
                "position ('a' -> 1, 'b' -> 2, ...) — using the raw "
                "c - 'a' value (0-based) makes 'a' repeat zero times "
                "instead of once."),
        "subject": _sub_c("repeat_alpha", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays it, repeating
        each alphabetical character as many times as its alphabetical
        index ('a' -> 'a', 'b' -> 'bb', 'e' -> 'eeeee', ...). Case and
        non-letters are unaffected. Followed by a newline. If argc != 2,
        just a newline.

        Examples:
            ./repeat_alpha "abc"  -> abbccc
            ./repeat_alpha "Alex." -> Alllllllllllleeeeexxxxxxxxxxxxxxxxxxxxxxxx.
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        int main(int argc, char **argv)
        {
            int i;
            int j;
            int idx;
            char c;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'a' && c <= 'z')
                    idx = c - 'a' + 1;
                else if (c >= 'A' && c <= 'Z')
                    idx = c - 'A' + 1;
                else
                    idx = 0;
                if (idx == 0)
                    write(1, &c, 1);
                else
                {
                    j = 0;
                    while (j < idx)
                    {
                        write(1, &c, 1);
                        j++;
                    }
                }
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["Alex."], ["abacadaba 42!"], [], [""], ["a", "b"],
        ],
    },
    "fprime": {
        "level": 4, "function": "fprime", "kind": "program",
        "fuzz_argv": "positive_int",
        "standard": True,
        "hint": ("After the trial-division loop stops (once d*d > n), "
                "whatever's left in n still needs printing unless "
                "nothing was ever found — that single check handles "
                "both a leftover prime bigger than sqrt(the original n) "
                "and the n == 1 input, so don't only print factors from "
                "inside the while loop or primes (and 1) print nothing "
                "at all."),
        "subject": _sub_c("fprime", "int main(int argc, char **argv);",
                         "printf, atoi", """
        Write a PROGRAM that takes a positive int and displays its prime
        factors on standard output, followed by a newline. Factors are in
        ascending order, separated by '*' (so the printed expression
        equals the input). If argc != 2, just a newline.

        Examples:
            ./fprime 225225 -> 3*3*5*5*7*11*13
            ./fprime 42     -> 2*3*7
            ./fprime 1      -> 1
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdio.h>
        #include <stdlib.h>

        int main(int argc, char **argv)
        {
            long n;
            long d;
            int first;

            if (argc != 2)
            {
                printf("\\n");
                return (0);
            }
            n = atol(argv[1]);
            first = 1;
            d = 2;
            while (d * d <= n)
            {
                while (n % d == 0)
                {
                    if (!first)
                        printf("*");
                    printf("%ld", d);
                    first = 0;
                    n /= d;
                }
                d++;
            }
            if (n > 1 || first)
            {
                if (!first)
                    printf("*");
                printf("%ld", n);
            }
            printf("\\n");
            return (0);
        }
        """),
        "cases": [
            ["225225"], ["42"], ["9539"], ["1"], [], ["42", "21"],
            ["804577"], ["8333325"],
        ],
    },
    "ft_itoa": {
        "level": 4, "function": "ft_itoa",
        "standard": True,
        "prototype": "char *ft_itoa(int nbr);",
        "args": ["int"], "returns": "str_owned",
        "hint": ("INT_MIN is the nasty edge case: you can't fix its "
                "sign by negating it (that overflows int, since "
                "2147483648 doesn't fit), and it needs an 11-character "
                "buffer plus the null terminator, one more than any "
                "other int."),
        "subject": _sub_c("ft_itoa", "char *ft_itoa(int nbr);", "malloc", """
        Write a function that converts an int into a null-terminated,
        malloc'd string.

        Examples:
            ft_itoa(42)  -> "42"
            ft_itoa(-42) -> "-42"
            ft_itoa(0)   -> "0"
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>

        char *ft_itoa(int nbr)
        {
            char buf[12];
            int i;
            long n;
            int neg;
            char *res;

            i = 11;
            buf[i] = '\\0';
            n = nbr;
            neg = (n < 0);
            if (neg)
                n = -n;
            if (n == 0)
                buf[--i] = '0';
            while (n > 0)
            {
                buf[--i] = (char)('0' + n % 10);
                n /= 10;
            }
            if (neg)
                buf[--i] = '-';
            res = malloc(sizeof(char) * (12 - i));
            if (!res)
                return (0);
            n = 0;
            while (buf[i])
            {
                res[n] = buf[i];
                n++;
                i++;
            }
            res[n] = '\\0';
            return (res);
        }
        """),
        "cases": [[0], [42], [-42], [2147483647], [-2147483648], [7]],
    },
    "rev_wstr": {
        "level": 4, "function": "rev_wstr", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": {
            "crash": ("If you malloc a buffer per extracted word, its "
                     "size has to include room for the null terminator "
                     "(word length + 1) — sizing it to exactly the "
                     "word's length overflows the buffer the moment you "
                     "write that terminator."),
            "leak": ("You end up mallocing one buffer per word as you "
                     "walk backward through the string — free each one "
                     "once you've written it out, or a multi-word input "
                     "leaks once per extra word instead of just once."),
            "default": ("Walk from the END of the string extracting "
                        "words in reverse order, and print a separating "
                        "space before every word EXCEPT the very first "
                        "one you output — unconditionally printing a "
                        "leading space before each word leaves a stray "
                        "space at the front of the result."),
        },
        "subject": _sub_c("rev_wstr", "int main(int argc, char **argv);",
                         "write, malloc, free", """
        Write a PROGRAM that takes a string with words separated by
        single spaces (no leading/trailing spaces) and displays its
        words in REVERSE order, single-space separated, followed by a
        newline. If argc != 2, just a newline.

        Examples:
            ./rev_wstr "one two three" -> three two one
            ./rev_wstr "single"         -> single
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int len;
            int end;
            int start;
            int i;
            int first;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            len = 0;
            while (argv[1][len])
                len++;
            end = len;
            first = 1;
            while (end > 0)
            {
                while (end > 0 && is_sep(argv[1][end - 1]))
                    end--;
                if (end == 0)
                    break ;
                start = end;
                while (start > 0 && !is_sep(argv[1][start - 1]))
                    start--;
                if (!first)
                    write(1, " ", 1);
                i = start;
                while (i < end)
                {
                    write(1, &argv[1][i], 1);
                    i++;
                }
                first = 0;
                end = start;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["one two three"], ["hello world"], ["single"], [""], [],
            ["a", "b"],
        ],
    },
    "rostring": {
        "level": 4, "function": "rostring", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": True,
        "hint": {
            "crash": ("If you malloc a buffer to save the first word "
                     "before printing the rest, size it for that word's "
                     "length plus one for the null terminator — off by "
                     "one there corrupts the heap as soon as you write "
                     "the terminating byte."),
            "leak": ("Free whatever you malloc'd to hold the saved "
                     "first word once you're done printing it at the "
                     "end — it's easy to allocate it, use it, and then "
                     "just fall through to return without freeing it."),
            "default": ("Save where the FIRST word ends before you "
                        "print anything else, so you can still print "
                        "that same word again at the very end — and a "
                        "single-word input (no other words to rotate "
                        "ahead of it) should come out completely "
                        "unchanged, not with a stray trailing space."),
        },
        "subject": _sub_c("rostring", "int main(int argc, char **argv);",
                         "write, malloc, free", """
        Write a PROGRAM that takes a string and displays it rotated one
        word to the left: the first word moves to the end, the rest keep
        their order, single-space separated, followed by a newline. If
        argc != 2, just a newline.

        Examples:
            ./rostring "one two three" -> two three one
            ./rostring "single"         -> single
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int len;
            int i;
            int first_end;
            int j;
            int printed;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            len = 0;
            while (argv[1][len])
                len++;
            i = 0;
            while (i < len && is_sep(argv[1][i]))
                i++;
            if (i == len)
            {
                write(1, "\\n", 1);
                return (0);
            }
            first_end = i;
            while (first_end < len && !is_sep(argv[1][first_end]))
                first_end++;
            j = first_end;
            printed = 0;
            while (j < len)
            {
                while (j < len && is_sep(argv[1][j]))
                    j++;
                if (j >= len)
                    break ;
                if (printed)
                    write(1, " ", 1);
                while (j < len && !is_sep(argv[1][j]))
                {
                    write(1, &argv[1][j], 1);
                    j++;
                }
                printed = 1;
            }
            if (printed)
                write(1, " ", 1);
            j = i;
            while (j < first_end)
            {
                write(1, &argv[1][j], 1);
                j++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["one two three"], ["hello world"], ["single"], [""], [],
            ["a", "b"],
        ],
    },
    "ft_list_foreach": {
        "level": 4, "function": "ft_list_foreach",
        "standard": True,
        "prototype": "void ft_list_foreach(t_list *begin_list, void (*f)(void *));",
        "args": ["voidlist", "cb_accumulate"], "returns": "foreach_sum",
        "hint": ("Call the callback as (*f)(begin_list->data) — pass the "
                "node's data, not the node itself — and make sure you "
                "advance to begin_list->next every iteration, or you'll "
                "spin on the first node forever instead of stopping at "
                "NULL."),
        "subject": _sub_c("ft_list_foreach",
                         "void ft_list_foreach(t_list *begin_list, "
                         "void (*f)(void *));", "None", """
        Write a function that walks a linked list and applies a function
        pointer `f` to each element's data, calling it as `(*f)(node->data)`.
        You must use the t_list type described in ft_list.h (provided):
        a node holds a `void *data` and a `next` pointer.

        The tester checks this by summing every element's (int) value
        through your traversal — a correct foreach visits every node
        exactly once, in order.

        Examples:
            ft_list_foreach([1,2,3], f) -> f is called with 1, then 2, then 3
        """),
        "oracle_c": textwrap.dedent("""
        #include "ft_list.h"

        void ft_list_foreach(t_list *begin_list, void (*f)(void *))
        {
            while (begin_list)
            {
                (*f)(begin_list->data);
                begin_list = begin_list->next;
            }
        }
        """),
        "cases": [[[1, 2, 3]], [[]], [[5]], [[10, -5, 3, 7]], [[0, 0, 0]]],
    },
    "ft_list_remove_if": {
        "level": 4, "function": "ft_list_remove_if",
        "standard": True,
        "prototype": "void ft_list_remove_if(t_list **begin_list, "
                     "void *data_ref, int (*cmp)(void *, void *));",
        "hint": {
            "crash": ("If the FIRST node matches, you need to rebind "
                     "*begin_list itself, not just a 'prev' pointer "
                     "inside the loop — leaving *begin_list pointing at "
                     "freed memory is what causes the crash."),
            "leak": ("Don't forget to free the removed node itself (and "
                     "its data, if you own it) — since every call "
                     "removes at least one node, a missing free here "
                     "shows up as a leak on nearly every test case."),
            "default": ("If the FIRST node matches, you need to rebind "
                        "*begin_list itself, not just a 'prev' pointer "
                        "inside the loop — and don't forget to free the "
                        "removed node (and its data)."),
        },
        "args": ["voidlist_ptr", "int_ptr", "cmp_eq_ints"],
        "returns": "void", "print_after_args": [0],
        "subject": _sub_c("ft_list_remove_if",
                         "void ft_list_remove_if(t_list **begin_list, "
                         "void *data_ref, int (*cmp)(void *, void *));", "free", """
        Write a function that removes every element of the list whose
        data is "equal" to `data_ref`, per `cmp` (which returns 0 when its
        two void* arguments are equal). You must use the t_list type
        described in ft_list.h (provided).

        Examples:
            ft_list_remove_if([1,2,3,2,1], &2, cmp) -> list becomes [1,3,1]
            ft_list_remove_if([5,5,5], &5, cmp)      -> list becomes []
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdlib.h>
        #include "ft_list.h"

        void ft_list_remove_if(t_list **begin_list, void *data_ref,
                               int (*cmp)(void *, void *))
        {
            t_list *cur;
            t_list *prev;
            t_list *tmp;

            cur = *begin_list;
            prev = NULL;
            while (cur)
            {
                if (cmp(cur->data, data_ref) == 0)
                {
                    tmp = cur;
                    if (prev)
                        prev->next = cur->next;
                    else
                        *begin_list = cur->next;
                    cur = cur->next;
                    free(tmp->data);
                    free(tmp);
                }
                else
                {
                    prev = cur;
                    cur = cur->next;
                }
            }
        }
        """),
        "cases": [
            [[1, 2, 3, 2, 1], 2], [[5, 5, 5], 5], [[1, 2, 3], 9],
            [[], 4], [[7], 7],
        ],
    },
    "flood_fill": {
        "level": 4, "function": "flood_fill",
        "standard": True,
        "prototype": "void flood_fill(char **tab, t_point size, "
                     "t_point begin);",
        "args": ["char_grid", "point", "point"], "returns": "void",
        "print_after_args": [0],
        "hint": {
            "crash": ("Before recursing into a neighbour, check both "
                     "that it's still inside the grid AND that it still "
                     "holds the ORIGINAL character — without that second "
                     "check you'll recurse back into cells you already "
                     "turned into 'F', which blows the stack."),
            "default": ("Remember t_point is {x, y} with x = width and "
                        "y = height — indexing the grid as tab[x][y] "
                        "instead of tab[y][x], or mixing up which loop "
                        "bound is width vs. height, gives you a subtly "
                        "wrong fill rather than a crash, especially on "
                        "a non-square grid."),
        },
        "subject": _sub_c("flood_fill",
                         "void flood_fill(char **tab, t_point size, "
                         "t_point begin);", "None", """
        Write a function that takes a 2D character grid, its dimensions
        as a t_point (x = width, y = height), and a starting point.
        Starting from `begin`, it fills the whole connected zone of
        identical characters (up/down/left/right only, never diagonally)
        by replacing them with 'F'. You must use the t_point type
        described in flood_fill.h (provided): `{ int x; int y; }`.

        Examples:
            flood_fill(["111","101","111"], {3,3}, {0,0})
                -> ["FFF","F0F","FFF"]   # the outer ring of 1s gets filled
        """),
        "oracle_c": textwrap.dedent("""
        #include "flood_fill.h"

        static void fill(char **tab, t_point size, t_point p, char target)
        {
            if (p.x < 0 || p.x >= size.x || p.y < 0 || p.y >= size.y)
                return ;
            if (tab[p.y][p.x] != target)
                return ;
            tab[p.y][p.x] = 'F';
            fill(tab, size, (t_point){p.x + 1, p.y}, target);
            fill(tab, size, (t_point){p.x - 1, p.y}, target);
            fill(tab, size, (t_point){p.x, p.y + 1}, target);
            fill(tab, size, (t_point){p.x, p.y - 1}, target);
        }

        void flood_fill(char **tab, t_point size, t_point begin)
        {
            char target;

            if (begin.x < 0 || begin.x >= size.x
                || begin.y < 0 || begin.y >= size.y)
                return ;
            target = tab[begin.y][begin.x];
            if (target == 'F')
                return ;
            fill(tab, size, begin, target);
        }
        """),
        "cases": [
            [["111", "101", "111"], (3, 3), (0, 0)],
            [["0011", "0011"], (4, 2), (0, 0)],
            [["0011", "0011"], (4, 2), (3, 1)],
            [["5"], (1, 1), (0, 0)],
            [["F00", "000", "000"], (3, 3), (0, 0)],
            [["111"], (3, 1), (5, 5)],
        ],
    },

    # ── EXTRA (practice only — never drawn by `make c-exam`) ────
    "count_vowels": {
        "level": 1, "function": "count_vowels", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": False,
        "hint": ("Only a, e, i, o, u count as vowels (not 'y') — "
                "normalize the character's case before comparing (or "
                "compare against both cases) so 'A' and 'a' are both "
                "counted correctly."),
        "subject": _sub_c("count_vowels", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays how many vowels
        (a, e, i, o, u, case-insensitive) it contains, followed by a
        newline. If argc != 2, just a newline.

        Examples:
            ./count_vowels "hello"  -> 2
            ./count_vowels "AEIOU"  -> 5
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_vowel(char c)
        {
            if (c >= 'A' && c <= 'Z')
                c = c - 'A' + 'a';
            return (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u');
        }

        static void put_nbr(int n)
        {
            char digit;

            if (n >= 10)
                put_nbr(n / 10);
            digit = '0' + n % 10;
            write(1, &digit, 1);
        }

        int main(int argc, char **argv)
        {
            int i;
            int count;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            count = 0;
            while (argv[1][i])
            {
                if (is_vowel(argv[1][i]))
                    count++;
                i++;
            }
            put_nbr(count);
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["hello"], ["AEIOUaeiou"], [""], [], ["xyz"],
            ["The Quick Brown Fox"], ["bcdfg"], ["y"], ["1234!?"],
            ["a", "b"],
        ],
    },
    "is_palindrome_str": {
        "level": 2, "function": "is_palindrome_str", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": False,
        "hint": ("A string with zero letters must print 'no', not "
                "'yes' — your two-pointer scan trivially finishes "
                "without ever finding a mismatch on an all-punctuation "
                "input, so you need an explicit 'did I see at least one "
                "letter' check before declaring a match."),
        "subject": _sub_c("is_palindrome_str",
                         "int main(int argc, char **argv);", "write", """
        Write a PROGRAM that takes a string and displays "yes" if it is a
        palindrome, "no" otherwise, followed by a newline. Only letters
        are compared, case-insensitively; everything else (spaces,
        digits, punctuation) is ignored. A string with no letters at all
        is not a palindrome. If argc != 2, just a newline.

        Examples:
            ./is_palindrome_str "racecar"                     -> yes
            ./is_palindrome_str "A man a plan a canal Panama"  -> yes
            ./is_palindrome_str "hello"                        -> no
            ./is_palindrome_str "12 21"                        -> no
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_alpha(char c)
        {
            return ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'));
        }

        static char to_lower(char c)
        {
            if (c >= 'A' && c <= 'Z')
                return (c - 'A' + 'a');
            return (c);
        }

        int main(int argc, char **argv)
        {
            int i;
            int left;
            int right;
            int len;
            int has_alpha;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            len = 0;
            while (argv[1][len])
                len++;
            has_alpha = 0;
            i = 0;
            while (i < len)
            {
                if (is_alpha(argv[1][i]))
                    has_alpha = 1;
                i++;
            }
            if (!has_alpha)
            {
                write(1, "no\\n", 3);
                return (0);
            }
            left = 0;
            right = len - 1;
            while (left < right)
            {
                while (left < right && !is_alpha(argv[1][left]))
                    left++;
                while (left < right && !is_alpha(argv[1][right]))
                    right--;
                if (to_lower(argv[1][left]) != to_lower(argv[1][right]))
                {
                    write(1, "no\\n", 3);
                    return (0);
                }
                left++;
                right--;
            }
            write(1, "yes\\n", 4);
            return (0);
        }
        """),
        "cases": [
            ["racecar"], ["A man a plan a canal Panama"], ["hello"],
            ["12 21"], [""], [], ["a"], ["ab"], ["Aa"], ["!!!"],
            ["race a car"], ["Was it a car or a cat I saw"], ["a", "b"],
        ],
    },
    "longest_word_str": {
        "level": 3, "function": "longest_word_str", "kind": "program",
        "fuzz_argv": "sentence",
        "standard": False,
        "hint": ("On a tie, the FIRST longest word wins — that means "
                "your comparison has to be strictly greater-than "
                "(replace only when a word is longer, never when equal), "
                "not greater-than-or-equal."),
        "subject": _sub_c("longest_word_str",
                         "int main(int argc, char **argv);", "write", """
        Write a PROGRAM that takes a string and displays its longest
        space/tab-delimited word, followed by a newline. On a tie, the
        first one wins. No words (empty or all-whitespace input): just a
        newline. If argc != 2, just a newline.

        Examples:
            ./longest_word_str "the quick brown fox" -> quick
            ./longest_word_str "a bb ccc dd"          -> ccc
        """),
        "oracle_c": textwrap.dedent("""
        #include <unistd.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int i;
            int start;
            int len;
            int best_start;
            int best_len;

            if (argc != 2)
            {
                write(1, "\\n", 1);
                return (0);
            }
            i = 0;
            best_start = 0;
            best_len = 0;
            while (argv[1][i])
            {
                while (argv[1][i] && is_sep(argv[1][i]))
                    i++;
                start = i;
                len = 0;
                while (argv[1][i] && !is_sep(argv[1][i]))
                {
                    len++;
                    i++;
                }
                if (len > best_len)
                {
                    best_len = len;
                    best_start = start;
                }
            }
            i = 0;
            while (i < best_len)
            {
                write(1, &argv[1][best_start + i], 1);
                i++;
            }
            write(1, "\\n", 1);
            return (0);
        }
        """),
        "cases": [
            ["the quick brown fox"], ["a bb ccc dd"], [""], ["   "], [],
            ["single"], ["tie tie2 abcd"], ["  lorem   ipsum  dolor  "],
            ["a", "b"],
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
        raise ValueError("c_exam.bank: %s has level %r, expected 1..%d"
                         % (_name, _lvl, N_LEVELS))
    LEVELS[_lvl].append(_name)
    _ex.setdefault("args", [])
    _ex.setdefault("kind", "function")
    _ex.setdefault("standard", False)

for _lvl, _pool in LEVELS.items():
    if not _pool:
        raise ValueError("c_exam.bank: level %d has no exercise" % _lvl)

# The real, documented subjects — `make c-exam` draws only from this pool,
# same split as the Python bank's Standard/Extra (see module docstring).
# The invented "Extra" exercises stay reachable through practice mode only.
STANDARD_LEVELS = {lvl: [name for name in pool if EXERCISES[name]["standard"]]
                   for lvl, pool in LEVELS.items()}

for _lvl, _pool in STANDARD_LEVELS.items():
    if not _pool:
        raise ValueError("c_exam.bank: level %d has no standard exercise" % _lvl)
