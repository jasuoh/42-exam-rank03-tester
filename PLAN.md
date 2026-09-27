# PLAN — Release 0.3.0

Branch: `claude/dreamy-bohr-q3sw4d` · Stand: 2026-09-27 · Vorgänger: 0.2.0 (#4)

Ziel von 0.3.0: **schneller üben** (weniger Tippen zwischen Versuchen),
**ehrlicher prüfen** (Exam wie das echte, auch beim Feedback) und den Code so
aufräumen, dass jedes weitere Feature nur noch **einmal** statt zweimal
gebaut werden muss.

Aufwand: Code = geänderte Zeilen inkl. Tests · Zeit = bis getestet & PR-reif.

---

## 0. Vorab (kein Code)

- **Release 0.2.0 veröffentlichen:** `git tag v0.2.0 && git push origin v0.2.0`
  → Release-Workflow erstellt das GitHub-Release. Erst danach funktioniert
  der Update-Hinweis im Menü für alle, die 0.2.0 nutzen.

---

## Priorität 1 — Übe-Erlebnis (großer Nutzen, kleiner Aufwand)

### F1 · Watch-Modus: automatisch neu bewerten beim Speichern ⭐
`make watch EX=first_word` / `grademe --watch` im Practice-Modus: der Tester
beobachtet `rendu/<ex>.py` bzw. `c_rendu/<ex>.c` und grademe't bei jeder
Änderung von selbst. Kein Hin- und Herwechseln zwischen Editor und Terminal —
das ist beim Üben der größte Zeitfresser.
- Polling der Datei-mtime (keine Abhängigkeit), Ctrl-C beendet.
- Nur Practice/Training, **nie im Exam**.
- **Code ~120 Zeilen · Zeit ~1,5 h**

### F2 · `make doctor`: Umgebung prüfen
Ein Befehl, der sagt, ob alles passt: Python-Version, `cc`/`gcc` vorhanden
und funktionsfähig (kompiliert ein Mini-Programm), `valgrind`, `rich`,
`~/.examshell` beschreibbar, `rendu/`-Ordner, Version + ob Update verfügbar.
Spart Supportfragen („warum geht grademe nicht?“).
- **Code ~100 Zeilen · Zeit ~1 h**

### F3 · Fortschritt über Zeit in `--stats`
Aktuell nur Summen. Neu: Übungstage-Streak („5 Tage in Folge“), Versuche
und Bestehensquote pro Woche als kleine Sparkline, letzte 5 Exam-Durchläufe
(Score, Zeit) — macht Fortschritt sichtbar und motiviert.
- **Code ~150 Zeilen · Zeit ~2 h**

---

## Priorität 2 — Exam noch näher am echten

### F4 · Blind-Grading im Exam ⭐
Im echten Exam sieht man bei einem Fehlschlag **nicht**, welcher Test mit
welcher Eingabe fehlschlug. Hier zeigt das Exam aktuell alle fehlgeschlagenen
Fälle inkl. Eingabe — damit trainiert man, sich auf den Tester zu verlassen,
statt selbst zu testen.
- Neues `--blind` (bzw. Teil des realistischen Modus): im Exam nur
  „✔ bestanden“ / „✖ nicht bestanden (x/y)“ ohne Fälle.
- Nach dem Exam: Zusammenfassung zeigt die Fälle, an denen man gescheitert ist
  (Lernen danach, nicht währenddessen).
- **Offene Frage:** Default im realistischen Modus oder nur per Flag?
- **Code ~80 Zeilen · Zeit ~1,5 h**

### F5 · Fuzzing für die letzten 3 C-Funktionsaufgaben
`flood_fill`, `ft_list_foreach`, `ft_list_remove_if` werden noch nur mit
kuratierten Fällen getestet. Eigene Generatoren: zufällige Grids (inkl.
Start auf Rand/Ecke, 1×1, ganze Fläche gleich), zufällige Listen (leer,
alle gleich, Treffer am Anfang/Ende — klassische `remove_if`-Bugs).
- **Code ~150 Zeilen · Zeit ~2 h**

---

## Priorität 3 — Lernhilfen vertiefen

### F6 · Gestufte Hinweise + Lösung nach dem Bestehen
- Stufe 1 (nach 3 Fehlschlägen, wie jetzt): allgemeiner Hinweis.
- Stufe 2 (nach 6 Fehlschlägen): konkreter Hinweis — generisch aus dem
  Randfall-Label abgeleitet („dein Code scheitert immer bei *tabs*“).
- **Nach dem Bestehen** (nur Practice): `solution`-Befehl zeigt die
  Referenzlösung zum Vergleichen — lernen, wie es eleganter geht.
  Vor dem Bestehen nur mit ausdrücklicher Bestätigung.
- **Code ~150 Zeilen · Zeit ~2 h**

---

## Priorität 4 — Code-Gesundheit (macht alles Weitere billiger)

### F7 · Gemeinsame Shell-Logik zusammenführen
`src/examshell.py` (1264 Z.) und `c_exam/examshell.py` (1144 Z.) haben
**~900 identische Zeilen** — Exam-Ablauf, Practice, Training, Readiness,
Drill, Menü. Jedes Feature in 0.2.0 musste doppelt gebaut werden (und B2 war
in beiden kopiert). Neues `src/shell_common.py` mit dem gemeinsamen Ablauf;
die beiden Shells liefern nur noch ihre Unterschiede (Bank, Grader-Aufruf,
Stub-Erzeugung, CLI-Flags).
- Verhalten bleibt identisch — die 397 bestehenden Tests sind das Netz.
- **Code ~−600 Zeilen netto (viel Umbau) · Zeit ~4 h**
- **Empfehlung:** als **erstes** umsetzen, dann sind F1, F3, F4, F6 jeweils
  nur noch halb so viel Arbeit.

---

## Nicht in 0.3.0 (bewusst verschoben)

- **Installierbar per `pipx install`** (`examshell`-Befehl statt
  `python3 -m src`): braucht eine Umbenennung des Pakets `src` → sinnvoll
  *nach* F7. Eigenes Release.
- **Mehrsprachige Oberfläche (DE/FR)**: hoher Aufwand (alle Texte), später.

---

## Vorschlag Reihenfolge

| Schritt | Inhalt | Zeit |
|---|---|---|
| 0 | Tag `v0.2.0` pushen (du) | 1 min |
| 1 | F7 Refactor | ~4 h |
| 2 | F1 Watch · F2 Doctor | ~2,5 h |
| 3 | F4 Blind-Grading · F5 C-Fuzzing | ~3,5 h |
| 4 | F3 Stats-Verlauf · F6 Hinweise/Lösung | ~4 h |
| 5 | Doku, CHANGELOG 0.3.0, Version bump, PR | ~1 h |

**Gesamt ~15 h**, ein PR mit einem Commit pro Feature.

## Offene Fragen

1. Alles umsetzen oder Auswahl?
2. F4: Blind-Grading als **Default** im Exam (`--relaxed` schaltet es mit ab)
   oder nur per `--blind`?
3. F6: Referenzlösung **vor** dem Bestehen überhaupt anbieten (mit
   Bestätigung) oder strikt erst danach?
