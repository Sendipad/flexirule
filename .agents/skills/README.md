# FlexiRule agent skills

Install the selected official Frappe skills for this checkout:

```bash
bash scripts/install-frappe-agent-skills.sh
```

The installer downloads these skills from [frappe/skills](https://github.com/frappe/skills) into the Codex project skill directory:

- `frappe-app-dev`
- `frappe-code-review`
- `code-style`
- `ui-design`
- `technical-writing`

The downloaded skill directories are intentionally excluded from Git: the upstream repository does not currently declare a repository-level license, so FlexiRule does not vendor or redistribute those files. Run the installer again to refresh the local copies from upstream. Review upstream changes before relying on updated instructions.
