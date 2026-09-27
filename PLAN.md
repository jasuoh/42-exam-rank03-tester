# PLAN — ExamShell 1.0: Vollbild-Terminal-App (TUI)

Branch: `claude/dreamy-bohr-q3sw4d` · Stand: 2026-09-27 · Vorgänger: 0.2.0 (#4)

Ziel: aus dem zeilenbasierten Tester eine **Vollbild-Terminal-App** machen —
Aufgabe und Ergebnisse nebeneinander, Live-Grading beim Speichern,
Exam-Fortschritt und Countdown immer sichtbar, Readiness als Heatmap,
Stats mit Verlauf. Die heutige Oberfläche bleibt als Fallback erhalten.

```
┌─ ExamShell · Rank 02 · alice ──────────────── Level 2/4 ── ⏱ 02:41:07 ─┐
│ ● ● ◐ ○   first_word ✔ · inter …                                        │
├─ Subject: inter ─────────────────────┬─ grademe (watching inter.c) ────┤
│ Assignment name : inter              │ ✔ padinton / paqefwt…    padinto│
│ Expected files  : inter.c            │ ✖ ./inter "aaa" "a"             │
│ Allowed functions: write             │   edge case: repeated chars     │
│ Write a program that takes two …     │ ████████████░░░░  7/10   70%    │
├──────────────────────────────────────┴─────────────────────────────────┤
│ [g] grademe  [s] subject  [h] hint  [r] readiness  [q] quit            │
└────────────────────────────────────────────────────────────────────────┘
```

## Rahmenbedingungen

- **TUI-Bibliothek: Textual** (baut auf `rich` auf, das schon optional genutzt
  wird). Aktuelle Textual-Version (8.x) braucht **Python ≥ 3.9**.
- **Der Kern bleibt Python 3.8 + null Abhängigkeiten.** Die TUI ist ein
  optionaler Aufsatz: ist Textual nicht installiert (oder Python 3.8), startet
  automatisch die heutige Oberfläche. Kein Feature geht verloren.
- Jede Phase ist ein eigener, lauffähiger PR/Release.

---

## Phase A — Engine von Anzeige trennen (0.3.0) · *dieser PR*

Heute: `src/examshell.py` und `c_exam/examshell.py` enthalten **je** den
kompletten Ablauf (Exam, Practice, Training, Readiness, Drill, Menü) —
~900 identische Zeilen, und Logik und `print`/`input` sind verwoben. Eine
TUI kann darauf nicht aufsetzen.

1. **`src/shell_common.py`** — der gemeinsame Ablauf, einmal. Die beiden
   Shells liefern nur noch ihre Unterschiede (Bank, Grader-Aufruf, Stubs,
   CLI-Flags, Menüpunkte) als „Hooks“.
2. **`ExamRun`** — das Exam als reiner Zustand (Level, Aufgabe, Versuche,
   Uhr, RNGs, Speichern/Fortsetzen, Zeitlimit) ohne jede Ein-/Ausgabe. Die
   heutige Oberfläche und später die TUI steuern beide dasselbe `ExamRun`.
3. **`grade()` ohne Anzeige** — bewertet, zeichnet Stats auf und liefert
   Report, neue Badges und Hinweis als Daten zurück; die Anzeige macht der
   Aufrufer.

Verhalten bleibt identisch — alle bestehenden Tests müssen unverändert grün
bleiben (plus neue Tests für `ExamRun`/`grade()`).

**~−600 / +700 Zeilen · ~1,5 Tage**

## Phase B — App-Gerüst (0.4.0)

`make tui` / `python3 -m src --tui` (später Default, wenn Textual da ist):
Screens für Menü, Practice-Liste mit Suche, Training, Readiness, Stats;
Tastaturkürzel, die drei Themes, Fallback-Erkennung.

**~1.200 Zeilen · ~2 Tage**

## Phase C — Exam-Screen (0.5.0)

Split-View Aufgabe | Ergebnisse, Ergebnisse laufen live ein, **Watch-Modus**
(grademe beim Speichern, im Practice), Level-Stepper, Countdown, Blind-Grading
im Exam, Level-geschafft-/Badge-Animationen.

**~800 Zeilen · ~1,5 Tage**

## Phase D — Feinschliff → 1.0.0

Readiness-Heatmap, Stats-Verlaufsdiagramme, Exam-Historie, TUI-Tests
(Textual „Pilot“), animierte GIFs fürs README (aufgenommen mit `vhs`),
Doku.

**~600 Zeilen · ~1 Tag**

---

## Danach (1.1)

- **Lokales Web-Dashboard** (`make dashboard` → `localhost:4242`): Heatmap,
  Diagramme, Exam-Historie im Browser.
- `pipx install`-bar (Paket `src` umbenennen).

## Risiken

- Textual auf Schulrechnern nicht installierbar → Fallback ist Pflicht und
  wird in CI mit *und* ohne Textual getestet.
- Textual-API ändert sich zwischen Major-Versionen → Version in
  `requirements` nach oben begrenzen.
