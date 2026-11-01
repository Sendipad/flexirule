import assert from "node:assert/strict";
import { runConfigSaveLifecycle } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/config_save_lifecycle.mjs";
import { normalizeCandidateDraft } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/candidate_normalization.mjs";

// Validation helper using normalizeCandidateDraft before contract/business validation
function validateDraft(targetDraft, options = {}) {
	normalizeCandidateDraft(targetDraft, options);
	const errors = [];
	if (targetDraft.data?.ignore_permissions && !targetDraft.data?.permission_audit_reason) {
		errors.push("Permission Audit Reason is required when bypassing permissions.");
	}
	return { valid: errors.length === 0, errors };
}

// First click save succeeds when candidate normalization applies defaults without mutating live draft
{
	const draftNode = {
		id: "node_1",
		data: {
			action_type: "Query Records",
			operation: "Fetch Records",
			ignore_permissions: 0,
			permission_audit_reason: "Audit Reason Provided",
		},
	};

	let commitCount = 0;

	// Capture initial signature of live draft
	const initialDraftSignature = JSON.stringify(draftNode);
	const isContextCurrent = () => JSON.stringify(draftNode) === initialDraftSignature;

	// Deep clone candidate draft as done in useRuleConfig.js save()
	const validatedDraft = JSON.parse(JSON.stringify(draftNode));

	const result = await runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent,
		validate: async () => validateDraft(validatedDraft, { isFrappe15: true }),
		commit: () => {
			commitCount += 1;
			draftNode.data = JSON.parse(JSON.stringify(validatedDraft.data));
		},
	});

	assert.equal(result.status, "committed");
	assert.equal(commitCount, 1);
	// Verify candidate normalization applied defaults upon commit and live draft was not mutated during validation
	assert.equal(draftNode.data.ignore_permissions, 1);
	assert.equal(draftNode.data.permission_audit_reason, "Audit Reason Provided");
}

// Permission-audit bypass test: missing audit reason when ignore_permissions=1 is normalized causes validation failure
// and leaves live draft unchanged
{
	const draftNode = {
		id: "node_1",
		data: {
			action_type: "Query Records",
			operation: "Fetch Records",
			ignore_permissions: 0, // Will be normalized to 1 on Frappe 15
			permission_audit_reason: "", // Missing audit reason!
		},
	};

	const initialDraftCopy = JSON.parse(JSON.stringify(draftNode));
	let commitCount = 0;
	const validatedDraft = JSON.parse(JSON.stringify(draftNode));

	const result = await runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent: () => true,
		validate: async () => validateDraft(validatedDraft, { isFrappe15: true }),
		commit: () => {
			commitCount += 1;
		},
	});

	assert.equal(result.status, "invalid");
	assert.equal(commitCount, 0);
	assert.deepEqual(result.validation.errors, [
		"Permission Audit Reason is required when bypassing permissions.",
	]);
	// Verify live draft remained completely unchanged
	assert.deepEqual(draftNode, initialDraftCopy);
}

// Genuine stale-context change during async validation is still rejected
{
	const draftNode = {
		id: "node_1",
		data: {
			action_type: "Query Records",
			operation: "Fetch Records",
			ignore_permissions: 0,
			permission_audit_reason: "Audit Reason Provided",
		},
	};

	let contextCurrent = true;
	let releaseValidation;
	const validationPromise = new Promise((resolve) => {
		releaseValidation = resolve;
	});

	const saving = runConfigSaveLifecycle({
		isLoading: () => false,
		isContextCurrent: () => contextCurrent,
		validate: () => validationPromise,
		commit: () => {},
	});

	// Context becomes stale while validation is pending
	contextCurrent = false;
	releaseValidation({ valid: true });

	const result = await saving;
	assert.equal(result.status, "blocked-stale-context");
}

// eslint-disable-next-line no-console
console.log("Action config validation side-effect and lifecycle tests passed");
