# ChatGPT-to-Jules handoff

The `Start Jules Task` workflow starts a Jules API session for `Sendipad/flexirule` and asks Jules to create a pull request automatically when its patch is ready. It never approves or merges a PR.

## Manual dispatch

1. Open **Actions → Start Jules Task → Run workflow**.
2. Choose the workflow ref that contains this workflow (normally `develop`).
3. Enter:
   - **Base branch**: the existing repository branch Jules should start from (defaults to `develop`).
   - **Prompt**: the complete task, implementation constraints, and acceptance criteria.
   - **Task title** (optional): the Jules session title.
4. Run the workflow. The Actions log and run summary show the Jules session URL; comment-triggered runs also publish it to the issue/PR.

The workflow validates the Git ref format and confirms that the requested base branch exists in this repository before creating a Jules session.

## Dispatch through the GitHub API

The workflow is designed for an authorized API caller that supports GitHub Actions workflow dispatch. The caller must have **Actions: write** permission and dispatch the workflow file on a ref where it exists. The dispatch request's `ref` selects the workflow version; `inputs.base_branch` independently selects Jules's starting branch.

Endpoint:

```http
POST /repos/Sendipad/flexirule/actions/workflows/jules-task.yml/dispatches
Content-Type: application/json

{
  "ref": "develop",
  "inputs": {
    "base_branch": "develop",
    "prompt": "Implement the task ...",
    "task_title": "Optional descriptive title"
  }
}
```

GitHub's standard ChatGPT GitHub connector may not expose this write operation. If it does not, use a GitHub integration/API caller that explicitly supports workflow dispatch, or use the authorized comment handoff below. Repository read access alone is not sufficient to dispatch a workflow.

## ChatGPT/GitHub comment handoff

If the connected GitHub integration can create issue/PR comments, ask ChatGPT to prepare the final task prompt and post it in this format:

```text
/jules
Implement the task described below. Follow AGENTS.md, inspect the actual call paths,
add regression tests, and run relevant checks before opening a pull request.
[Complete task prompt and acceptance criteria]
```

To start from another existing branch, put the branch on the command line:

```text
/jules --base-branch feature/my-branch
Implement the task described below...
```

The comment trigger accepts only repository owners, members, or collaborators. If the first line is malformed, the prompt is empty, the branch is invalid/nonexistent, or the prompt exceeds 20,000 characters, the workflow stops before contacting Jules. A successful comment-triggered run posts the Jules session URL and Actions run URL back to the issue/PR.

## Guardrails and prerequisites

- Fixed Jules source: `sources/github/Sendipad/flexirule`.
- Jules starts from the validated `base_branch`; default is `develop`.
- Prompts are limited to 20,000 characters; session titles are limited to 120 characters.
- `JULES_API_KEY` is read from GitHub Actions secrets and is not written to the request payload or printed in logs.
- `AUTO_CREATE_PR` is enabled and plan approval is disabled. Review the resulting PR and CI; this workflow does not merge.
- API dispatch requires a caller authorized for GitHub Actions write access. Comment-triggered handoff requires comment-write permission.
- The workflow cannot verify the secret value or Jules repository access until an authorized run executes.
