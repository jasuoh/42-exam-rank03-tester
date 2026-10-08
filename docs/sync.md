# 🔄 Setting up sync — continue on any device

[← back to the README](../README.md) · 🇩🇪 [Deutsche Version](sync.de.md)

Sync carries **your progress, a paused exam and your solutions** from
one device to another — say, the cluster in the morning and your own laptop
in the evening. Everything goes through **your own private git repository**.
There is no server of ours in between.

## In short

1. Once, on GitHub: create an empty **private** repo, e.g. `examshell-progress`.
2. Once per device: in the app, **Settings** (`o`) → *Sync repo* → paste
   `git@github.com:<your-name>/examshell-progress.git`.
3. From then on: `s` in the menu when you stop **and** when you start —
   or turn on *Auto-sync* in Settings and forget about it.

That's all. The steps in detail:

---

## 1. Create a private repo (once)

1. Go to <https://github.com/new>.
2. Name it, e.g. `examshell-progress`.
3. Choose **Private**. ⚠️ Important — your solutions end up there, and
   sharing solutions can count as cheating at 42.
4. Do **not** add a README, `.gitignore` or license — the repo must be empty.
5. Click "Create repository" and copy the **SSH address**:
   `git@github.com:<your-name>/examshell-progress.git`

> GitLab, Codeberg or any other git server works too — as long as it's private.

## 2. Check that git can log you in (once per device)

```bash
ssh -T git@github.com
```

- `Hi <your-name>! You've successfully authenticated` → good, go on to step 3.
- `Permission denied (publickey)` → this device needs an SSH key:

  ```bash
  ssh-keygen -t ed25519 -C "you@mail"      # pressing Enter 3× is fine
  cat ~/.ssh/id_ed25519.pub                # copy the output
  ```

  Paste it at <https://github.com/settings/keys> under "New SSH key", then
  run `ssh -T git@github.com` again.

> Prefer HTTPS over SSH? Use the `https://github.com/...` address instead.
> GitHub then wants a **personal access token** as the password, not your
> login password.

## 3. Connect the device (once per device)

Start the app (`make`), open **Settings** (`o`), pick *Sync repo* and paste
the address. This connects the device and runs a first sync right away — on
the first device it reports something like *↑ to the repo: 12 attempts,
3 solutions*.

Do the same on the second device — there everything comes down
(*↓ from the repo: …*).

> Without the app: `python3 -m examshell --sync-setup <address>`.

## 4. Day to day

| When | What |
|---|---|
| before you stop | `s` in the menu |
| before you start on the other device | `s` in the menu |
| switching in the middle of an exam | `esc` in the exam (it saves), `s`; on the other device `s`, then **Exam** → answer "Resume?" with `y` |

One sync covers **both the Python and the C tester**. Without the app:
`python3 -m examshell --sync` — always from the folder that holds your
`rendu/` and `c_rendu/`.

---

## 5. Sync automatically (optional)

**Settings** (`o`) → *Auto-sync* (or `python3 -m examshell --auto-sync on`).

Every session then pulls the repo's state when it starts and pushes yours
when it ends — no more remembering `s`. Offline, you only get a one-line note; you can still
practise, and the next session catches up. `make doctor` shows whether
auto-sync is on.

## What travels?

| What | If both devices have something |
|---|---|
| practice history (stats, readiness, streak) | everything from both — nothing is lost |
| paused exam | the **newer** one wins; a finished exam stays finished |
| solutions in `rendu/` and `c_rendu/` | per file the **newer** edit wins — the older one is kept in `~/.examshell/sync-backup/` |
| settings (compiler, time limit, …) | **not synced** — they stay per device |

You never have to resolve a git conflict yourself: the tester combines both
sides on its own, then pushes.

## When something goes wrong

| Message | Fix |
|---|---|
| `sync isn't set up on this device` | Step 3 is still missing on this device. |
| `Permission denied (publickey)` | Step 2 — no SSH key, or it isn't added to GitHub. |
| `Repository not found` | Typo in the address, or the repo belongs to a different account. |
| `git isn't installed` | Install git (`xcode-select --install` on macOS, `sudo apt install git` on Linux). |
| "My file was overwritten!" | It was newer on the other device. Your version is in `~/.examshell/sync-backup/<date>/`. |

**Use a different repo:** enter the new address under *Sync repo* again.
**Turn sync off on a device:** delete the folder `~/.examshell/sync-repo/`.
Your data and solutions stay untouched.

## Without git: `EXAMSHELL_HOME`

If you already use iCloud, Dropbox or Nextcloud, you can simply put the data
folder there — history and paused exams then travel automatically:

```bash
export EXAMSHELL_HOME=~/Dropbox/examshell     # e.g. add this to ~/.zshrc
```

Your solution folders (`rendu/`, `c_rendu/`) do **not** travel this way —
that's what sync is for.
