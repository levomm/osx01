#!/usr/bin/env bash
# One-time setup: GitHub Actions -> restricted SafeClip deploy account.
# Run on your own Android Termux. No private key leaves Termux except for the
# encrypted GitHub Actions secret. No existing server service is replaced.
set -Eeuo pipefail

HOST='46.62.156.109'
OWNER='levomm'
REPO='levomm/safeclip'
DEPLOY_USER='safeclipdeploy'
KEY="$HOME/.ssh/safeclip_actions_ed25519"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v pkg >/dev/null 2>&1; then
  fail 'Run this in Android Termux, not on the server.'
fi

for cmd in gh ssh ssh-keygen; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing $cmd, installing dependencies via Termux..."
    pkg install -y gh openssh || fail 'Termux package setup failed'
    break
  fi
done

if ! gh auth status >/dev/null 2>&1; then
  echo 'GitHub login is needed once. Complete login in your browser.'
  gh auth login --web --git-protocol https
fi
LOGIN="$(gh api user --jq .login)"
[[ "$LOGIN" == "$OWNER" ]] || fail "GitHub is logged in as '$LOGIN', expected '$OWNER'."

if ! gh repo view "$REPO" >/dev/null 2>&1; then
  echo "Creating independent private repository $REPO ..."
  gh repo create "$REPO" --private --description 'OSX01 SafeClip one-time encrypted secret sharing'
fi
PRIV="$(gh api "repos/$REPO" --jq .private)"
[[ "$PRIV" == true ]] || fail "Repository $REPO must be PRIVATE, refusing to store deploy credentials."

install -d -m 700 "$HOME/.ssh"
if [[ -e "$KEY" && ! -e "$KEY.pub" ]] || [[ ! -e "$KEY" && -e "$KEY.pub" ]]; then
  fail "Partial deploy key found at $KEY; inspect before continuing."
fi
if [[ ! -f "$KEY" ]]; then
  echo 'Generating a dedicated SafeClip deploy key locally...'
  ssh-keygen -q -t ed25519 -N '' -f "$KEY" -C 'safeclip-github-actions'
fi
chmod 600 "$KEY"
chmod 644 "$KEY.pub"
PUBLIC_KEY="$(cat "$KEY.pub")"
[[ "$PUBLIC_KEY" == ssh-ed25519\ * ]] || fail 'Bad deploy public key format.'

# Quoting an authorized SSH public key avoids embedding raw key text into shell code.
printf -v QUOTED_KEY '%q' "$PUBLIC_KEY"
echo "Setting up restricted '$DEPLOY_USER' account on $HOST ..."
ssh -o StrictHostKeyChecking=accept-new "root@$HOST" \
  "SAFECLIP_PUBLIC_KEY=$QUOTED_KEY bash -s" <<'REMOTE'
set -Eeuo pipefail
APP=/opt/safeclip
DEPLOY_USER=safeclipdeploy
[[ $(id -u) -eq 0 ]] || { echo 'Expected root during first-time setup' >&2; exit 1; }
[[ -f "$APP/server.py" && -d "$APP/public" && -d "$APP/data" ]] || {
  echo 'Existing SafeClip installation not found. Nothing modified.' >&2; exit 1;
}
command -v sudo >/dev/null || { echo 'sudo missing' >&2; exit 1; }
command -v visudo >/dev/null || { echo 'visudo missing' >&2; exit 1; }
DOCKER_BIN="$(command -v docker)"
[[ -x "$DOCKER_BIN" ]] || { echo 'docker executable not found' >&2; exit 1; }
if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "/home/$DEPLOY_USER" --shell /bin/bash "$DEPLOY_USER"
fi
USER_GROUP="$(id -gn "$DEPLOY_USER")"
install -d -m 700 -o "$DEPLOY_USER" -g "$USER_GROUP" "/home/$DEPLOY_USER/.ssh"
AUTH="/home/$DEPLOY_USER/.ssh/authorized_keys"
touch "$AUTH"
chown "$DEPLOY_USER:$USER_GROUP" "$AUTH"
chmod 600 "$AUTH"
# restrict: no PTY, port forwarding, X11, agent forwarding or user rc.
ENTRY="restrict $SAFECLIP_PUBLIC_KEY"
grep -Fqx "$ENTRY" "$AUTH" || printf '%s\n' "$ENTRY" >> "$AUTH"

# Allow writes ONLY to application sources and backups. The encrypted database
# directory, Docker compose and proxy configuration stay owned as before.
chown -R "$DEPLOY_USER:$USER_GROUP" "$APP/public"
chown "$DEPLOY_USER:$USER_GROUP" "$APP/server.py"
install -d -m 700 -o "$DEPLOY_USER" -g "$USER_GROUP" "$APP/backups"
chown -R "$DEPLOY_USER:$USER_GROUP" "$APP/backups"

# Only one root-privileged operation: restart THIS named Docker container.
SUDOERS="/etc/sudoers.d/safeclipdeploy"
TEMP="$(mktemp)"
printf '%s ALL=(root) NOPASSWD: %s restart safeclip\n' "$DEPLOY_USER" "$DOCKER_BIN" > "$TEMP"
chmod 440 "$TEMP"
visudo -cf "$TEMP" >/dev/null || { rm -f "$TEMP"; exit 1; }
install -m 440 -o root -g root "$TEMP" "$SUDOERS"
rm -f "$TEMP"

echo 'Restricted deployment access installed. Database and other services untouched.'
REMOTE

# Read host public key THROUGH the existing authenticated root SSH channel.
HOST_PUB="$(ssh -o StrictHostKeyChecking=yes "root@$HOST" 'head -n 1 /etc/ssh/ssh_host_ed25519_key.pub')"
[[ "$HOST_PUB" == ssh-ed25519\ * ]] || fail 'Could not confirm SSH host key.'
printf '%s %s\n' "$HOST" "$HOST_PUB" | gh secret set SAFECLIP_SSH_KNOWN_HOSTS -R "$REPO"
gh secret set SAFECLIP_DEPLOY_KEY -R "$REPO" < "$KEY"
gh variable set SAFECLIP_HOST -R "$REPO" --body "$HOST"

echo ''
echo 'SAFECLIP ACCESS READY'
echo "GitHub repository: https://github.com/$REPO"
echo 'The assistant can now commit application code using the connected GitHub app.'
echo 'The GitHub workflow will deploy using the restricted safeclipdeploy user.'
echo 'Do NOT send the private SSH key or GitHub token in chat.'
