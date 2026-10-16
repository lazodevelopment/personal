#!/bin/bash
# One-time rollout of the 2026-10-16 audit fixes. Run from anywhere:  bash ~/jarvis-hub/rollout-2026-10-16.sh
# Order matters: the session secret first, then the new code, then the key swap (old key -> FEED_KEY for the
# scripts, new key -> HUB_KEY for logging in), then the VM gets the new executor + crontab.
set -e
cd "$(dirname "$0")"
[ -s .session-secret.tmp ] && [ -s .hub-login-key ] && [ -s .hub-key ] || { echo "missing .session-secret.tmp / .hub-login-key / .hub-key"; exit 1; }

echo "1/5 session secret";     tr -d '\r\n' < .session-secret.tmp | bash deploy.sh secret SESSION_SECRET
echo "2/5 deploy worker";      bash deploy.sh
echo "3/5 feed key (the key every script already carries)"; tr -d '\r\n' < .hub-key | bash deploy.sh secret FEED_KEY
echo "4/5 new login key";      tr -d '\r\n' < .hub-login-key | bash deploy.sh secret HUB_KEY
echo "5/5 VM: executor + crontab"; bash deploy.sh vm
rm -f .session-secret.tmp
echo
echo "Done. Sign in again on each device (Google sign-in, or the new key in jarvis-hub/.hub-login-key)."
