# 🔄 Setting up sync — continue on any device

[← back to the README](../README.md) · 🇩🇪 [Deutsche Version](sync.de.md)

`make sync` carries **your progress, a paused exam and your solutions** from
one device to another — say, the cluster in the morning and your own laptop
in the evening. Everything goes through **your own private git repository**.
There is no server of ours in between.

## In short

```bash
# once, on GitHub: create an empty PRIVATE repo, e.g. "examshell-progress"
# once per device, in the tester's folder:
make sync-setup REPO=git@github.com:<your-name>/examshell-progress.git

# from then on: when you stop AND when you start
make sync
```

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

In the tester's folder (`42-exam-tester/`):

```bash
make sync-setup REPO=git@github.com:<your-name>/examshell-progress.git
```

This connects the device and runs a first sync right away. On the first
device you'll see something like:

```
✔  this device is connected to git@github.com:<your-name>/examshell-progress.git
✔  ↓ from the repo: nothing new  ·  ↑ to the repo: 12 attempts, 3 solutions
```

Run the same command on the second device — there everything comes down
(`↓ from the repo: …`).

## 4. Day to day

| When | What |
|---|---|
| before you stop | `make sync` |
| before you start on the other device | `make sync` |
| switching in the middle of an exam | `quit` in the exam (it saves), `make sync`, `make sync` on the other device, then `make exam` → answer "Resume?" with `y` |

One `make sync` covers **both the Python and the C tester**. The same works as `make c-sync`, `s` in the menu, "🔄 Sync" in the full-screen app, and — if you installed with `uv tool install` — `examshell --sync` / `examshell --sync-setup <address>` — always from the folder that holds your `rendu/` and `c_rendu/`.

---

## What travels?

| What | If both devices have something |
|---|---|
| practice history (stats, readiness, streak) | everything from both — nothing is lost |
| paused exam | the **newer** one wins; a finished exam stays finished |
| exam reports | all of them |
| solutions in `rendu/` and `c_rendu/` | per file the **newer** edit wins — the older one is kept in `~/.examshell/sync-backup/` |
| settings (theme, compiler, …) | **not synced** — they stay per device |

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

**Use a different repo:** just run `make sync-setup REPO=<new-address>`
again.
**Turn sync off on a device:** delete the folder `~/.examshell/sync-repo/`.
Your data and solutions stay untouched.

## Without git: `EXAMSHELL_HOME`

If you already use iCloud, Dropbox or Nextcloud, you can simply put the data
folder there — history, paused exams and reports then travel automatically:

```bash
export EXAMSHELL_HOME=~/Dropbox/examshell     # e.g. add this to ~/.zshrc
```

Your solution folders (`rendu/`, `c_rendu/`) do **not** travel this way —
that's what `make sync` is for.
