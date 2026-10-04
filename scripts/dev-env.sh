#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_DIR:-$HOME/frappe-bench}"
SITE="${FRAPPE_SITE:-test_site}"

cd "$BENCH_DIR"

case "${1:-help}" in
  setup)
    exec bash /workspaces/flexirule/.devcontainer/bootstrap.sh
    ;;
  start)
    exec bench start
    ;;
  migrate)
    exec bench --site "$SITE" migrate
    ;;
  shell)
    exec bench --site "$SITE" console
    ;;
  test)
    exec bench --site "$SITE" set-config allow_tests true
    exec bench --site "$SITE" run-tests --app flexirule
    ;;
  build)
    exec bench build --app flexirule
    ;;
  lint)
    cd /workspaces/flexirule
    exec yarn lint
    ;;
  ui)
    exec bench --site "$SITE" run-ui-tests flexirule --headless
    ;;
  doctor)
    bench version
    bench --site "$SITE" list-apps
    bench --site "$SITE" migrate
    ;;
  *)
    cat <<'EOF'
Usage: scripts/dev-env.sh <setup|start|migrate|shell|test|build|lint|ui|doctor>
EOF
    ;;
esac
