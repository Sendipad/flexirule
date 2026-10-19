#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v npx >/dev/null 2>&1; then
  echo "Error: Node.js/npm (npx) is required to install the Frappe agent skills." >&2
  exit 1
fi

npx --yes skills add https://github.com/frappe/skills \
  --skill frappe-app-dev \
  --skill frappe-code-review \
  --skill code-style \
  --skill ui-design \
  --skill technical-writing \
  --agent codex \
  --copy \
  --yes

echo
echo "Installed the selected Frappe skills for Codex in this checkout."
echo "Start a new Codex session if the skills are not detected automatically."
