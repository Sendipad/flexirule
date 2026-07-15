import { ref, reactive, computed, watch, nextTick } from "vue";
import { useStore } from "../stores";
import { getContract, validateAgainstContract } from "../../core/contracts.js";
import { deepClone } from "../utils/serialization.js";

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

	const isDirty = ref(false);

	watch(
		[() => draftNode.value?.data, initialDraftState],
		() => {
			if (!props.node || !draftNode.value || initialDraftState.value === null) {
				isDirty.value = false;
				return;
			}
			const current = JSON.stringify(draftNode.value.data || {});
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
	async function validate() {
		showValidation.value = true;
		const errors = [];

		// 1. Canonical Contract Validation (Handles mandatory fields, policies, etc.)
		const contractRes = validateAgainstContract(draftNode.value.data);
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
		if (
			draftNode.value.data?.ignore_permissions &&
			!draftNode.value.data?.permission_audit_reason
		) {
			errors.push(__("Permission Audit Reason is required when bypassing permissions."));
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

				// Capture baseline state as soon as draft is created.
				// We wait for a single tick to ensure the child components have received the draft.
				nextTick(() => {
					if (draftNode.value) {
						initialDraftState.value = JSON.stringify(draftNode.value.data || {});
					}
				});
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
