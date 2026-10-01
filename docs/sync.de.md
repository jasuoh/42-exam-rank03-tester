# 🔄 Sync einrichten — auf jedem Gerät mit deinem Stand weitermachen

[← zurück zum README](../README.md) · 🇬🇧 [English version](sync.md)

Mit `make sync` nimmst du **deinen Fortschritt, ein pausiertes Exam und deine
Lösungen** von einem Gerät aufs andere mit — z. B. morgens im Cluster, abends
am eigenen Laptop. Alles läuft über **dein eigenes, privates Git-Repo**. Es
gibt keinen Server von uns dazwischen.

## Kurzfassung

```bash
# 1× auf GitHub: leeres PRIVATES Repo anlegen, z. B. "examshell-progress"
# 1× pro Gerät, im Ordner des Testers:
make sync-setup REPO=git@github.com:<dein-name>/examshell-progress.git

# danach immer: beim Aufhören UND beim Weitermachen
make sync
```

Das ist alles. Die Schritte im Detail:

---

## 1. Privates Repo anlegen (einmalig)

1. Auf <https://github.com/new> gehen.
2. Name z. B. `examshell-progress`.
3. **Private** auswählen. ⚠️ Wichtig — dort liegen deine Lösungen, und
   geteilte Lösungen können an der 42 als Schummeln gelten.
4. **Keine** README, `.gitignore` oder Lizenz hinzufügen — das Repo soll leer sein.
5. „Create repository“ klicken und die **SSH-Adresse** kopieren:
   `git@github.com:<dein-name>/examshell-progress.git`

> Geht auch mit GitLab, Codeberg oder jedem anderen Git-Server — Hauptsache
> privat.

## 2. Prüfen, ob Git dich einloggen kann (einmal pro Gerät)

```bash
ssh -T git@github.com
```

- Kommt `Hi <dein-name>! You've successfully authenticated` → passt, weiter
  mit Schritt 3.
- Kommt `Permission denied (publickey)` → du brauchst auf diesem Gerät einen
  SSH-Key:

  ```bash
  ssh-keygen -t ed25519 -C "deine@mail"      # 3× Enter reicht
  cat ~/.ssh/id_ed25519.pub                  # Ausgabe kopieren
  ```

  Den kopierten Text auf <https://github.com/settings/keys> unter
  „New SSH key“ einfügen, dann `ssh -T git@github.com` nochmal testen.

> Lieber HTTPS statt SSH? Dann die `https://github.com/...`-Adresse nehmen.
> Als Passwort will GitHub dann ein **Personal Access Token**, nicht dein
> Login-Passwort.

## 3. Gerät verbinden (einmal pro Gerät)

Im Ordner, in dem der Tester liegt (`42-exam-tester/`):

```bash
make sync-setup REPO=git@github.com:<dein-name>/examshell-progress.git
```

Das verbindet das Gerät und macht direkt den ersten Sync. Auf dem ersten
Gerät siehst du z. B.:

```
✔  this device is connected to git@github.com:<dein-name>/examshell-progress.git
✔  ↓ from the repo: nothing new  ·  ↑ to the repo: 12 attempts, 3 solutions
```

Auf dem zweiten Gerät dasselbe Kommando — dort kommt dann alles herunter
(`↓ from the repo: …`).

## 4. Im Alltag

| Wann | Was |
|---|---|
| bevor du aufhörst | `make sync` |
| bevor du auf dem anderen Gerät anfängst | `make sync` |
| mitten im Exam wechseln | im Exam `quit` (speichert), `make sync`, am anderen Gerät `make sync`, dann `make exam` → „Resume?“ mit `y` |

Ein `make sync` nimmt **Python- und C-Tester** gleichzeitig mit.

---

## Was wird mitgenommen?

| Was | Wenn beide Geräte etwas haben |
|---|---|
| Übungshistorie (Stats, Readiness, Streak) | alles von beiden — nichts geht verloren |
| pausiertes Exam | das **neuere** gewinnt; ein beendetes Exam bleibt beendet |
| Exam-Reports | alle |
| Lösungen in `rendu/` und `c_rendu/` | pro Datei gewinnt die **neuere** Änderung — die ältere wird in `~/.examshell/sync-backup/` aufgehoben |
| Einstellungen (Theme, Compiler, …) | **nicht** — die bleiben pro Gerät |

Du musst nie selbst Git-Konflikte lösen: Der Tester führt beide Stände
selbst zusammen und pusht dann.

## Wenn etwas nicht klappt

| Meldung | Lösung |
|---|---|
| `sync isn't set up on this device` | Auf diesem Gerät fehlt noch Schritt 3. |
| `Permission denied (publickey)` | Schritt 2 — SSH-Key fehlt oder ist nicht bei GitHub hinterlegt. |
| `Repository not found` | Adresse vertippt, oder das Repo gehört einem anderen Account. |
| `git isn't installed` | Git installieren (`xcode-select --install` auf macOS, `sudo apt install git` auf Linux). |
| „Meine Datei wurde überschrieben!“ | Auf dem anderen Gerät war sie neuer. Deine Version liegt in `~/.examshell/sync-backup/<Datum>/`. |

**Anderes Repo verwenden:** einfach `make sync-setup REPO=<neue-adresse>`
nochmal ausführen.
**Sync auf einem Gerät abschalten:** den Ordner `~/.examshell/sync-repo/`
löschen. Deine Daten und Lösungen bleiben dabei unangetastet.

## Ohne Git: `EXAMSHELL_HOME`

Wenn du schon iCloud, Dropbox oder Nextcloud nutzt, kannst du den
Datenordner einfach dorthin legen — dann wandern Historie, pausierte Exams
und Reports automatisch mit:

```bash
export EXAMSHELL_HOME=~/Dropbox/examshell     # z. B. in ~/.zshrc eintragen
```

Deine Lösungsordner (`rendu/`, `c_rendu/`) wandern so **nicht** mit — dafür
ist `make sync` da.
