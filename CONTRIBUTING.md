# Contributing to FlexiRule

Thank you for your interest in contributing!

## Development environment

FlexiRule provides a reproducible Frappe v15 development environment through GitHub Codespaces / VS Code Dev Containers.

See [DEVELOPMENT.md](DEVELOPMENT.md) for the complete setup.

The key invariant is that **the FlexiRule repository remains the Git working tree**. Do not generate or commit a Frappe Bench inside this repository. The development Bench lives outside the repository and links apps/flexirule back to the working tree.

## Daily workflow

~~~bash
bash scripts/dev-env.sh doctor
bash scripts/dev-env.sh start
~~~

Then use a second terminal for:

~~~bash
bash scripts/dev-env.sh test
bash scripts/dev-env.sh build
bash scripts/dev-env.sh lint
bash scripts/dev-env.sh migrate
bash scripts/dev-env.sh ui
~~~

## What we welcome

- Improvements to the rule engine.
- Process expansions.
- UI/UX improvements for the Rule Builder.
- Documentation and test cases.
- Improvements to the reproducible development environment.

## Pull requests

Before opening a PR, verify the affected layers locally. Backend changes should pass:

~~~bash
bench --site test_site run-tests --app flexirule
~~~

Frontend changes should pass:

~~~bash
yarn lint
bench build --app flexirule
~~~

UI changes should additionally run:

~~~bash
bench --site test_site run-ui-tests flexirule --headless
~~~

GitHub Actions performs the same environment setup and verification on pull requests.
