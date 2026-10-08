# PLAN — ExamShell

Branch: `tui-clean-split` → PR nach `beta` · Stand: 2026-10-08 · auf `main`: **0.6.0** (stabil)

**Branches:** `main` bleibt stabil und ist das, was Nutzer bekommen.
`beta` ist der Integrations-Branch für 1.0.0 — Arbeits-Branches gehen per PR
nach `beta`; wenn dort alles getestet ist, `beta` → `main` = **Release
1.0.0** (der Release-Workflow taggt automatisch, nur von `main`).

---

## ✔ Erledigt (Kurzüberblick)

| Version | Inhalt | PR |
|---|---|---|
| 0.2.0 | Bugfixes, strenges Exam, `--time-limit`, `inter`, Randfall-Fuzzing für C-Programme, Randfall-Labels, Readiness, Drill, Versionierung, Update-Hinweis | #4 |
| 0.3.0 | Gemeinsame Engine für beide Tester (`ExamRun`, `grade()`), Vollbild-App (TUI), `--blind`, kurzes README + `docs/`, Issue-Vorlagen | #5, #6 |
| 0.4.0 | `make sync` über eigenes privates Git-Repo, `EXAMSHELL_HOME`, Anleitung DE/EN | #7 |
| 0.5.0 | Paket `examshell`, `uv tool install` → `examshell` / `examshell-c`, uv + Lockfile, `--doctor`, Sync im C-Tester und in den Menüs, Exam-Wechsel in der TUI | #8 |
| 0.6.0 | Releases automatisch, Feedback-Formular, Randfall-Tests für die letzten C-Aufgaben, Auto-Sync; danach Fixes, mypy strict, TUI-Layout, leeres rendu/ pro Exam, Exam-Ziehung als Deck | #9–#21 |

Details: CHANGELOG.md.

---

## ▶ 1.0.0 — Aufräumen: weniger, kompakter, das Wichtige läuft

**Ziel:** Wer zum ersten Mal kommt, ist nicht überfordert. Ein Weg zum Üben
(das TUI), eine Handvoll Befehle, ein ruhiges Aussehen — und die Kern-Features
laufen wirklich zuverlässig. Seltenes bleibt technisch drin, wird aber nicht
mehr beworben.

**Kern (muss perfekt laufen):** Exam starten · eine Aufgabe üben · grademe ·
Stub anlegen · Rank 03/04/05 + C 02 wechseln (merkt sich die letzte Wahl) ·
Fortschritt sehen.

**Leitlinie:** Der **Exam-Modus simuliert das echte Exam** — da muss alles
stimmen (Regeln, Ablauf, was grademe zeigt). Alles Komfortable (Extra-/
LeetCode-Aufgaben, Lücken üben, Details zu jedem Fail) gehört in **Practice**.
Das **Makefile** ist nur noch zum Installieren/Starten; alles andere wird im
TUI gemacht und eingestellt.

### Entscheidungen (mit dir, 2026-10-08)

| Thema | Entscheidung |
|---|---|
| Oberfläche | **TUI ist die Hauptsache.** Das Textmenü bleibt nur als schlanker Fallback (ohne Textual / Python 3.8), wird nicht weiter ausgebaut |
| Layout Übung/Exam | Aufgabe oben, Ergebnis unten, keine Code-Ansicht, kein Session-Log ✔ (Commit auf diesem Branch) |
| TUI-Menü | **5 Einträge:** Exam · Practice · Progress · Switch exam · Quit. Sync (`s`), Feedback (`f`) und **Settings (`o`)** als Tasten in der Fußzeile |
| Settings im TUI | Eigener Screen (`o`): Watch-Modus, Sync einrichten, Auto-Sync, Timeout, Zeitlimit u.ä. — ersetzt `--save-config` und die meisten Make-Variablen |
| Exam-grademe | Wie im echten Exam: **SUCCESS / FAILURE**, bei FAILURE eine **Trace mit dem fehlschlagenden Testfall** (input / expected / got) — keine Hinweise, keine weiteren Fails. Extra-Aufgaben nie im Exam |
| Practice | Ein Picker mit Tabs/Filter: **Exam-Aufgaben** · **Meine Lücken** (heutiger Drill) · **Extra** (heutiger Training-Pool) |
| Progress | Stats + Readiness auf **einem** Screen |
| Training-Pool | Kein eigener Menüpunkt mehr → Tab „Extra“ in Practice |
| Theme | **Terminal-Farben** (Textual `textual-ansi`): übernimmt das Terminal-Theme (z.B. Ghostty), ein Akzent für ✔/✖; `--theme` light/highcontrast fallen weg |
| grademe-Panel | **Kompakt + aufklappbar:** Panel nur so hoch wie nötig, eine Ergebniszeile, die ersten 3 Fails je 1 Zeile (`input  got ≠ expected`), `d` zeigt alle Details |
| Raus | **Badges/Achievements** und **Markdown-Reports** (`~/.examshell/reports/`) |
| Bleibt versteckt | Blind-Modus, Auto-Sync, `--relaxed`, `--time-limit`, `--strict*`, `--fuzz`, `--diff`, `--show-fails`, `--no-rich`/`--no-color`, `--seed` — funktionieren weiter, stehen aber nur in `docs/` |
| `make` | **Nur noch:** `make` (startet das TUI, letzte Wahl, auch C) · `make install` · `make update` · `make doctor` · `make dev` (Tests/Lint für Mitwirkende). Alles andere (`exam`, `practice`, `grade`, `stats`, `sync`, `c-*`, `RANK=` …) entfällt aus dem Makefile — die CLI-Flags bleiben für Skripte |
| Release | **1.0.0**, nur von `main`; CI läuft auch auf `beta` |
| README | Neu, kurz: was es ist · Installation · 3 Befehle · ein Screenshot. Alles andere in `docs/` |

