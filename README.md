# pc

Backup of the project folders on Jesse's PC (C:\Users\kurvh). The repo root is the
home folder; `.gitignore` whitelists project folders only.

Not in this repo on purpose (see `.gitignore`):
- generated output and deploy mirrors: `lazo-directory/dist`, `atavia-deploy`,
  `es-deploy`, `roven-deploy`, `lr-site/community` (rebuilt by the site scripts)
- secrets: `.env`, `secrets/`, service-account JSON keys
- dependencies: `node_modules`, `venv`, `.venv`

Push after working: `git add -A && git commit -m "..." && git push`
