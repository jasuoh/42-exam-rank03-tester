# PLAN — Bug-Check & Lernhilfen

Branch: `claude/dreamy-bohr-q3sw4d` · Stand: 2026-09-27

> **Status: vollständig umgesetzt in Version 0.2.0** (Phase 1 + H1–H6, dazu
> Versionierung/Releases und Update-Hinweis). Entscheidungen zu den offenen
> Fragen: realistischer Modus ist **Default** im Exam (`--relaxed` als
> Ausweg), Zeitlimit **nur per `--time-limit`**. Details: CHANGELOG.md.

Ziel: (1) den Tester auf Bugs prüfen und sie beheben, (2) danach Hilfsmittel
einbauen, die Leuten konkret helfen, die echten Exams zu bestehen.

---

## 0. Ausgangslage (Audit-Ergebnis)

| Check | Ergebnis |
|---|---|
| `make test` (Python-Tester, 344 Unit-Tests + Bank-Selbsttest) | **2 Fehlschläge** (siehe B1), Banken selbst ✔ |
| `make c-test` (C-Tester, Unit-Tests + Bank-Selbsttest) | ✔ |
| `python3 -m c_exam --check --valgrind` | ✔ alle Referenzlösungen leak-frei |
| `make lint` (ruff) | ✔ |

Gelesen/geprüft: `src/grader.py`, `src/examshell.py`, `src/stats.py`,
`src/session_store.py`, `src/settings.py`, `src/report_export.py`,
`src/hints.py`, `src/achievements.py`, `c_exam/grader.py`,
`c_exam/examshell.py` (Exam-Flow) + gezielte Verhaltens-Tests.

Grundsätzlich ist der Code in gutem Zustand — die Funde unten sind echte, aber
überschaubare Probleme.

---

## Phase 1 — Bugs beheben

### B1 · Zwei Tests schlagen fehl, wenn als root ausgeführt (Docker/CI-Container)
- `tests/test_shared.py` → `test_save_config_survives_unwritable_dir`,
  `test_write_report_survives_unwritable_dir`
- Die Tests nehmen an, `/this/does/not/exist/at/all` sei nicht beschreibbar.
  Als root wird das Verzeichnis **tatsächlich angelegt** → Test schlägt fehl
  **und** hinterlässt Müll im Dateisystem (`/this/...`).
- **Fix:** Pfad verwenden, der für *jeden* User unbeschreibbar ist — z. B. ein
  Unterpfad unter einer existierenden *Datei* (`<tmpfile>/sub`), dort schlägt
  `os.makedirs` immer mit `NotADirectoryError` fehl.

### B2 · `--seed` macht das Exam nicht wirklich reproduzierbar
- Das Exam druckt „seed N — this exam is reproducible“, aber `grademe`
  verbraucht Zufallszahlen aus **demselben** RNG (Fuzz-Tests). Dadurch hängt
  die Aufgabe in Level 2+ davon ab, wie oft man in Level 1 `grademe` getippt hat.
- Nachgewiesen: bei 19 von 50 Seeds ändert schon **ein** `grademe` die
  Level-2-Aufgabe.
- Betrifft `src/examshell.py` und `c_exam/examshell.py`.
- **Fix:** zwei getrennte RNGs — einer fürs Ziehen der Aufgaben, einer fürs
  Grading. Session-Save/Resume entsprechend anpassen (abwärtskompatibel mit
  alten Save-Files).

### B3 · C-Programm-Aufgaben: Endlosschleife blockiert den Grader ~30–65 s
- Bei `kind: "program"` läuft jeder Fall bis zum Timeout (5 s), ohne Abbruch —
  z. B. `rotone` mit `while(1);` → 30 s, `is_palindrome_str` (13 Fälle) → 65 s.
- Der Python-Grader bricht bereits nach 3 Timeouts in Folge ab
  (`MAX_TIMEOUTS`); der C-Grader nicht.
- **Fix:** gleiche Logik im C-Grader (`_grade_program`): nach 3 Timeouts in
  Folge restliche Fälle als „skipped after N timeouts“ markieren.

