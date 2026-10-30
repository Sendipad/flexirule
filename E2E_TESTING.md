# FlexiRule E2E Testing Architecture

FlexiRule uses Cypress for end-to-end testing, following the Frappe Framework's testing conventions.

## Project Structure

- `cypress/`: Main Cypress directory.
    - `integration/`: Contains test scripts (e.g., `rule_builder.js`).
    - `support/`: Custom commands and global configuration.
    - `fixtures/`: Static data for tests.
    - `plugins/`: Cypress plugins.
- `cypress.config.js`: Cypress configuration file.

## Execution Flow

To run FlexiRule UI tests, follow these steps:

1. **Prepare a Test Site**:

    ```bash
    bench new-site test_site
    bench --site test_site install-app flexirule
    bench --site test_site migrate
    bench --site test_site execute frappe.utils.install.complete_setup_wizard
    bench --site test_site set-admin-password admin
    ```

2. **Start the Bench**:

    ```bash
    bench --site test_site serve
    ```

3. **Run UI Tests**:
    ```bash
    bench --site test_site run-ui-tests flexirule --headless
    ```

## Infrastructure Reuse

FlexiRule reuses Frappe's Cypress infrastructure (commands, helpers, utilities). To ensure stability and avoid cross-app pathing issues during execution, the core Frappe support scripts are copied into the FlexiRule repository:

- `cypress/support/frappe_commands.js`
- `cypress/support/frappe_e2e.js`

These are then imported by FlexiRule's own `cypress/support/commands.js` and `cypress/support/e2e.js`.

## Dependencies

Required node packages are added to FlexiRule's `devDependencies` in `package.json`. The `bench run-ui-tests` command automatically handles Cypress installation in the bench environment if not present.

## Isolated Cypress smoke runner

For debugging Cypress independently of Frappe's `bench run-ui-tests` runner and the existing shared Cypress commands, use the isolated smoke configuration. It uses the regular browser UI for login, Rule creation, Visual Builder, node addition, save, and reload; it does not load `cypress/support/e2e.js`, the legacy page objects, or the Python/pytest E2E suite.

### Local run

Build the assets and start a prepared Frappe v15 site first:

```bash
bench build --app flexirule --production
bench --site localhost serve --port 8000
```

In another terminal, from the FlexiRule repository:

```bash
export FRAPPE_SITE_URL=http://localhost:8000
export FRAPPE_USER=Administrator
export FRAPPE_PASSWORD='your-test-site-password'
yarn test:e2e:cypress:smoke
```

Use a disposable test site: the smoke flow creates and then deletes a Rule. The workflow-created site uses the disposable `admin` password only inside its isolated CI environment. Do not use production credentials.

### Dedicated GitHub Actions workflow

`.github/workflows/cypress-smoke.yml` runs as its own workflow on relevant pull requests and supports manual `workflow_dispatch`. It creates a fresh Frappe v15 site, builds FlexiRule assets, starts a dedicated web server, waits for the login page to respond, runs the isolated Cypress spec, and uploads screenshots, video, diagnostics, and the server log. It does not invoke `bench run-ui-tests` or depend on a separate CI server workflow.

The runner intentionally captures browser `console.log`, `console.warn`, and `console.error` messages without globally swallowing exceptions. It explicitly fails on the previously reported grid-field/schema-getter console regressions and failed JavaScript/CSS asset responses.
