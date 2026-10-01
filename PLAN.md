# PLAN — ExamShell

Branch: `claude/dreamy-bohr-q3sw4d` · Stand: 2026-10-01 · aktuell auf `main`: **0.5.0** (dieser PR: **0.6.0**)
(noch **kein** veröffentlichtes Release — es gibt keinen einzigen Tag)

---

## ✔ Erledigt (Kurzüberblick)

| Version | Inhalt | PR |
|---|---|---|
| 0.2.0 | Bugfixes, strenges Exam, `--time-limit`, `inter`, Randfall-Fuzzing für C-Programme, Randfall-Labels, Readiness, Drill, Versionierung, Update-Hinweis | #4 |
| 0.3.0 | Gemeinsame Engine für beide Tester (`ExamRun`, `grade()`), Vollbild-App (TUI), `--blind`, kurzes README + `docs/`, Issue-Vorlagen | #5, #6 |
| 0.4.0 | `make sync` über eigenes privates Git-Repo, `EXAMSHELL_HOME`, Anleitung DE/EN | #7 |
| 0.5.0 | Paket `examshell`, `uv tool install` → `examshell` / `examshell-c`, uv + Lockfile, `--doctor`, Sync im C-Tester und in den Menüs, Exam-Wechsel in der TUI | #8 |

Details: CHANGELOG.md.

---

## ▶ 0.6.0 — „bereit für echte Nutzer“ · R1, F1, F2, T1, S1 ✔ umgesetzt

Ziel: Das Tool ist technisch weit — jetzt soll es **bei Leuten ankommen**,
**Feedback einsammeln** und **zuverlässig Updates ausliefern**. Dazu die
letzten bekannten Test-Lücken schließen.

### R1 · Releases automatisch veröffentlichen ⭐ ✔
**Problem:** Ein Release entsteht nur durch einen manuell gepushten Tag — das
ist seit 0.2.0 jedes Mal liegen geblieben. Ohne Release funktionieren der
Update-Hinweis im Menü und der Update-Check in `doctor` nicht.
**Lösung:** Workflow auf `main`: Hat sich `examshell/version.py` geändert und
gibt es den Tag noch nicht → Tests laufen → Tag `vX.Y.Z` + GitHub-Release mit
dem passenden CHANGELOG-Abschnitt. Der bisherige Tag-Workflow bleibt als
manueller Weg bestehen.
**Einmalig:** v0.5.0 nachträglich veröffentlichen (passiert beim ersten Lauf
automatisch).
**Aufwand:** ~30–45 min

### F1 · Feedback mit einem Klick ✔
- `examshell --feedback` / `examshell-c --feedback` und ein Menüpunkt
  „Feedback geben“ (Terminal-Menü + TUI): öffnet die passende Issue-Vorlage
  im Browser, **Version, Tester und Betriebssystem schon ausgefüllt**. Ohne
  Browser wird der Link nur angezeigt.
- Auswahl: „Aufgabe weicht vom echten Exam ab“ · „Bug“ · „Feedback“.
- Nichts wird automatisch gesendet — der Nutzer sieht und schickt das Issue
  selbst ab.
**Aufwand:** ~45 min

### F2 · Richtige Haltung nach außen ✔
- Kurzer Hinweis im README: *Übungstool — im echten Exam gibt es nichts davon;
  es ersetzt nicht das eigene Lernen.* Signalisiert die richtige Absicht, falls
  Staff/Bocal draufschaut.
- GitHub-Repo: Beschreibung aktualisieren (nennt Rank 04/05 und die Vollbild-App
  noch nicht) und Topics setzen (`42school`, `42-exam`, `exam-rank-02`,
  `exam-rank-03`, `tester`, `tui`) — damit Suchende es finden.
  *Das Setzen von Beschreibung/Topics machst du in den Repo-Einstellungen
  (Zahnrad bei „About“) — ich liefere die Texte.*
**Aufwand:** ~15 min

### T1 · Randfall-Tests für die letzten 3 C-Aufgaben ✔
`flood_fill`, `ft_list_foreach` und `ft_list_remove_if` werden bisher nur mit
festen Fällen geprüft. Eigene Zufallsgeneratoren:
- **Listen:** leer, ein Element, alle gleich, Treffer am Anfang / am Ende /
  überall / nirgends — die klassischen `remove_if`-Bugs (Kopf nicht
  umgehängt, Speicher nicht freigegeben, nach dem Löschen falsch weiter).
- **flood_fill:** zufällige Grids, Start in Ecke / am Rand / in einer
  1×1-Fläche, die ganze Fläche gleich, Zeichen, die nicht gefüllt werden
  dürfen.
- Alles auch unter valgrind im Bank-Selbsttest (keine Leaks in den Referenzlösungen).
**Aufwand:** ~2 h

### S1 · Optional: Auto-Sync ✔
Einstellung (per `--save-config`): beim Start automatisch holen, beim Beenden
automatisch hochladen — nur wenn Sync eingerichtet ist, Fehler (offline)
werden nur als Hinweis gezeigt, nie als Abbruch.
**Aufwand:** ~1 h

**Gesamt 0.6.0:** ~5 h, ein PR, ein Commit pro Punkt.

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