### Schritte

0. **Branches** — `beta` angelegt ✔; CI auch bei Push auf `beta` ✔.
1. **TUI-Menü & Screens bündeln** — 5 Einträge; Practice-Picker mit Tabs
   (Exam / Lücken / Extra); Progress = Stats + Readiness; Sync/Feedback als
   Tasten.
2. **Kompaktes grademe-Panel** — Ergebniszeile, 3 Fails einzeilig, `d` für
   Details; Panel-Höhe nach Inhalt.
3. **Theme** — `textual-ansi`, weniger Emojis/Rahmen/Farben, schlichte
   Statuszeile; Rich-Ausgabe im Textmenü ebenfalls auf Terminal-Farben.
4. **Entfernen** — Badges (`achievements.py`), Markdown-Reports
   (`report_export.py`), Theme-Varianten; Tests/Doku nachziehen.
5. **Exam = echtes Exam** — grademe im Exam: Ergebnis + erster Fail;
   Exam-Regeln gegen das echte Exam prüfen (Ablauf, Level, Zeit, Stub).
6. **Settings-Screen** (`o`) im TUI; **Makefile** auf `make`/`install`/
   `update`/`doctor`/`dev` reduzieren; `--help` zeigt nur die Kern-Flags.
7. **README neu**, `docs/` an die neue Struktur anpassen, CHANGELOG.
8. **AGENTS.md** — Projekt, Befehle, Konventionen, Workflow (Branch → PR,
   nie selbst mergen, Tests nie ins echte `~/.examshell`).
9. **Multi-Agent-Testrunde** — parallele Agenten testen manuell wie neue
   Nutzer: Python-Exam · C-Exam · Practice/Progress im TUI · Installation +
   `make`/doctor · README/Doku-Review. Bugs sammeln → fixen → zweite
   Durchsicht.

Erst nach Schritt 9 und deinem OK: PR nach `beta`. Version **1.0.0** +
CHANGELOG, dann `beta` → `main` = Release.

---

### Außerhalb des Codes (du)
- [ ] Beim Staff/Bocal deines Campus kurz nachfragen, ob ein öffentlicher
      Übungstester okay ist.
- [ ] 2–3 Peers, die bald ins Exam gehen, direkt fragen (DM/Lerngruppe) —
      Nachrichten-Vorlage siehe unten.
- [ ] Erst danach ggf. ein passender Campus-Kanal, r/42school, Discord.

**Vorlage (DM / Lerngruppe):**
> Hey! Ich hab mir für die Exam-Vorbereitung einen Übungs-Tester gebaut (C Rank
> 02 + Python Rank 03–05): zufällige Aufgabe pro Level, `grademe` wie im echten
> Exam, testet viele Randfälle (Tabs, leere Strings, falsche argc …) und zeigt
> dir, welches Level noch Lücken hat.
> Falls du gerade aufs Exam lernst und Lust hast, es auszuprobieren:
> https://github.com/jasuoh/42-exam-tester
> Mich interessiert vor allem: **Weicht eine Aufgabe von deinem echten Exam ab?**
> Dafür gibt's eine Issue-Vorlage — oder schreib mir einfach direkt 🙏

---

## ⏸ Bewusst zurückgestellt

| Idee | Warum nicht jetzt |
|---|---|
| Referenzlösung nach dem Bestehen anzeigen | Macht das Tool beim Thema „Exam-Lösungen verbreiten“ angreifbarer — erst klären, wie der Campus dazu steht; niemand hat bisher danach gefragt |
| Gestufte (konkretere) Hinweise | Sinnvoll, aber besser mit echtem Feedback, *welche* Hinweise fehlen |
| Rank-04/05-Pools erweitern (je nur 7 Aufgaben) | Braucht verlässliche Quellen für echte Subjects — Feedback abwarten |
| Editor direkt in der TUI | Beeindruckend, entfernt sich aber vom echten Exam (dort: vim/emacs im Terminal) |
| Web-Dashboard | Erst wenn es Nutzer gibt, die danach fragen |

---

## 💡 Nächste Ideen (zum gemeinsamen Überlegen)

*Platz für das, was wir als Nächstes besprechen — über 0.6.0 hinaus.*
