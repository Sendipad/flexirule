# FlexiRule Development Environment

This repository is the Git working tree. The Frappe Bench is deliberately created outside it and the app is linked into the Bench with a symlink.

## Supported stack

- Python 3.10
- Node.js 18
- Frappe Framework version-15
- ERPNext version-15
- MariaDB 10.6
- Redis 7
- Bench CLI 5.x
- site name: test_site

The versions above match the repository's existing CI baseline where it already specifies Python 3.10, Node 18, Frappe v15, and MariaDB 10.6.

## GitHub Codespaces / Dev Container

Open the repository in GitHub Codespaces or VS Code's Dev Containers. The container starts MariaDB and two Redis services and runs .devcontainer/bootstrap.sh.

The bootstrap creates:

~~~text
/home/vscode/frappe-bench/
  apps/frappe
  apps/erpnext
  apps/flexirule -> /workspaces/flexirule
  sites/test_site
~~~

The generated Bench is stored in a Docker volume, not in the repository.

After the container is created:

~~~bash
cd /workspaces/flexirule
bash scripts/dev-env.sh doctor
bash scripts/dev-env.sh start
~~~

In another terminal:

~~~bash
bash scripts/dev-env.sh test
bash scripts/dev-env.sh build
bash scripts/dev-env.sh lint
bash scripts/dev-env.sh migrate
~~~

For UI tests:

~~~bash
bash scripts/dev-env.sh ui
~~~

## Manual Bench commands

~~~bash
cd ~/frappe-bench
bench --site test_site migrate
bench --site test_site run-tests --app flexirule
bench build --app flexirule
bench --site test_site run-ui-tests flexirule --headless
bench start
~~~

The normal Frappe console is also available:

~~~bash
bench --site test_site console
~~~

## Frontend development

FlexiRule's frontend dependencies are managed by the app's existing Yarn lockfile.

~~~bash
yarn --cwd /workspaces/flexirule install --frozen-lockfile
yarn --cwd /workspaces/flexirule lint
~~~

Asset compilation should use Frappe's asset pipeline:

~~~bash
bench build --app flexirule
~~~

## Database and Redis

| Service | Host | Port |
|---|---|---:|
| MariaDB | db | 3306 |
| Redis cache | redis-cache | 6379 |
| Redis queue/socketio | redis-queue | 6379 |

The test site is created with MariaDB root password root and Frappe Administrator password admin. These credentials are for local development only.

## Rebuilding the environment

If the Bench or site becomes corrupted, remove the Codespace/Dev Container volumes and recreate the container. Do not commit the Bench.

The bootstrap is intentionally idempotent: it creates the Bench and apps only when absent, then re-links FlexiRule and runs migration.

## GitHub Actions

CI verifies the same architecture in isolated jobs:

1. Frontend lint and Frappe asset build.
2. Frappe v15 + ERPNext v15 installation.
3. MariaDB + Redis services.
4. Creation of test_site.
5. FlexiRule installation and migration.
6. Backend tests.
7. A second migration to catch non-repeatable migrations.
8. Cypress UI tests against a running Bench.

CI creates the Bench under the runner's home directory and symlinks the checked-out FlexiRule repository into apps/flexirule; no generated Bench is committed.

## Troubleshooting

Check the environment first:

~~~bash
bash scripts/dev-env.sh doctor
~~~

If the site needs another migration:

~~~bash
bash scripts/dev-env.sh migrate
~~~

If frontend assets are stale:

~~~bash
bash scripts/dev-env.sh build
~~~

If the site needs to be recreated, remove the test_site site from the Bench and rerun .devcontainer/bootstrap.sh.

bench start is the preferred iterative debugging mode because it runs the Frappe web, websocket, scheduler, and worker processes together.
