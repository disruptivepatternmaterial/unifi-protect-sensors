---
name: hacs-release-workflow
description: Release workflow for the unifi-protect project. Use when asked to push changes, cut versions, create tags, publish GitHub releases, or ship HACS updates. Includes mounted-volume path rules, SSH fallback host usage, and mandatory README/docs/changelog updates for every release.
---

# HACS Release Workflow

## Repository And Host Rules

- **Local path (mounted volume):** `/Volumes/ntableman/Documents/GitHub/unifi-protect`
- **Remote path on SSH host:** `~/Documents/GitHub/unifi-protect` (no `/Volumes/ntableman` prefix)
- **Primary remote:** `git@github.com:disruptivepatternmaterial/unifi-protect-sensors.git`
- **SSH host:** `192.168.10.223` — use `id_ed25519_particle` key, `gh` is at `/opt/homebrew/bin/gh`

**Push strategy:** The local sandbox cannot push to GitHub (keychain blocked). Always use SSH for `git push`, tag push, and `gh release create`:

```bash
ssh -i ~/.ssh/id_ed25519_particle -o IdentitiesOnly=yes ntableman@192.168.10.223 \
  "cd ~/Documents/GitHub/unifi-protect && <commands>"
```

Do not bounce tasks back to the user unless a step requires interactive human auth (e.g. browser device-code flow).

## Required For Every Release

Before tagging, update all relevant files:

1. `custom_components/unifi_protect_sensors/manifest.json` — bump `version`
2. `docs/CHANGELOG.md` — add release section with date
3. `README.md` — update if behavior, setup, or device support changed
4. `docs/ENTITIES.md` — update if entities or API fields changed

Never ship a release without completing these.

## Release Checklist

```text
Release Progress:
- [ ] Confirm working tree clean and on main
- [ ] Run tests — all must pass
- [ ] Update manifest.json version
- [ ] Update docs (CHANGELOG, README, ENTITIES as needed)
- [ ] Commit: "chore: bump version to X.Y.Z"
- [ ] Push main via SSH host
- [ ] Create and push annotated tag via SSH host (after main push)
- [ ] Publish GitHub release with notes via SSH host
- [ ] Verify release URL responds 200
```

## Standard Commands

Check status locally:

```bash
cd /Volumes/ntableman/Documents/GitHub/unifi-protect
git status
git log --oneline -5
```

Run tests (bootstrap `.venv_test` first if it doesn't exist):

```bash
# Create if missing
[ ! -f .venv_test/bin/pytest ] && python/bin/python3.11 -m venv .venv_test && .venv_test/bin/pip install -q pytest pytest-asyncio

.venv_test/bin/pytest tests/ -q --no-header
```

Commit locally:

```bash
git add -A
git commit -m "chore: bump version to X.Y.Z"
```

## Pushing, Tagging, and Releasing via SSH

Run all of these over SSH. The tag must be created **after** main is pushed so it points at the correct commit.

```bash
ssh -i ~/.ssh/id_ed25519_particle -o IdentitiesOnly=yes ntableman@192.168.10.223 "
  cd ~/Documents/GitHub/unifi-protect &&
  git pull origin main --rebase &&
  git push origin main &&
  git tag -d vX.Y.Z 2>/dev/null || true &&
  git tag -a vX.Y.Z -m 'vX.Y.Z — <release title>' &&
  git push origin vX.Y.Z
"
```

Create the GitHub release using the CHANGELOG as the release notes source. Extract the relevant section first:

```bash
# Extract notes for this version from CHANGELOG (adjust sed pattern to match version)
NOTES=$(sed -n '/^## \[X.Y.Z\]/,/^## \[/{ /^## \[X.Y.Z\]/d; /^## \[/d; p }' docs/CHANGELOG.md)

ssh -i ~/.ssh/id_ed25519_particle -o IdentitiesOnly=yes ntableman@192.168.10.223 "
  export PATH='/opt/homebrew/bin:$PATH'
  gh release create vX.Y.Z \
    --repo disruptivepatternmaterial/unifi-protect-sensors \
    --title 'vX.Y.Z — <release title>' \
    --notes '$NOTES'
"
```

Verify release is live:

```bash
curl -I -s "https://github.com/disruptivepatternmaterial/unifi-protect-sensors/releases/tag/vX.Y.Z" | grep -i "^HTTP"
```

## Reporting Back

When done, report:

- Commit SHA pushed to `main`
- Tag pushed (e.g. `v0.2.0`)
- Release URL
- Test result summary (N passed)
- Which docs were updated
