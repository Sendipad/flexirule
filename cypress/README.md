# FlexiRule Cypress UI tests

FlexiRule follows Frappe's UI-testing layout: Cypress specs live in `cypress/integration/`,
shared commands are loaded from `cypress/support/e2e.js`, and the supported bench command
is the CI entry point.

Run the complete UI suite against a local site:

```bash
bench --site <site-name> run-ui-tests flexirule --headless --browser chrome
```

For interactive debugging, run the Cypress UI from the FlexiRule app directory:

```bash
yarn test:e2e:cypress:open
```

The browser tests use Frappe's `cy.login()` support command. The CI workflow provisions a
disposable Frappe 15 site and runs the same `bench run-ui-tests` command used by developers.
Screenshots, videos, and server logs are uploaded as workflow artifacts.
