import { ref, reactive, computed, watch, nextTick } from "vue";
import { useStore } from "../stores";
import { getContract, validateAgainstContract } from "../../core/contracts.js";
import { deepClone } from "../utils/serialization";

/**
 * useRuleConfig
 *
 * Composable to manage the state and lifecycle of a rule node configuration.
 *
 * @param {Object} props - Component props containing the source node
 * @param {Object} emit - Component emit function
 */
export function useRuleConfig(props, emit) {
	const store = useStore();
	const draftNode = ref(null);
	const showValidation = ref(false);
	const config = computed(() => draftNode.value?.data || {});

	// Capture initial draft state after a short delay to allow background sync to settle
	const initialDraftState = ref(null);

	const isDirty = computed(() => {
		if (!props.node || !draftNode.value || initialDraftState.value === null) return false;

		// Compare current draft state with the captured initial state
		const current = JSON.stringify(draftNode.value.data || {});
		return current !== initialDraftState.value;
	});

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
		// Deep clone the node using our utility to preserve reactivity-friendly structures
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
	async function validate() {
		showValidation.value = true;
		const errors = [];
		const actionType = draftNode.value?.data?.action_type || draftNode.value?.type;
		const contract = actionType ? getContract(actionType) : null;
		const operation = draftNode.value?.data?.operation;

		// 1. Contract-based Mandatory Field Validation
		if (contract && contract.mandatory_fields) {
			const reqFields =
				contract.mandatory_fields[operation] || contract.mandatory_fields["*"] || [];
			reqFields.forEach((f) => {
				const val = draftNode.value.data?.[f];
				if (val === undefined || val === null || val === "") {
					// Use a descriptive label for the error message
					const fieldLabel = f
						.replace(/_/g, " ")
						.replace(/\b\w/g, (c) => c.toUpperCase());
					errors.push(
						__("{0} is required for {1}")
							.replace("{0}", fieldLabel)
							.replace("{1}", operation || actionType)
					);
				}
			});
		}

		// 2. Action Label is always good to have
		if (!draftNode.value?.data?.action_label) {
			// errors.push(__("Action Label is required"));
		}

		// 3. Panel-specific validation
		for (const [name, panelRef] of Object.entries(panelRefs)) {
			if (panelRef.value && typeof panelRef.value.validate === "function") {
				const res = await panelRef.value.validate();
				if (!res.valid) {
					if (res.errors) errors.push(...res.errors);
					else if (res.message) errors.push(res.message);
				}
			}
		}

		// 4. Permission Audit Reason (Global requirement when skipping)
		if (
			draftNode.value.data?.skip_permissions &&
			!draftNode.value.data?.permission_audit_reason
		) {
			errors.push(__("Permission Audit Reason is required when bypassing permissions."));
		}

		// 5. Canonical Contract Validation
		const contractRes = validateAgainstContract(draftNode.value.data);
		if (!contractRes.valid) {
			errors.push(...contractRes.errors);
		}

		return {
			valid: errors.length === 0,
			errors: [...new Set(errors)],
		};
	}

	/**
	 * Save changes back to the source node and close.
	 */
	async function save() {
		const validation = await validate();
		if (!validation.valid) {
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

		// Commit changes
		if (props.node && draftNode.value) {
			const oldValue = props.node.data?.rule;
			const newValue = draftNode.value.data?.rule;

			props.node.data = deepClone(draftNode.value.data);
			props.node.label = draftNode.value.label || draftNode.value.data?.action_label;

			// Redraw nested nodes when Sub-Rule LinkControl target changes
			if (props.node.data.action_type === "Sub-Rule" && oldValue !== newValue) {
				// store.expand_sub_rule_in_graph removed per user request
			}

			store.touch_node(props.node.id);
			store.mark_dirty();
		}

		emit("save", props.node.data);
		emit("update:modelValue", false);
		return true;
	}

	function cancel() {
		emit("update:modelValue", false);
	}

	// Watch for node changes or modal open to refresh draft
	watch(
		() => [props.node, props.modelValue],
		([newNode, isOpen]) => {
			if (isOpen && newNode) {
				createDraft();
				initialDraftState.value = null;
				showValidation.value = false;

				// Immediately capture a baseline of the raw data.
				// This prevents the UI from appearing "dirty" immediately upon opening
				// while dynamic components (useActionConfig) are still loading.
				if (draftNode.value) {
					initialDraftState.value = JSON.stringify(draftNode.value.data || {});
				}

				// Optional: Re-baseline after a tick to account for any immediate reactive
				// transformations that happen during component setup, but BEFORE the user interacts.
				nextTick(() => {
					if (draftNode.value && initialDraftState.value === null) {
						initialDraftState.value = JSON.stringify(draftNode.value.data || {});
					}
				});

				// We no longer use a 1000ms timeout which was causing race conditions.
				// If a child component needs to "clean" the state during init,
				// it should do so without triggering mark_dirty in the store.
			}
		},
		{ immediate: true }
	);

	return {
		draftNode,
		config,
		isDirty,
		panelRefs,
		showValidation,
		updateField,
		validate,
		save,
		cancel,
	};
}
