#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_DIR:-/home/vscode/frappe-bench}"
SITE="${FRAPPE_SITE:-test_site}"
FLEXIRULE_REF="${FLEXIRULE_REF:-version-15}"

export PATH="$BENCH_DIR/env/bin:$BENCH_DIR/apps/frappe/.venv/bin:$PATH"

mkdir -p "$(dirname "$BENCH_DIR")"

if [ ! -f "$BENCH_DIR/apps/frappe/frappe/__init__.py" ]; then
  rm -rf "$BENCH_DIR"
  bench init --frappe-branch version-15 --skip-redis-config-generation "$BENCH_DIR"
fi

cd "$BENCH_DIR"

if [ ! -d "$BENCH_DIR/apps/erpnext/erpnext" ]; then
  bench get-app --branch version-15 erpnext https://github.com/frappe/erpnext.git
fi

if [ ! -d "$BENCH_DIR/apps/flexirule/flexirule" ]; then
  rm -rf "$BENCH_DIR/apps/flexirule"
  bench get-app --branch "$FLEXIRULE_REF" https://github.com/Sendipad/flexirule.git
fi

bench set-config -g db_host "${DB_HOST:-db}"
bench set-config -g db_port "${DB_PORT:-3306}"
bench set-config -g redis_cache "${REDIS_CACHE:-redis://redis-cache:6379}"
bench set-config -g redis_queue "${REDIS_QUEUE:-redis://redis-queue:6379}"
bench set-config -g redis_socketio "${REDIS_SOCKETIO:-redis://redis-queue:6379}"

bench setup requirements --dev

if ! bench --site "$SITE" list-apps >/dev/null 2>&1; then
  bench new-site "$SITE"     --db-root-password root     --admin-password admin     --db-host "${DB_HOST:-db}"     --db-port "${DB_PORT:-3306}"     --install-app erpnext
fi

if ! bench --site "$SITE" list-apps | grep -qx flexirule; then
  bench --site "$SITE" install-app flexirule
fi

bench --site "$SITE" migrate
bench --site "$SITE" set-config allow_tests true

echo
echo "FlexiRule development environment is ready."
echo "Bench: $BENCH_DIR"
echo "Site:  $SITE"
echo "FlexiRule: ${BENCH_DIR}/apps/flexirule"
echo "Run:   cd $BENCH_DIR && bench start"
echo "Run tests: bench --site $SITE run-tests --app flexirule"
echo "Build: bench build --app flexirule"
