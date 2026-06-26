#!/usr/bin/env bash
# setup-github-auth.sh
# Run once on the build host to permanently fix GitHub auth for git, gh CLI,
# and all non-interactive agents (Cursor, CI, cron, etc.)
#
# Usage:
#   bash setup-github-auth.sh ghp_YOUR_TOKEN_HERE
#   bash setup-github-auth.sh  (will prompt securely)

set -e

GH=/opt/homebrew/bin/gh
ZPROFILE="$HOME/.zprofile"

# ── 1. Get the token ────────────────────────────────────────────────────────
if [[ -n "$1" ]]; then
  PAT="$1"
else
  read -rs -p "GitHub PAT (repo scope): " PAT
  echo
fi

[[ "$PAT" =~ ^gh[ps]_[A-Za-z0-9_]{36,} ]] || { echo "Error: that doesn't look like a GitHub PAT"; exit 1; }

# ── 2. Authenticate gh CLI (persists to ~/.config/gh/hosts.yml) ─────────────
echo "$PAT" | "$GH" auth login --with-token
echo "✓ gh auth done ($(\"$GH\" auth status 2>&1 | grep 'Logged in' || true))"

# ── 3. Store in macOS Keychain for git HTTPS ────────────────────────────────
git config --global credential.helper osxkeychain
printf "protocol=https\nhost=github.com\nusername=oauth2\npassword=%s\n" "$PAT" \
  | git credential approve
echo "✓ git HTTPS credential stored in keychain"

# ── 4. Set GITHUB_TOKEN + PATH for all shells and non-interactive agents ────
# Remove any previous versions of these lines first
sed -i '' '/^# GitHub auth (setup-github-auth)/d;/^export GITHUB_TOKEN=/d;/^export PATH.*homebrew\/bin/d' "$ZPROFILE" 2>/dev/null || true

{
  echo "# GitHub auth (setup-github-auth)"
  echo "export GITHUB_TOKEN='$PAT'"
  echo "export PATH=\"/opt/homebrew/bin:\$PATH\""
} >> "$ZPROFILE"

# Also apply to current session
export GITHUB_TOKEN="$PAT"
export PATH="/opt/homebrew/bin:$PATH"
echo "✓ GITHUB_TOKEN + homebrew PATH written to $ZPROFILE"

# ── 5. Verify everything ────────────────────────────────────────────────────
echo ""
echo "── Verification ──────────────────────────────────────────────────"
"$GH" auth status
echo ""
echo "── git credential test (should return your PAT) ──────────────────"
printf "protocol=https\nhost=github.com\n" | git credential fill | grep username || true
echo ""
echo "All done. Re-open any existing terminals to pick up the new PATH."
echo "Agents running in new shells will automatically have GITHUB_TOKEN set."
