import { ref, reactive, computed, watch, nextTick } from "vue";
import { useGraphStore, useRuleStore, useStore } from "../stores";
import { getContract, getOperationFieldOverride, validateAgainstContract } from "../../core/contracts.js";
import { deepClone } from "../utils/serialization.js";
import { stableStringify } from "../utils/stable_serialization.mjs";
import { runConfigSaveLifecycle } from "../utils/config_save_lifecycle.mjs";

/**
 * useRuleConfig
 *
 * Composable to manage the state and lifecycle of a rule node configuration.
 *
 * @param {Object} props - Component props containing the source node
 * @param {Object} emit - Component emit function
 */
export function useRuleConfig(props, emit) {
	const ruleStore = useRuleStore();
	const graphStore = useGraphStore();
	const store = useStore();
	const draftNode = ref(null);
	const showValidation = ref(false);
	const config = computed(() => draftNode.value?.data || {});

	// Capture initial draft state after a short delay to allow background sync to settle
	const initialDraftState = ref(null);

	const isDirty = ref(false);
	const isSaving = ref(false);
	// Invalidates pending saves when the modal is cancelled or the editing context changes.
	let saveContextGeneration = 0;

	watch(
		[() => draftNode.value?.data, initialDraftState],
		() => {
			if (!props.node || !draftNode.value || initialDraftState.value === null) {
				isDirty.value = false;
				return;
			}
			const current = stableStringify(draftNode.value.data || {});
			isDirty.value = current !== initialDraftState.value;
		},
		{ deep: true, immediate: true }
	);

	// Refs for panel validation
	const panelRefs = {
		input: ref(null),
		config: ref(null),
		output: ref(null),
		logic: ref(null),
	};

	/**
	 * Create a draft copy of the node for editing.
	 */
	function createDraft() {
		if (!props.node) return;
		// Deep clone the node
		draftNode.value = deepClone(props.node);
	}

	/**
	 * Update a field value in the draft config.
	 */
	function updateField(fieldname, value, row = null) {
		if (!draftNode.value?.data) return;

		if (row) {
			row[fieldname] = value;
		} else {
			draftNode.value.data[fieldname] = value;
		}

		// We don't mark dirty in the store until Save is clicked
	}

	/**
	 * Validate the entire configuration.
	 * Checks all panels and returns { valid, errors }.
	 */
	async function validate(targetDraft = draftNode.value) {
		showValidation.value = true;
		const errors = [];

		// 1. Canonical Contract Validation (Handles mandatory fields, policies, etc.)
		const contractRes = validateAgainstContract(targetDraft.data);
		if (!contractRes.valid) {
			errors.push(...contractRes.errors);
		}

		// 2. Panel-specific deep validation (Component-level validation)
		for (const [name, panelRef] of Object.entries(panelRefs)) {
			if (panelRef.value && typeof panelRef.value.validate === "function") {
				const res = await panelRef.value.validate();
				if (!res.valid) {
					if (res.errors) errors.push(...res.errors);
					else if (res.message) errors.push(res.message);
				}
			}
		}

		// 3. Global Business Rules
		if (targetDraft.data?.ignore_permissions && !targetDraft.data?.permission_audit_reason) {
			errors.push(__("Permission Audit Reason is required when bypassing permissions."));
		}

		return {
			valid: errors.length === 0,
			errors: [...new Set(errors)],
		};
	}

	/**
	 * Normalize a copied candidate draft before validation; never mutate the live draft.
	 */
	function normalizeCandidate(candidateDraft) {
		if (!candidateDraft?.data) return candidateDraft;
		const doc = candidateDraft.data;

		if (doc.action_type === "Query Records" && doc.operation === "Fetch Records") {
			const permissionPolicy = getOperationFieldOverride(
				doc.action_type,
				"ignore_permissions",
				{ operation: doc.operation }
			);
			if (permissionPolicy.default === 1) {
				doc.ignore_permissions = 1;
			}
		}

		return candidateDraft;
	}

	/**
	 * Save changes back to the source node and close.
	 */
	async function save() {
		if (isSaving.value) return false;

		// Bind the attempt to the exact source node, draft, fetch generation, and
		// modal editing session that initiated validation. A navigation or close
		// while a panel validator awaits must never redirect this draft's commit.
		const sourceNode = props.node;
		const sourceDraft = draftNode.value;
		const validatedDraft = sourceDraft ? deepClone(sourceDraft) : null;
		const validatedDraftSignature = validatedDraft ? stableStringify(validatedDraft) : null;
		const sourceGeneration = ruleStore.fetch_generation;
		const sourceContextGeneration = saveContextGeneration;
		const hasUnchangedDraft = () => {
			if (!sourceDraft || validatedDraftSignature === null) return false;
			try {
				return stableStringify(sourceDraft) === validatedDraftSignature;
			} catch {
				return false;
			}
		};
		const isSourceContextCurrent = () =>
			Boolean(
				sourceNode &&
					validatedDraft &&
					props.modelValue &&
					props.node === sourceNode &&
					draftNode.value === sourceDraft &&
					hasUnchangedDraft() &&
					saveContextGeneration === sourceContextGeneration &&
					ruleStore.fetch_generation === sourceGeneration &&
					graphStore.nodes.includes(sourceNode)
			);

		isSaving.value = true;
		let saveResult;
		try {
			const candidateDraft = normalizeCandidate(deepClone(validatedDraft));
			saveResult = await runConfigSaveLifecycle({
				// Read live domain-store state, not the spread legacy facade.
				isLoading: () => ruleStore.is_loading,
				isContextCurrent: isSourceContextCurrent,
				validate: () => validate(candidateDraft),
				commit: () => {
					if (!sourceNode || !candidateDraft) return;

					const oldValue = sourceNode.data?.rule;
					const newValue = candidateDraft.data?.rule;

					sourceNode.data = deepClone(candidateDraft.data);
					sourceNode.label = candidateDraft.label || candidateDraft.data?.action_label;
					if (draftNode.value) {
						draftNode.value.data = deepClone(candidateDraft.data);
						draftNode.value.label =
							candidateDraft.label || candidateDraft.data?.action_label;
					}

					// Redraw nested nodes when Sub-Rule LinkControl target changes
					if (sourceNode.data.action_type === "Sub-Rule" && oldValue !== newValue) {
						// store.expand_sub_rule_in_graph removed per user request
					}

					store.touch_node(sourceNode.id);
					store.commit_graph_edit();
				},
			});
		} finally {
			isSaving.value = false;
		}

		if (
			saveResult.status === "blocked-loading" ||
			saveResult.status === "blocked-stale-context"
		) {
			return false;
		}

		if (saveResult.status === "invalid") {
			const validation = saveResult.validation;
			const message = validation.errors.map((e) => `<li>${e}</li>`).join("");
			frappe.msgprint({
				title: __("Validation Error"),
				message: `<ul class="text-left" style="list-style-type: disc; padding-left: 20px;">${message}</ul>`,
				indicator: "red",
			});

			// Scroll to first error
			nextTick(() => {
				const firstError = document.querySelector(".has-error, .is-invalid");
				if (firstError) {
					firstError.scrollIntoView({ behavior: "smooth", block: "center" });
				}
			});

			return false;
		}

		emit("save", sourceNode.data);
		emit("update:modelValue", false);
		return true;
	}

	function cancel() {
		saveContextGeneration += 1;
		if (isDirty.value) {
			frappe.confirm(
				__("You have unsaved changes. Are you sure you want to discard them?"),
				() => {
					emit("update:modelValue", false);
				}
			);
		} else {
			emit("update:modelValue", false);
		}
	}

	// Watch for node changes or modal open to refresh draft
	watch(
		() => [props.node, props.modelValue],
		([newNode, isOpen]) => {
			saveContextGeneration += 1;
			if (isOpen && newNode) {
				createDraft();
				initialDraftState.value = null;
				showValidation.value = false;

				// Capture baseline state as soon as draft is created.
				// We wait for a single tick to ensure the child components have received the draft.
				nextTick(() => {
					if (draftNode.value) {
						initialDraftState.value = stableStringify(draftNode.value.data || {});
					}
				});
			}
		},
		{ immediate: true, flush: "sync" }
	);

	return {
		draftNode,
		config,
		isDirty,
		isSaving,
		panelRefs,
		showValidation,
		updateField,
		validate,
		save,
		cancel,
	};
}
