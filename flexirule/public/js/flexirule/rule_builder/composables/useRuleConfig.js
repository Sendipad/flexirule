import { ref, reactive, computed, watch, nextTick } from "vue";
import { useGraphStore, useRuleStore, useStore, useUIStore } from "../stores";
import { validateAgainstContract } from "../../core/contracts.js";
import { deepClone } from "../utils/serialization.js";
import { stableStringify } from "../utils/stable_serialization.mjs";
import { runConfigSaveLifecycle } from "../utils/config_save_lifecycle.mjs";
import { normalizeCandidateDraft } from "../utils/candidate_normalization.mjs";
import {
	getDirtyConfigDraftEntries,
	getOrCreateConfigDraftEntry,
} from "../utils/config_draft_session.js";

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
	const uiStore = useUIStore();
	const store = useStore();
	const draftNode = ref(null);
	const showValidation = ref(false);
	const config = computed(() => draftNode.value?.data || {});

	// Capture initial draft state after a short delay to allow background sync to settle
	const initialDraftState = ref(null);

	const isDirty = ref(false);
	const isSaving = ref(false);
	const showDiscardConfirmation = ref(false);
	let discardReturnFocus = null;
	// Invalidates pending saves when the modal is cancelled or the editing context changes.
	let saveContextGeneration = 0;
	// Reactive Map entries preserve visited drafts and drive session-wide dirty tracking.
	const draftEntries = reactive(new Map());
	const activeNodeId = ref(null);

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
	 * Drop session-local drafts after the modal has been closed.
	 */
	function resetDraftSession() {
		draftEntries.clear();
		activeNodeId.value = null;
		draftNode.value = null;
		initialDraftState.value = null;
		showValidation.value = false;
	}

	function createDraft(sourceNode) {
		if (!sourceNode) {
			draftNode.value = null;
			initialDraftState.value = null;
			activeNodeId.value = null;
			return null;
		}

		const entry = getOrCreateConfigDraftEntry(draftEntries, sourceNode);
		if (!entry) return null;

		// Store the Vue proxy as well as the entry so edits remain reactive while
		// the draft is cached during navigation to another action.
		draftNode.value = entry.draftNode;
		entry.draftNode = draftNode.value;
		activeNodeId.value = entry.nodeId;
		initialDraftState.value = entry.initialDraftState;
		return entry;
	}

	function captureDraftBaseline(entry) {
		if (!entry || entry.initialDraftState !== null) return;

		nextTick(() => {
			if (
				!props.modelValue ||
				draftEntries.get(entry.nodeId) !== entry ||
				entry.initialDraftState !== null
			) {
				return;
			}

			// Keep the existing post-mount baseline behavior: config panels may
			// initialize draft defaults during their first render.
			entry.initialDraftState = stableStringify(entry.draftNode.data || {});
			if (activeNodeId.value === entry.nodeId && draftNode.value === entry.draftNode) {
				initialDraftState.value = entry.initialDraftState;
			}
		});
	}

	function getDirtyDraftEntriesInFlowOrder() {
		const dirtyByNodeId = new Map(
			getDirtyConfigDraftEntries(draftEntries).map((entry) => [entry.nodeId, entry])
		);
		return graphStore.orderedConfigurableNodes
			.map((node) => dirtyByNodeId.get(node.id))
			.filter(Boolean);
	}

	function getDraftActionLabel(entry) {
		const node = entry?.draftNode;
		return (
			node?.data?.action_label ||
			node?.label ||
			node?.data?.label ||
			node?.data?.action_type ||
			entry?.nodeId ||
			__("Unnamed action")
		);
	}

	function escapeHtml(value) {
		return String(value ?? "").replace(/[&<>"']/g, (character) => {
			const entities = {
				"&": "&amp;",
				"<": "&lt;",
				">": "&gt;",
				'"': "&quot;",
				"'": "&#39;",
			};
			return entities[character];
		});
	}

	const hasUnsavedChanges = computed(() => getDirtyConfigDraftEntries(draftEntries).length > 0);

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
	 * Save the active action draft back to the source graph node.
	 */
	async function save() {
		if (isSaving.value) return false;

		const activeEntry = draftEntries.get(activeNodeId.value);
		const sourceNode = props.node;
		const sourceDraft = draftNode.value;
		if (!activeEntry || !sourceNode || !sourceDraft || activeEntry.draftNode !== sourceDraft) {
			return false;
		}

		// Never apply an old draft over a graph node changed by another workflow.
		// The draft remains in the session so the user can review/reopen safely.
		const sourceIsCurrent = () => {
			try {
				return (
					!activeEntry.isStale &&
					activeEntry.sourceNode === sourceNode &&
					stableStringify(sourceNode.data || {}) === activeEntry.sourceDataSignature &&
					graphStore.nodes.includes(sourceNode)
				);
			} catch {
				return false;
			}
		};
		if (!sourceIsCurrent()) {
			activeEntry.isStale = true;
			frappe.msgprint({
				title: __("Configuration Changed"),
				message: __(
					"The rule graph changed while this action was being configured. Your draft has been preserved, but it cannot be saved over the newer graph. Close and reopen the configuration after reviewing the latest state."
				),
				indicator: "orange",
			});
			return false;
		}

		// Bind the attempt to the exact source node, draft, fetch generation, and
		// modal editing session that initiated validation. Navigation while a panel
		// validator awaits must never redirect this draft's commit.
		const sourceDraftSignature = stableStringify(sourceDraft);
		const validatedDraft = deepClone(sourceDraft);
		normalizeCandidateDraft(validatedDraft);
		const sourceGeneration = ruleStore.fetch_generation;
		const sourceContextGeneration = saveContextGeneration;
		const hasUnchangedDraft = () => {
			try {
				return stableStringify(sourceDraft) === sourceDraftSignature;
			} catch {
				return false;
			}
		};
		const isSourceContextCurrent = () =>
			Boolean(
				props.modelValue &&
					props.node === sourceNode &&
					draftNode.value === sourceDraft &&
					activeNodeId.value === activeEntry.nodeId &&
					draftEntries.get(activeEntry.nodeId) === activeEntry &&
					!activeEntry.isStale &&
					sourceIsCurrent() &&
					hasUnchangedDraft() &&
					saveContextGeneration === sourceContextGeneration &&
					ruleStore.fetch_generation === sourceGeneration
			);

		isSaving.value = true;
		let saveResult;
		try {
			saveResult = await runConfigSaveLifecycle({
				// Read live domain-store state, not the spread legacy facade.
				isLoading: () => ruleStore.is_loading,
				isContextCurrent: isSourceContextCurrent,
				validate: () => validate(validatedDraft),
				commit: () => {
					const oldValue = sourceNode.data?.rule;
					const newValue = validatedDraft.data?.rule;

					sourceNode.data = deepClone(validatedDraft.data);
					sourceNode.label = validatedDraft.label || validatedDraft.data?.action_label;
					// Keep the visible draft aligned with normalization performed for Save.
					sourceDraft.data = deepClone(sourceNode.data);
					sourceDraft.label = sourceNode.label;
					// Rebase the saved entry before touch_node replaces the graph-node
					// object. The current modal draft stays valid and clean afterwards.
					activeEntry.sourceDataSignature = stableStringify(sourceNode.data || {});
					activeEntry.initialDraftState = stableStringify(sourceDraft.data || {});
					initialDraftState.value = activeEntry.initialDraftState;

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

		if (hasUnsavedChanges.value) {
			frappe.show_alert({
				message: __("This action was saved. Other actions still have unsaved changes."),
				indicator: "orange",
			});
		} else {
			emit("update:modelValue", false);
		}
		return true;
	}

	function keepEditing() {
		if (!showDiscardConfirmation.value) return;

		showDiscardConfirmation.value = false;
		discardReturnFocus = null;
		const firstDirtyEntry = getDirtyDraftEntriesInFlowOrder()[0];
		if (firstDirtyEntry) {
			// Keep Editing takes users to the earliest unsaved action so they can
			// work through outstanding drafts in rule-flow order.
			uiStore.config_modal_mode = "setup";
			nextTick(() => uiStore.select(firstDirtyEntry.nodeId));
		}
	}

	function discardChanges() {
		if (isSaving.value || !showDiscardConfirmation.value) return false;

		showDiscardConfirmation.value = false;
		discardReturnFocus = null;
		// Pending save attempts are invalidated only after explicit discard.
		saveContextGeneration += 1;
		emit("update:modelValue", false);
		return true;
	}

	function cancel() {
		// Let Frappe's native confirmation handle Escape / dismiss while it is open.
		if (showDiscardConfirmation.value) return false;

		// Don't interrupt an async validation/commit. Save owns the editing
		// context until it has settled.
		if (isSaving.value || !props.modelValue) return false;

		if (!hasUnsavedChanges.value && !isDirty.value) {
			saveContextGeneration += 1;
			emit("update:modelValue", false);
			return true;
		}

		discardReturnFocus = typeof document !== "undefined" ? document.activeElement : null;
		const dirtyEntries = getDirtyDraftEntriesInFlowOrder();
		const actionList = dirtyEntries
			.map((entry) => "• " + escapeHtml(getDraftActionLabel(entry)))
			.join("<br>");
		// frappe.confirm wraps its message in a paragraph element, so keep the
		// supplied markup phrasing-only and use line breaks instead of nested
		// block elements. This keeps every action label visible in the dialog.
		const message = [
			escapeHtml(__("The following actions have unsaved configuration changes:")),
			actionList,
			escapeHtml(
				__(
					"Keep editing will open the first action in this list. Discard changes will discard all listed modal drafts."
				)
			),
			escapeHtml(
				__(
					"Changes already saved to individual actions remain in the rule builder. You may still need to click Save Rule to persist the rule."
				)
			),
		].join("<br><br>");
		showDiscardConfirmation.value = true;
		const confirmation = frappe.confirm(
			message,
			() => discardChanges(),
			null,
			__("Discard changes"),
			__("Keep editing")
		);

		// Bootstrap ignores hide() while the modal is still entering. Queue a
		// close requested during that transition and perform it once shown.
		let closeWhenShown = false;
		const requestConfirmationClose = () => {
			if (!confirmation.display) {
				closeWhenShown = true;
				return;
			}
			closeWhenShown = false;
			confirmation.hide();
		};
		confirmation.$wrapper.one("shown.bs.modal.fxrDiscardConfirmation", () => {
			if (closeWhenShown) requestConfirmationClose();
		});

		// Own the secondary action explicitly; both it and Escape use the same
		// transition-aware close path.
		confirmation
			.get_secondary_btn()
			.off("click")
			.on("click.fxrDiscardConfirmation", (event) => {
				event.preventDefault();
				requestConfirmationClose();
			});

		// Handle Escape at the confirmation itself and stop the same key event
		// from reaching the config modal's global Escape shortcut.
		confirmation.$wrapper.on("keydown.fxrDiscardConfirmation", (event) => {
			if (event.key !== "Escape" && event.which !== 27) return;
			event.preventDefault();
			event.stopPropagation();
			requestConfirmationClose();
		});

		// Resume editing only after Bootstrap has removed the dialog backdrop.
		confirmation.$wrapper.one("hidden.bs.modal", () => {
			confirmation.$wrapper.off(".fxrDiscardConfirmation");
			if (showDiscardConfirmation.value) keepEditing();
		});
		return false;
	}

	// Watch for node changes or modal open to refresh draft
	watch(
		() => [props.node, props.modelValue, ruleStore.fetch_generation],
		([newNode, isOpen]) => {
			saveContextGeneration += 1;
			if (!isOpen) {
				showDiscardConfirmation.value = false;
				discardReturnFocus = null;
				resetDraftSession();
				return;
			}
			if (!newNode) {
				draftNode.value = null;
				initialDraftState.value = null;
				activeNodeId.value = null;
				return;
			}

			const entry = createDraft(newNode);
			showValidation.value = false;
			if (entry?.initialDraftState == null) {
				captureDraftBaseline(entry);
			}
		},
		{ immediate: true, flush: "sync" }
	);

	return {
		draftNode,
		config,
		isDirty,
		hasUnsavedChanges,
		isSaving,
		showDiscardConfirmation,
		panelRefs,
		showValidation,
		updateField,
		validate,
		save,
		cancel,
		keepEditing,
		discardChanges,
	};
}
