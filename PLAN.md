# PLAN — ExamShell 1.0: Vollbild-Terminal-App (TUI)

Branch: `claude/dreamy-bohr-q3sw4d` · Stand: 2026-09-27 · Vorgänger: 0.2.0 (#4)

> **Stand 0.3.0:** Phase A (#5) und die TUI (Phasen B–D) sind umgesetzt.
> Offen für 1.0: Feedback echter Nutzer einarbeiten (Issue-Vorlagen sind
> da), danach entscheiden, ob die TUI Standard wird.

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

## 0.5.0 — uv, Ein-Befehl-Installation, doctor, C im Sync & in der TUI · ✔ umgesetzt

- Paket `src` → `examshell`; `uv tool install … examshell[tui]` liefert die
  Befehle `examshell` und `examshell-c`.
- `uv.lock` + `make install` über uv (pip als Fallback), CI über setup-uv.
- `--doctor` / `make doctor`.
- Sync auch über `make c-sync`, Menüpunkt `s` und „🔄 Sync“ in der TUI.
- TUI: „🔀 Switch exam“ zwischen Python 03/04/05 und C 02.

**Als Nächstes (Vorschlag):** Randfall-Tests für `flood_fill`,
`ft_list_foreach`, `ft_list_remove_if`; Referenzlösung nach dem Bestehen;
Feedback echter Nutzer einarbeiten.

---

## 0.4.0 — Git-Sync: auf jedem Gerät mit demselben Stand weitermachen · ✔ umgesetzt

Ziel: Fortschritt **und** Lösungen über ein eigenes, **privates** Git-Repo
zwischen Geräten (Schule ↔ Laptop) mitnehmen — kein Server, kein Account
bei uns, nichts verlässt die Rechner außer Richtung des eigenen Repos.

```bash
make sync-setup REPO=git@github.com:<du>/examshell-progress.git   # einmal pro Gerät
make sync                                                         # vor und nach dem Üben
```

**Was synchronisiert wird** (Arbeitskopie in `~/.examshell/sync-repo/`):

| Daten | Zusammenführen |
|---|---|
| `stats.jsonl` (alle Versuche) | Vereinigung aller Zeilen, nach Zeit sortiert — nichts geht verloren |
| gespeichertes Exam (je Tester/Rank) | das **neuere** gewinnt; ein beendetes Exam hinterlässt einen Lösch-Marker, damit es nicht auf dem anderen Gerät wieder auftaucht |
| Exam-Reports | Vereinigung (Dateinamen sind eindeutig) |
| Lösungen `rendu/`, `c_rendu/` | pro Datei gewinnt die **neuere** Änderung; die ältere Version wird lokal in `~/.examshell/sync-backup/` aufgehoben — Code geht nie verloren |
| `config.json` | **nicht** — Einstellungen wie Compiler sind pro Gerät |

Kein `git merge`: der Tester holt den Remote-Stand, führt selbst nach den
Regeln oben zusammen, schreibt das Ergebnis lokal und ins Repo, committet und
pusht. Dadurch gibt es nie Git-Konflikte für den Nutzer.

Dazu: `EXAMSHELL_HOME` verlegt den Datenordner (z. B. in iCloud/Dropbox) als
einfachste Alternative ohne Git.

**Aufwand:** ~500 Zeilen inkl. Tests · ~1 Tag.

---

## Phase A — Engine von Anzeige trennen (0.3.0) · *dieser PR*

Heute: `examshell/examshell.py` und `c_exam/examshell.py` enthalten **je** den
kompletten Ablauf (Exam, Practice, Training, Readiness, Drill, Menü) —
~900 identische Zeilen, und Logik und `print`/`input` sind verwoben. Eine
TUI kann darauf nicht aufsetzen.

1. **`examshell/shell_common.py`** — der gemeinsame Ablauf, einmal. Die beiden
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

`make tui` / `python3 -m examshell --tui` (später Default, wenn Textual da ist):
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
