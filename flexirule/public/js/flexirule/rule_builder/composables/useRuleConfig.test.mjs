import assert from "node:assert/strict";
import { runConfigSaveLifecycle } from "../utils/config_save_lifecycle.mjs";

// Helper mock to simulate useRuleConfig normalize + save logic
function createMockUseRuleConfig({ nodeData, isFrappe15 = true, panelValidator = null }) {
	let liveNode = { id: "node-1", label: "Query Records", data: { ...nodeData } };
	let draftNode = {
		id: "node-1",
		label: "Query Records",
		data: JSON.parse(JSON.stringify(nodeData)),
	};
	let isLoading = false;
	let fetchGeneration = 1;
	let saveContextGeneration = 1;

	function normalizeCandidate(candidateDraft) {
		if (!candidateDraft?.data) return candidateDraft;
		const doc = candidateDraft.data;
		if (doc.action_type === "Query Records" && doc.operation === "Fetch Records") {
			if (isFrappe15 && ![true, 1, "1"].includes(doc.ignore_permissions)) {
				doc.ignore_permissions = 1;
			}
		}
		return candidateDraft;
	}

	async function validate(targetDraft) {
		const errors = [];
		if (targetDraft.data?.ignore_permissions && !targetDraft.data?.permission_audit_reason) {
			errors.push("Permission Audit Reason is required when bypassing permissions.");
		}
		if (panelValidator) {
			const res = await panelValidator(targetDraft);
			if (!res.valid) errors.push(...(res.errors || []));
		}
		return { valid: errors.length === 0, errors };
	}

	async function save() {
		const sourceNode = liveNode;
		const sourceDraft = draftNode;
		const validatedDraft = sourceDraft ? JSON.parse(JSON.stringify(sourceDraft)) : null;
		const validatedDraftSignature = validatedDraft ? JSON.stringify(validatedDraft) : null;
		const sourceGeneration = fetchGeneration;
		const sourceContextGeneration = saveContextGeneration;

		const hasUnchangedDraft = () => {
			if (!sourceDraft || validatedDraftSignature === null) return false;
			return JSON.stringify(sourceDraft) === validatedDraftSignature;
		};

		const isSourceContextCurrent = () =>
			Boolean(
				sourceNode &&
					validatedDraft &&
					draftNode === sourceDraft &&
					hasUnchangedDraft() &&
					saveContextGeneration === sourceContextGeneration &&
					fetchGeneration === sourceGeneration
			);

		const candidateDraft = normalizeCandidate(JSON.parse(JSON.stringify(validatedDraft)));

		const saveResult = await runConfigSaveLifecycle({
			isLoading: () => isLoading,
			isContextCurrent: isSourceContextCurrent,
			validate: () => validate(candidateDraft),
			commit: () => {
				if (!sourceNode || !candidateDraft) return;
				sourceNode.data = JSON.parse(JSON.stringify(candidateDraft.data));
				if (draftNode) {
					draftNode.data = JSON.parse(JSON.stringify(candidateDraft.data));
				}
			},
		});

		return saveResult;
	}

	return {
		getLiveNode: () => liveNode,
		getDraftNode: () => draftNode,
		setLoading: (val) => {
			isLoading = val;
		},
		incrementFetchGeneration: () => {
			fetchGeneration += 1;
		},
		cancelContext: () => {
			saveContextGeneration += 1;
		},
		save,
	};
}

// 1. A configuration whose validation applies ignore_permissions default saves successfully on the FIRST click.
{
	const instance = createMockUseRuleConfig({
		nodeData: {
			action_type: "Query Records",
			operation: "Fetch Records",
			permission_audit_reason: "Automated audit check",
		},
		isFrappe15: true,
	});

	const initialDraftSignature = JSON.stringify(instance.getDraftNode());

	const result = await instance.save();
	assert.equal(result.status, "committed");

	// 2. The default is committed to the final configuration.
	assert.equal(instance.getLiveNode().data.ignore_permissions, 1);
	assert.equal(instance.getDraftNode().data.ignore_permissions, 1);

	// 3. Validation does not mutate original draft BEFORE commit check/during validation.
	// (Proved because if it had mutated draftNode before signature check, isSourceContextCurrent would fail and status would be blocked-stale-context).
}

// 4. Invalid configuration does not partially mutate or commit the draft.
{
	const instance = createMockUseRuleConfig({
		nodeData: {
			action_type: "Query Records",
			operation: "Fetch Records",
			// missing permission_audit_reason
		},
		isFrappe15: true,
	});

	const initialLiveNode = JSON.parse(JSON.stringify(instance.getLiveNode()));
	const result = await instance.save();

	assert.equal(result.status, "invalid");
	assert.deepEqual(instance.getLiveNode(), initialLiveNode);
	assert.equal(instance.getLiveNode().data.ignore_permissions, undefined);
}

// 5. Genuine stale-context change during asynchronous validation is rejected.
{
	let releasePanelValidation;
	const validationPromise = new Promise((resolve) => {
		releasePanelValidation = resolve;
	});

	const instance = createMockUseRuleConfig({
		nodeData: {
			action_type: "Query Records",
			operation: "Fetch Records",
			permission_audit_reason: "Audit reason",
		},
		isFrappe15: true,
		panelValidator: () => validationPromise,
	});

	const savePromise = instance.save();

	// User modifies draft while validation is pending
	instance.getDraftNode().data.permission_audit_reason = "Modified during save";

	releasePanelValidation({ valid: true });
	const result = await savePromise;

	assert.equal(result.status, "blocked-stale-context");
	assert.equal(instance.getLiveNode().data.permission_audit_reason, "Audit reason");
}

// 6. Validation failure followed by correction and retry succeeds on first retry click.
{
	const instance = createMockUseRuleConfig({
		nodeData: {
			action_type: "Query Records",
			operation: "Fetch Records",
		},
		isFrappe15: true,
	});

	// Attempt 1: Invalid
	let result = await instance.save();
	assert.equal(result.status, "invalid");

	// User corrects error
	instance.getDraftNode().data.permission_audit_reason = "Fixed audit reason";

	// Attempt 2: Should succeed on first click
	result = await instance.save();
	assert.equal(result.status, "committed");
	assert.equal(instance.getLiveNode().data.ignore_permissions, 1);
	assert.equal(instance.getLiveNode().data.permission_audit_reason, "Fixed audit reason");
}

console.log("Bug 1 Action Config Save Lifecycle tests passed!");