### B4 · Kleinkram
- `resolve_exercise()` (beide Tester): exakter Treffer `py_<name>` sollte
  Vorrang vor Suffix-Treffern haben (aktuell nur latent, noch keine Kollision
  in den Banken).
- Training-Modus: Warnmeldung bei ungültiger Eingabe erwähnt `w` (weak) nicht.

Jeder Fix bekommt einen Regressionstest. Danach `make test`, `make c-test`,
`make lint` grün.

---

## Phase 2 — Hilfsmittel, damit mehr Leute bestehen

Priorisiert nach erwartetem Nutzen. **Bitte auswählen/streichen**, bevor ich
anfange.

### H1 · „Realistischer Exam-Modus“ (hoher Nutzen) ⭐
Aktuell ist das Exam **gnädiger als das echte**: Compiler-Warnungen und
verbotene Funktionen geben nur eine Warnung, man kann mit `new` beliebig neu
ziehen, und es gibt kein Zeitlimit. Wer hier besteht, fällt im echten Exam
evtl. trotzdem durch (z. B. 100 % trotz `unused variable`-Warnung — echtes
Exam kompiliert mit `-Werror`).
- Im Exam-Modus standardmäßig: `--strict-norm` + `--strict-forbidden` (C),
  `--strict-imports` (Python).
- `new` im Exam-Modus deaktivieren (oder nur mit Opt-in-Flag).
- Optionales Zeitlimit mit Countdown in der Statuszeile (`--time-limit 3h`).
- Opt-out-Flag `--relaxed` für Anfänger.

### H2 · Fehlende Standard-Aufgabe `inter` (C, Level 2)
`inter` ist ein klassisches Rank-02-Level-2-Exercise und fehlt in der C-Bank
(`union`/`wdmatch` sind da). Hinzufügen inkl. Subject, Referenzlösung, Cases,
Hint.

### H3 · Edge-Case-Fuzzing für C-Programm-Aufgaben (hoher Nutzen)
Die 31 `program`-Aufgaben (rotone, epur_str, rostring, …) werden nur mit ~6
festen Fällen getestet, **ohne Fuzzing** — genau hier fallen Leute im echten
Exam durch (mehrere Leerzeichen/Tabs, leerer String, falsche Argumentanzahl).
- Pro Aufgabe (oder pro Aufgaben-Typ „ein String-Argument“, „zwei
  Argumente“, …) einen argv-Generator mit typischen Fallen.
- Aktivierung wie bei Function-Aufgaben über `--fuzz`.

### H4 · Fall-Beschriftungen: *warum* ist ein Test fehlgeschlagen
Bei Fehlschlag anzeigen, welche Kategorie von Edge-Case betroffen ist
(„leerer String“, „nur Leerzeichen“, „INT_MIN“, „keine Argumente“ …) statt
nur `case 4`. Optionale Labels an kuratierten Fällen in den Banken.

### H5 · Readiness-Übersicht pro Level
`--readiness` / Menüpunkt: pro Level alle **Standard**-Aufgaben mit Status
(✔ bestanden / ✖ gescheitert / · nie versucht) + Prozent „exam-ready“.
Zeigt sofort, wo die Lücken sind, bevor man ins echte Exam geht.

### H6 · Tägliches Drill-Programm
`--drill`: stellt eine kurze Session (z. B. 5 Aufgaben) aus schwachen,
nie-versuchten und lange-nicht-geübten Standard-Aufgaben zusammen
(Spaced-Repetition-light, nutzt vorhandene `stats.jsonl`).

---

## Ablauf

1. Diesen Plan reviewen → Punkte in Phase 2 bestätigen/streichen.
2. Phase 1 umsetzen, pro Bug ein Commit mit Test.
3. Bestätigte Phase-2-Punkte umsetzen, je Feature ein Commit, README/TUTORIAL
   + CHANGELOG aktualisieren.
4. Alle Checks grün → PR von `claude/dreamy-bohr-q3sw4d` erstellen.

## Offene Fragen

- H1: Realistischer Modus als **Default** im Exam (mit `--relaxed` als
  Ausweg) oder nur per Flag?
- H1: Welches Zeitlimit als Default (keins / 3 h)?
- Phase 2: alle Punkte oder nur eine Auswahl?
