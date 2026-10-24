import assert from "node:assert/strict";
import { runConfigSaveLifecycle } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/config_save_lifecycle.mjs";

// An active fetch blocks before starting validation.
{
	let validationCalls = 0;
	let commitCalls = 0;
	const result = await runConfigSaveLifecycle({
		isLoading: () => true,
		validate: async () => {
			validationCalls += 1;
			return { valid: true };
		},
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.deepEqual(result, { status: "blocked-stale-context" });
	assert.equal(validationCalls, 0);
	assert.equal(commitCalls, 0);
}

// A fetch that starts while an async panel validator is pending blocks the commit.
// This exercises the async lifecycle boundary instead of only the final decision helper.
{
	let loading = false;
	let releaseValidation;
	let commitCalls = 0;
	const validationPending = new Promise((resolve) => {
		releaseValidation = resolve;
	});
	const saving = runConfigSaveLifecycle({
		isLoading: () => loading,
		validate: () => validationPending,
		commit: () => {
			commitCalls += 1;
		},
	});

	loading = true;
	releaseValidation({ valid: true });
	assert.deepEqual(await saving, { status: "blocked-stale-context" });
	assert.equal(commitCalls, 0);
}

// A fetch may start and finish before validation resolves. The loading boolean
// is false again, but the generation/context guard must still reject the stale draft.
{
	let loading = false;
	let fetchGeneration = 7;
	let capturedGeneration = fetchGeneration;
	let contextCurrent = true;
	let releaseValidation;
	let commitCalls = 0;
	const validationPending = new Promise((resolve) => {
		releaseValidation = resolve;
	});
	const saving = runConfigSaveLifecycle({
		isLoading: () => loading,
		isContextCurrent: () => contextCurrent && fetchGeneration === capturedGeneration,
		validate: () => validationPending,
		commit: () => {
			commitCalls += 1;
		},
	});

	loading = true;
	fetchGeneration += 1;
	contextCurrent = false; // the fetch replaced the source node object
	loading = false;
	releaseValidation({ valid: true });

	assert.deepEqual(await saving, { status: "blocked-stale-context" });
	assert.equal(commitCalls, 0);
}

// A replaced source node is rejected even when no loading transition is observable.
{
	let commitCalls = 0;
	const result = await runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent: () => false,
		validate: async () => ({ valid: true }),
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.deepEqual(result, { status: "blocked-stale-context" });
	assert.equal(commitCalls, 0);
}

// Switching from Action A to Action B while validation is pending must not commit A's
// validated save using B's replacement draft.
{
	const originalDraft = { id: "action-a" };
	let activeDraft = originalDraft;
	let releaseValidation;
	let commitCalls = 0;
	const validationPending = new Promise((resolve) => {
		releaseValidation = resolve;
	});
	const saving = runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent: () => activeDraft === originalDraft,
		validate: () => validationPending,
		commit: () => {
			commitCalls += 1;
		},
	});
	activeDraft = { id: "action-b" };
	releaseValidation({ valid: true });
	assert.deepEqual(await saving, { status: "blocked-stale-context" });
	assert.equal(commitCalls, 0);
}

// Editing the same draft object while validation is pending must invalidate the
// save, because edits made after validation started have not been validated.
{
	const draft = { id: "action-a", data: { limit: 10 } };
	const validatedSnapshot = JSON.stringify(draft);
	let releaseValidation;
	let commitCalls = 0;
	const validationPending = new Promise((resolve) => {
		releaseValidation = resolve;
	});
	const saving = runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent: () => JSON.stringify(draft) === validatedSnapshot,
		validate: () => validationPending,
		commit: () => {
			commitCalls += 1;
		},
	});
	draft.data.limit = 20;
	releaseValidation({ valid: true });
	assert.deepEqual(await saving, { status: "blocked-stale-context" });
	assert.equal(commitCalls, 0);
}

// Closing/cancelling the modal while validation is pending must not commit.
{
	let modalOpen = true;
	let releaseValidation;
	let commitCalls = 0;
	const validationPending = new Promise((resolve) => {
		releaseValidation = resolve;
	});
	const saving = runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent: () => modalOpen,
		validate: () => validationPending,
		commit: () => {
			commitCalls += 1;
		},
	});
	modalOpen = false;
	releaseValidation({ valid: true });
	assert.deepEqual(await saving, { status: "blocked-stale-context" });
	assert.equal(commitCalls, 0);
}

// Valid saves commit once; invalid saves never commit.
{
	let commitCalls = 0;
	const valid = await runConfigSaveLifecycle({
		isLoading: () => false,
		validate: async () => ({ valid: true }),
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.equal(valid.status, "committed");
	assert.equal(commitCalls, 1);

	const invalid = await runConfigSaveLifecycle({
		isLoading: () => false,
		validate: async () => ({ valid: false, errors: ["Required field"] }),
		commit: () => {
			commitCalls += 1;
		},
	});
	assert.equal(invalid.status, "invalid");
	assert.deepEqual(invalid.validation.errors, ["Required field"]);
	assert.equal(commitCalls, 1);
}

console.log("Rule Config save lifecycle tests passed");
