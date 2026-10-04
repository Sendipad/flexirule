#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_DIR:-$HOME/frappe-bench}"
SITE="${FRAPPE_SITE:-test_site}"

case "${1:-help}" in
  setup)
    exec bash /workspaces/flexirule/.devcontainer/bootstrap.sh
    ;;
  start)
    cd "$BENCH_DIR"
    exec bench start
    ;;
  migrate)
    cd "$BENCH_DIR"
    exec bench --site "$SITE" migrate
    ;;
  shell)
    cd "$BENCH_DIR"
    exec bench --site "$SITE" console
    ;;
  test)
    cd "$BENCH_DIR"
    exec bench --site "$SITE" set-config allow_tests true
    exec bench --site "$SITE" run-tests --app flexirule
    ;;
  build)
    cd "$BENCH_DIR"
    exec bench build --app flexirule
    ;;
  lint)
    cd /workspaces/flexirule
    exec yarn lint
    ;;
  ui)
    cd "$BENCH_DIR"
    exec bench --site "$SITE" run-ui-tests flexirule --headless
    ;;
  doctor)
    cd "$BENCH_DIR"
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
