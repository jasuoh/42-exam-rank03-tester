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

Every exercise here mirrors a real, publicly documented Exam Rank 02
subject (names, prototypes and behaviour cross-checked against several
independent public exam-prep repositories) — the exact pool and level
placement still varies by campus/date, same caveat as the Python bank's
"Extra" pool, but these are not invented subjects.

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
        "prototype": "void ft_putstr(char *str);",
        "args": ["str"], "returns": "void",
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
        "prototype": "void ft_swap(int *a, int *b);",
        "args": ["int_ptr", "int_ptr"], "returns": "void",
        "print_after_args": [0, 1],
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                printf("\\n");
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
                printf("%c", c);
                i++;
            }
            printf("\\n");
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
        #include <stdio.h>

        int main(void)
        {
            int i;

            i = 1;
            while (i <= 100)
            {
                if (i % 15 == 0)
                    printf("fizzbuzz\\n");
                else if (i % 3 == 0)
                    printf("fizz\\n");
                else if (i % 5 == 0)
                    printf("buzz\\n");
                else
                    printf("%d\\n", i);
                i++;
            }
            return (0);
        }
        """),
        "cases": [[]],
    },
    "first_word": {
        "level": 1, "function": "first_word", "kind": "program",
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
        #include <stdio.h>

        static int is_sep(char c)
        {
            return (c == ' ' || c == '\\t');
        }

        int main(int argc, char **argv)
        {
            int i;

            if (argc != 2)
            {
                printf("\\n");
                return (0);
            }
            i = 0;
            while (argv[1][i] && is_sep(argv[1][i]))
                i++;
            while (argv[1][i] && !is_sep(argv[1][i]))
            {
                printf("%c", argv[1][i]);
                i++;
            }
            printf("\\n");
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
        "prototype": "char *ft_strcpy(char *s1, char *s2);",
        "args": ["buf", "str"], "returns": "str", "forbidden": ["strcpy"],
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
        "prototype": "int ft_strlen(char *str);",
        "args": ["str"], "returns": "int", "forbidden": ["strlen"],
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
        "subject": _sub_c("rev_print", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a string and displays it reversed,
        followed by a newline. If argc != 2, just a newline.

        Examples:
            ./rev_print "abc"         -> cba
            ./rev_print "hello world" -> dlrow olleh
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;

            if (argc != 2)
            {
                printf("\\n");
                return (0);
            }
            i = 0;
            while (argv[1][i])
                i++;
            while (i > 0)
            {
                i--;
                printf("%c", argv[1][i]);
            }
            printf("\\n");
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["hello world"], [""], [], ["a", "b"], ["racecar"],
        ],
    },
    "search_and_replace": {
        "level": 1, "function": "search_and_replace", "kind": "program",
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            char from;
            char to;

            if (argc != 4)
            {
                printf("\\n");
                return (0);
            }
            from = argv[2][0];
            to = argv[3][0];
            i = 0;
            while (argv[1][i])
            {
                if (argv[1][i] == from)
                    printf("%c", to);
                else
                    printf("%c", argv[1][i]);
                i++;
            }
            printf("\\n");
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                printf("\\n");
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
                printf("%c", c);
                i++;
            }
            printf("\\n");
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
        "prototype": "int ft_atoi(const char *str);",
        "args": ["str"], "returns": "int", "forbidden": ["atoi"],
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
        "prototype": "int is_power_of_2(unsigned int n);",
        "args": ["int"], "returns": "int",
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
        "prototype": "int max(int *tab, unsigned int len);",
        "args": ["int_arr"], "returns": "int",
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                printf("\\n");
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
                printf("%c", c);
                i++;
            }
            printf("\\n");
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                printf("\\n");
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
                printf("%c", c);
                i++;
            }
            printf("\\n");
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["My Test String."], [""], [], ["a", "b"], ["Hello"],
        ],
    },
    "camel_to_snake": {
        "level": 2, "function": "camel_to_snake", "kind": "program",
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            char c;

            if (argc != 2)
            {
                printf("\\n");
                return (0);
            }
            i = 0;
            while (argv[1][i])
            {
                c = argv[1][i];
                if (c >= 'A' && c <= 'Z')
                {
                    printf("_");
                    printf("%c", c - 'A' + 'a');
                }
                else
                    printf("%c", c);
                i++;
            }
            printf("\\n");
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
        "prototype": "int ft_strcmp(char *s1, char *s2);",
        "args": ["str", "str"], "returns": "strcmp_sign",
        "forbidden": ["strcmp"],
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
        "prototype": "size_t ft_strcspn(const char *s, const char *reject);",
        "args": ["str", "str"], "returns": "int", "forbidden": ["strcspn"],
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
        "prototype": "char *ft_strdup(char *src);",
        "args": ["str"], "returns": "str_owned", "forbidden": ["strdup"],
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
        "prototype": "char *ft_strpbrk(const char *s1, const char *s2);",
        "args": ["str", "str"], "returns": "str", "forbidden": ["strpbrk"],
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
        "prototype": "char *ft_strrev(char *str);",
        "args": ["buf"], "returns": "str",
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
        "prototype": "size_t ft_strspn(const char *s, const char *accept);",
        "args": ["str", "str"], "returns": "int", "forbidden": ["strspn"],
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
        #include <stdio.h>

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
                printf("\\n");
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
                printf("%c", argv[1][start]);
                start++;
            }
            printf("\\n");
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
        "prototype": "void print_bits(unsigned char octet);",
        "args": ["int"], "returns": "void",
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            int upnext;
            char c;

            if (argc != 2)
            {
                printf("\\n");
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
                    printf("%c", c);
                    upnext = 0;
                }
                i++;
            }
            printf("\\n");
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
        "prototype": "unsigned char swap_bits(unsigned char octet);",
        "args": ["int"], "returns": "int",
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
    "union": {
        "level": 2, "function": "union", "kind": "program",
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
        #include <stdio.h>

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
                printf("\\n");
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
                printf("%c", buf[i]);
                i++;
            }
            printf("\\n");
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            int j;

            if (argc != 3)
            {
                printf("\\n");
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
                printf("%s\\n", argv[1]);
            else
                printf("\\n");
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
        #include <stdio.h>

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
                printf("\\n");
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
                    printf(" ");
                    need_space = 0;
                }
                printf("%c", argv[1][i]);
                i++;
            }
            printf("\\n");
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
        #include <stdio.h>

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
                printf("\\n");
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
                    printf("   ");
                    need_space = 0;
                }
                printf("%c", argv[1][i]);
                i++;
            }
            printf("\\n");
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
        "prototype": "int ft_atoi_base(const char *str, int str_base);",
        "args": ["str", "int"], "returns": "int",
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
        "prototype": "int *ft_range(int start, int end);",
        "args": ["int", "int"], "returns": "int_arr",
        "return_len": lambda a: abs(a[1] - a[0]) + 1,
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
        "prototype": "int *ft_rrange(int start, int end);",
        "args": ["int", "int"], "returns": "int_arr",
        "return_len": lambda a: abs(a[1] - a[0]) + 1,
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
        "subject": _sub_c("paramsum", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that displays the number of arguments passed to
        it, followed by a newline. No arguments displays 0.

        Examples:
            ./paramsum a b c -> 3
            ./paramsum        -> 0
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            (void)argv;
            printf("%d\\n", argc - 1);
            return (0);
        }
        """),
        "cases": [["1", "2", "3"], [], ["a"], ["a", "b", "c", "d", "e"]],
    },
    "print_hex": {
        "level": 3, "function": "print_hex", "kind": "program",
        "forbidden": ["atoi"],
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
        #include <stdio.h>
        #include <stdlib.h>

        int main(int argc, char **argv)
        {
            long n;
            char buf[32];
            int i;

            if (argc != 2)
            {
                printf("\\n");
                return (0);
            }
            n = atol(argv[1]);
            if (n == 0)
            {
                printf("0\\n");
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
                printf("%c", buf[i]);
            }
            printf("\\n");
            return (0);
        }
        """),
        "cases": [["10"], ["255"], ["0"], ["16"], [], ["4096"]],
    },
    "rstr_capitalizer": {
        "level": 3, "function": "rstr_capitalizer", "kind": "program",
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
        #include <stdio.h>

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
                printf("%c", c);
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
                printf("\\n");
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
                        printf("%c", argv[a][i]);
                        i++;
                    }
                }
                printf("\\n");
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
        #include <stdio.h>

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
                printf("\\n");
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
                    printf("%c", c);
                    i++;
                }
                printf("\\n");
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
        "forbidden": ["atoi"],
        "subject": _sub_c("tab_mult", "int main(int argc, char **argv);",
                         "write", """
        Write a PROGRAM that takes a strictly positive int and displays
        its multiplication table from 1x to 9x, one line each, formatted
        as "i x n = i*n". No arguments: just a newline.

        Examples:
            ./tab_mult 9 -> 1 x 9 = 9 ... 9 x 9 = 81 (9 lines)
        """),
        "oracle_c": textwrap.dedent("""
        #include <stdio.h>
        #include <stdlib.h>

        int main(int argc, char **argv)
        {
            int n;
            int i;

            if (argc != 2)
            {
                printf("\\n");
                return (0);
            }
            n = atoi(argv[1]);
            i = 1;
            while (i <= 9)
            {
                printf("%d x %d = %d\\n", i, n, i * n);
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
        "prototype": "char **ft_split(char *str);",
        "args": ["str"], "returns": "str_array", "forbidden": ["malloc"],
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

            n = count_words(str);
            res = malloc(sizeof(char *) * (n + 1));
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
        "prototype": "int ft_list_size(t_list *begin_list);",
        "args": ["int_list"], "returns": "int",
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            int j;

            if (argc != 3)
            {
                printf("\\n");
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
            printf("%d\\n", argv[1][i] == '\\0');
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
        "forbidden": ["atoi"],
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
        "prototype": "unsigned int lcm(unsigned int a, unsigned int b);",
        "args": ["int", "int"], "returns": "int",
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
        "forbidden": ["atoi"],
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
        #include <stdio.h>
        #include <stdlib.h>

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

        int main(int argc, char **argv)
        {
            int n;
            int i;
            long sum;

            if (argc != 2 || atoi(argv[1]) <= 0)
            {
                printf("0\\n");
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
            printf("%ld\\n", sum);
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
        "prototype": "t_list *sort_list(t_list *lst, int (*cmp)(int, int));",
        "args": ["int_list", "cmp_ascending"], "returns": "int_list",
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
        "prototype": "void sort_int_tab(int *tab, unsigned int size);",
        "args": ["int_arr"], "returns": "void", "print_after_args": [0],
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
        "prototype": "unsigned char reverse_bits(unsigned char octet);",
        "args": ["int"], "returns": "int",
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
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            int i;
            int j;
            int idx;
            char c;

            if (argc != 2)
            {
                printf("\\n");
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
                    printf("%c", c);
                else
                {
                    j = 0;
                    while (j < idx)
                    {
                        printf("%c", c);
                        j++;
                    }
                }
                i++;
            }
            printf("\\n");
            return (0);
        }
        """),
        "cases": [
            ["abc"], ["Alex."], ["abacadaba 42!"], [], [""], ["a", "b"],
        ],
    },
    "fprime": {
        "level": 4, "function": "fprime", "kind": "program",
        "forbidden": ["atoi"],
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
        "prototype": "char *ft_itoa(int nbr);",
        "args": ["int"], "returns": "str_owned",
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
        #include <stdio.h>

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
                printf("\\n");
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
                    printf(" ");
                i = start;
                while (i < end)
                {
                    printf("%c", argv[1][i]);
                    i++;
                }
                first = 0;
                end = start;
            }
            printf("\\n");
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
        #include <stdio.h>

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
                printf("\\n");
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
                printf("\\n");
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
                    printf(" ");
                while (j < len && !is_sep(argv[1][j]))
                {
                    printf("%c", argv[1][j]);
                    j++;
                }
                printed = 1;
            }
            if (printed)
                printf(" ");
            j = i;
            while (j < first_end)
            {
                printf("%c", argv[1][j]);
                j++;
            }
            printf("\\n");
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
        "prototype": "void ft_list_foreach(t_list *begin_list, void (*f)(void *));",
        "args": ["voidlist", "cb_accumulate"], "returns": "foreach_sum",
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
        "prototype": "void ft_list_remove_if(t_list **begin_list, "
                     "void *data_ref, int (*cmp)());",
        "args": ["voidlist_ptr", "int_ptr", "cmp_eq_ints"],
        "returns": "void", "print_after_args": [0],
        "subject": _sub_c("ft_list_remove_if",
                         "void ft_list_remove_if(t_list **begin_list, "
                         "void *data_ref, int (*cmp)());", "free", """
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
                               int (*cmp)())
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
        "prototype": "void flood_fill(char **tab, t_point size, "
                     "t_point begin);",
        "args": ["char_grid", "point", "point"], "returns": "void",
        "print_after_args": [0],
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

for _lvl, _pool in LEVELS.items():
    if not _pool:
        raise ValueError("c_exam.bank: level %d has no exercise" % _lvl)
