# FlexiRule Development Environment

The repository is developed through a normal Git checkout. The Frappe Bench is deliberately created outside the repository, and FlexiRule is installed into that Bench with Frappe's canonical `bench get-app` mechanism.

## Supported stack

- Python 3.10
- Node.js 18
- Frappe Framework version-15
- ERPNext version-15
- MariaDB 10.6
- Redis 7
- Bench CLI 5.x
- site name: test_site

## GitHub Codespaces / Dev Container

Open the repository in GitHub Codespaces or VS Code's Dev Containers. The container starts MariaDB and two Redis services and runs `.devcontainer/bootstrap.sh`.

The bootstrap creates:

~~~text
/home/vscode/frappe-bench/
  apps/frappe
  apps/erpnext
  apps/flexirule
  sites/test_site
~~~

FlexiRule is installed with:

~~~bash
bench get-app --branch version-15 https://github.com/Sendipad/flexirule.git
~~~

For a PR/feature branch, set `FLEXIRULE_REF` to that branch or commit before running the bootstrap.

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

The bootstrap is idempotent: it creates the Bench and apps only when absent, then runs requirements and migration.

## GitHub Actions

CI verifies the same canonical installation architecture in isolated jobs:

1. Create a Frappe v15 Bench.
2. Install ERPNext v15 with `bench get-app`.
3. Install FlexiRule with `bench get-app` from the exact PR/commit under test.
4. Create `test_site`.
5. Install FlexiRule and migrate.
6. Build/lint and run backend tests.
7. Verify repeatable migration.
8. Run Cypress UI tests against a running Bench.

CI never symlinks the repository into `apps/flexirule` and never modifies `sites/apps.txt` manually.

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

If the site needs to be recreated, remove the `test_site` site from the Bench and rerun `.devcontainer/bootstrap.sh`.

`bench start` is the preferred iterative debugging mode because it runs the Frappe web, websocket, scheduler, and worker processes together.
