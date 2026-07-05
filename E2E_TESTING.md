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
