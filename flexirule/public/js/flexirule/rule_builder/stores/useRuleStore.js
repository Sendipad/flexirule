/**
 * useRuleStore — Rule document lifecycle, fetch/save, processes.
 *
 * Follows Frappe builder pattern (workflow_builder/store.js):
 *   - fetch(): load doc → build graph → setup history
 *   - save_changes(): serialize graph → validate → save doc
 *   - Coordinates all other domain stores
 *
 * Extracted from store.js lines: 12-14, 20-22, 153-259, 747-874, 891-1221
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { normalizeActionType } from "../../core/contracts";
import { getConditionPayload } from "../utils/condition_payload";

import { useGraphStore } from "./useGraphStore";
import { useMetaStore } from "./useMetaStore";
import { useUIStore } from "./useUIStore";
import { useHistoryStore } from "./useHistoryStore";

export const useRuleStore = defineStore("rule-builder-rule", () => {
	// ── Core state ──
	const rule_name = ref(null);
	const rule_doc = ref(null);
	const _is_dirty = ref(false); // Manual override flag if needed
	const is_dirty = computed(() => {
		if (is_read_only.value || is_loading.value) return false;

		const uiStore = useUIStore();
		if (uiStore.is_initializing || uiStore.is_performing_layout) return false;

		if (_is_dirty.value) return true;
		return checkDirty();
	});
	const initial_state = ref(null);
	const settings = ref(null);
	const validation_errors = ref([]);
	const is_loading = ref(false);
	// ── Process / Sub-Rule state ──
	const processes = ref([]);
	const available_rules = ref([]);
	const trigger_event_options = ref([]);
	const trigger_type_options = ref([]);

	// ── Derived ──
	const is_active = computed(() => rule_doc.value?.is_active === 1);
	const is_read_only = computed(() => is_active.value);

	const doc_fields = computed(() => {
		const metaStore = useMetaStore();
		const doctype = rule_doc.value?.document_type;
		if (!doctype || !metaStore.doc_meta[doctype]) return [];
		return metaStore.get_fields_for_doctype(doctype, { alias: "doc", valueMode: "expression" });
	});

	const raw_meta = computed(() => {
		const doctype = rule_doc.value?.document_type;
		if (!doctype) return null;
		return frappe.get_meta(doctype);
	});

	const nodes = computed({
		get: () => useGraphStore().nodes,
		set: (val) => (useGraphStore().nodes = val),
	});

	const edges = computed({
		get: () => useGraphStore().edges,
		set: (val) => (useGraphStore().edges = val),
	});

	// ── Fetch ──
	// Follows Frappe pattern: load doc → sync graph → setup breadcrumbs → setup history
	async function fetch() {
		if (!rule_name.value) return;

		const graphStore = useGraphStore();
		const metaStore = useMetaStore();
		const historyStore = useHistoryStore();
		const uiStore = useUIStore();

		// Guard to prevent redundant fetches
		if (is_loading.value) return;
		is_loading.value = true;
		uiStore.is_initializing = true;
		// Fetch Settings
		try {
			const res = await frappe.call({
				method: "frappe.client.get",
				args: { doctype: "RuleFlow Settings", name: "RuleFlow Settings" },
			});
			settings.value = res.message;
		} catch (e) {
			console.warn("Failed to load RuleFlow Settings");
		}

		const result = await frappe.call({
			method: "frappe.client.get",
			args: { doctype: "Rule", name: rule_name.value },
		});

		if (result.message) {
			frappe.model.sync(result.message);
			rule_doc.value = { ...frappe.get_doc("Rule", rule_name.value) };
		}

		if (rule_doc.value?.document_type) {
			await metaStore.fetch_metadata(rule_doc.value.document_type);
		}

		// Load trigger event options from Rule meta (Frappe pattern)
		if (!trigger_event_options.value.length) {
			await frappe.model.with_doctype("Rule");
			const meta = frappe.get_meta("Rule");
			if (meta && meta.fields) {
				const trigger_field = meta.fields.find((f) => f.fieldname === "trigger_event");
				if (trigger_field && trigger_field.options) {
					trigger_event_options.value = trigger_field.options.split("\n");
				}
				const type_field = meta.fields.find((f) => f.fieldname === "trigger_type");
				if (type_field && type_field.options) {
					trigger_type_options.value = type_field.options.split("\n");
				}
			}
		}

		if (!rule_doc.value) {
			frappe.show_alert({ message: __("Rule not found"), indicator: "orange" });
			is_loading.value = false;
			return;
		}

		await fetch_processes();

		const visual_data = flexirule.utils.safe_json_parse(rule_doc.value.visual_data, []);

		// Build graph from actions (mirrors workflow_builder: get_workflow_elements)
		graphStore.sync_actions_to_graph(rule_doc.value);

		let needs_auto_layout = false;
		if (visual_data && visual_data.length > 0) {
			graphStore.merge_visual_layout(visual_data);

			// Smart layout detection: if stored layout differs from UI preference, re-layout
			const storedPref = visual_data.find((el) => el.type === "ui_preferences")?.layout;
			if (storedPref && storedPref !== uiStore.layout_preference) {
				needs_auto_layout = true;
			}
		} else {
			// Brand new rule or missing visual data
			needs_auto_layout = true;
		}

		if (!graphStore.nodes.length) {
			graphStore.initialize_default_graph(rule_doc.value);
			needs_auto_layout = true;
		}

		graphStore.autoConnectStartNode();
		graphStore.normalize_graph_nodes();

		// Trigger auto-layout only if mismatch or new
		if (needs_auto_layout) {
			const { useRuleGraph } = await import("../composables/useRuleGraph");
			const { layoutGraph } = useRuleGraph();
			nextTick(() => {
				layoutGraph(uiStore.layout_preference);
			});
		}

		setup_breadcrumbs();

		// We wait for nextTick to ensure all reactive changes from
		// graphStore sync and normalize have settled before we capture the baseline.
		await nextTick();
		initial_state.value = JSON.stringify(graphStore.getStateSnapshot());
		_is_dirty.value = false;

		// Ensure App.vue bindings see the nodes/edges immediately
		// by triggering a reactivity update if needed
		nodes.value = [...graphStore.nodes];
		edges.value = [...graphStore.edges];

		historyStore.reset(() => graphStore.getGraphSnapshot());
		is_loading.value = false;

		// Note: is_initializing is kept true until VueFlow reports ready in App.vue
	}

	// ── Save ──
	// Follows Frappe pattern: serialize → validate → save doc → re-fetch
	async function save_changes() {
		if (is_loading.value) return;
		is_loading.value = true;
		frappe.dom.freeze(__("Saving..."));
		const graphStore = useGraphStore();

		try {
			if (is_active.value) {
				frappe.msgprint({
					title: __("Rule Is Active"),
					message: __(
						"Cannot save edits while rule is Active. Use status toggle to move it to Draft first."
					),
					indicator: "orange",
				});
				return;
			}

			graphStore.normalize_graph_nodes();

			// 1. Validate mandatory fields using contract
			const { validateAgainstContract } = await import("../../core/contracts");
			const errors = [];

			for (const node of graphStore.nodes) {
				if (node.type === "start") continue;

				const label = node.data?.action_label || node.label || node.id;

				if (node.type === "selector") {
					errors.push(
						`${label}: ${__("Please configure this action type before saving")}`
					);
					continue;
				}

				const doc = node.data;

				// Deep sync condition_json for validation if missing
				if (doc.action_type === "Condition" && !doc.condition_json && doc.config) {
					doc.condition_json = JSON.stringify(doc.config);
				}

				// Auto-populate hidden mandatory fields
				if (["Document Action", "Assignment", "Notify"].includes(doc.action_type)) {
					if (doc.action_type === "Document Action" && !doc.permission_audit_reason) {
						doc.permission_audit_reason = "System Rule Execution";
					}
					if (!doc.reference_doctype) {
						doc.reference_doctype = rule_doc.value?.document_type;
					}
				}

				// Contract-based validation
				const contractValidation = validateAgainstContract(doc);
				if (!contractValidation.valid) {
					contractValidation.errors.forEach((err) => {
						errors.push(`${label}: ${err}`);
					});
				}
			}

			if (errors.length > 0) {
				const message = errors.map((e) => `<li>${e}</li>`).join("");
				frappe.msgprint({
					title: __("Validation Error"),
					message: `<ul class="text-left">${message}</ul>`,
					indicator: "red",
				});
				return;
			}

			// 2. Prepare doc for save
			const fresh = await frappe.call({
				method: "frappe.client.get",
				args: { doctype: "Rule", name: rule_name.value },
			});

			const currentIsActive = rule_doc.value.is_active;
			frappe.model.sync(fresh.message);
			let doc = frappe.get_doc("Rule", rule_name.value);
			doc.is_active = currentIsActive;

			const startNode = graphStore.nodes.find((el) => el.type === "start");
			doc.trigger_condition = serializeField(startNode?.data?.trigger_condition);
			doc.compiled_expression = null;

			if (startNode?.data) {
				doc.trigger_type = startNode.data.trigger_type ?? doc.trigger_type;
				doc.document_type = startNode.data.document_type ?? doc.document_type;
				doc.trigger_event = startNode.data.trigger_event ?? doc.trigger_event;
				doc.priority = startNode.data.priority ?? doc.priority;
				doc.execution_mode = startNode.data.execution_mode ?? doc.execution_mode;
				doc.max_execution_time =
					startNode.data.max_execution_time !== undefined
						? startNode.data.max_execution_time
						: doc.max_execution_time;
				doc.debug_mode = startNode.data.debug_mode ? 1 : 0;
				doc.description = startNode.data.description;
				const exposedAsSubrule = startNode.data.exposed_as_subrule ? 1 : 0;
				doc.exposed_as_subrule = exposedAsSubrule;
				const skip_roles = Array.isArray(startNode.data.skip_for_roles)
					? startNode.data.skip_for_roles
					: [];
				doc.skip_for_roles = skip_roles.filter(Boolean).map((role) => ({ role: role }));
				const perms = Array.isArray(startNode.data.permissions)
					? startNode.data.permissions
					: [];
				doc.permissions = perms
					.filter((row) => row && row.role)
					.map((row) => ({
						role: row.role,
						can_execute: row.can_execute ? 1 : 0,
					}));
			}

			// Topological sort for action ordering
			const edgesList = graphStore.edges;
			const orderedNodes = graphStore.getTopologicalSort(graphStore.nodes, edgesList);
			const nodeIdToActionId = new Map(
				graphStore.nodes
					.map((node) => [node.id, getActionIdForNode(node)])
					.filter(([nodeId, actionId]) => nodeId && actionId)
			);
			const resolveActionId = (nodeId) => nodeIdToActionId.get(nodeId) || nodeId || null;

			const uiStore = useUIStore();
			doc.visual_data = JSON.stringify(
				canonicalizeGraphData(
					graphStore.get_visual_data_payload(
						uiStore.layout_preference ||
							(settings.value?.layout_direction === "Top to Bottom" ? "TB" : "LR")
					),
					nodeIdToActionId
				)
			);

			doc.actions = orderedNodes.map((node, idx) => {
				const outgoing = edgesList.filter((e) => e.source === node.id);
				let true_edge = outgoing.find(
					(e) => e.sourceHandle === "true" || e.sourceHandle === "default"
				);
				const false_edge = outgoing.find((e) => e.sourceHandle === "false");

				const is_start_node = node.type === "start";
				const action_type = is_start_node
					? "Entry Action"
					: normalizeActionType(node.data?.action_type || "Process");

				if (is_start_node && !true_edge) {
					const startOutgoing = edgesList.filter(
						(e) => e.source === "start" || e.source === "root"
					);
					true_edge = startOutgoing.find(
						(e) => e.sourceHandle === "true" || e.sourceHandle === "default"
					);
				}

				let rawConfig = node.data?.config || {};
				if (typeof rawConfig === "string") {
					try {
						rawConfig = JSON.parse(rawConfig);
					} catch (e) {
						rawConfig = {};
					}
				}
				const normalizedConfig =
					graphStore.clean_action_config(rawConfig, {
						actionType: action_type,
						processName: node.data?.process_name,
						operation: node.data?.operation,
					}) || {};
				const conditionPayload =
					action_type === "Condition"
						? getConditionPayload({
								config: node.data?.config,
								condition_json: node.data?.condition_json,
						  })
						: null;

				const finalInputMapping =
					node.data?.input_mapping && node.data.input_mapping.length > 0
						? node.data.input_mapping
						: normalizedConfig.input_mapping;
				if (finalInputMapping) {
					normalizedConfig.input_mapping = finalInputMapping;
				}

				const finalOutputMapping =
					node.data?.output_mapping && node.data.output_mapping.length > 0
						? node.data.output_mapping
						: normalizedConfig.output_mapping;
				if (finalOutputMapping) {
					normalizedConfig.output_mapping = finalOutputMapping;
				}

				if (action_type === "Sub-Rule" && node.data?.rule) {
					normalizedConfig.sub_rule_name = node.data.rule;
				}

				const finalConfig =
					action_type === "Condition"
						? conditionPayload || normalizedConfig
						: normalizedConfig;

				return {
					name: node.data?.name,
					idx: idx + 1,
					action_id: resolveActionId(node.id),
					action_label: node.data?.action_label || node.label,
					action_type: action_type,
					is_enabled: node.data?.is_enabled !== undefined ? node.data.is_enabled : 1,
					process_name: node.data?.process_name,
					operation: node.data?.operation,
					config: serializeField(finalConfig),
					target_field: node.data?.target_field,
					value_template: node.data?.value_template,
					compiled_expression: node.data?.compiled_expression,
					condition_json:
						action_type === "Condition" ? serializeField(finalConfig) : null,
					on_error: node.data?.on_error || "Stop",
					timeout: node.data?.timeout || 30,
					priority: node.data?.priority || 0,
					retry_count: node.data?.retry_count || 0,
					return_variable: node.data?.return_variable,
					rule: node.data?.rule,
					is_async: node.data?.is_async || 0,
					skip_conditions:
						node.data?.skip_conditions !== undefined ? node.data.skip_conditions : 1,
					skip_permissions: node.data?.skip_permissions || 0,
					next_step_if_true: resolveActionId(true_edge?.target),
					next_step_if_false: resolveActionId(false_edge?.target),
					input_source: node.data?.input_source,
					reference_doctype: node.data?.reference_doctype,
					reference_docname: node.data?.reference_docname,
					mutation_mode: node.data?.mutation_mode,
					return_type: node.data?.return_type,
					resolved_output_schema: serializeField(node.data?.resolved_output_schema),
				};
			});

			// 3. Backend validation precheck (draft mode: relaxed for building)
			validation_errors.value = []; // Clear previous errors

			const validationPayload = {
				name: doc.name,
				is_active: doc.is_active,
				trigger_type: doc.trigger_type,
				document_type: doc.document_type,
				trigger_event: doc.trigger_event,
				actions: doc.actions.map((row) => ({ ...row })),
			};
			const backendValidation = await frappe.call({
				method: "flexirule.ruleflow.api.validate_rule_document",
				args: { doc: validationPayload, mode: "draft" },
			});
			if (backendValidation?.message && backendValidation.message.valid === false) {
				validation_errors.value = backendValidation.message.errors || [];
				const message = validation_errors.value.map((e) => `<li>${e}</li>`).join("");
				frappe.msgprint({
					title: __("Validation Error"),
					message: `<ul class="text-left">${message}</ul>`,
					indicator: "red",
				});
				return;
			}

			// Show warnings as non-blocking alerts
			if (backendValidation?.message?.warnings?.length) {
				backendValidation.message.warnings.forEach((w) => {
					frappe.show_alert({ message: w, indicator: "orange" });
				});
			}

			await frappe.call({ method: "frappe.client.save", args: { doc } });
			frappe.toast(__("Saved"));
			await fetch();
			clear_dirty();
		} catch (e) {
			console.error("FlexiRule: Save failed", e);
			const errorMsg =
				e.message || (typeof e === "string" ? e : __("Unknown error occurred during save"));
			frappe.msgprint({
				title: __("Critical Error"),
				message: errorMsg,
				indicator: "red",
			});
		} finally {
			is_loading.value = false;
			frappe.dom.unfreeze();
		}
	}

	// ── Lifecycle Transitions (Phase 2: State Machine) ──
	// Uses the backend lifecycle service for validated state transitions
	async function activate_rule() {
		if (is_active.value || is_loading.value) return;
		is_loading.value = true;

		if (is_dirty.value) {
			const confirmed = await new Promise((resolve) => {
				frappe.confirm(
					__("You have unsaved changes. Save and activate now?"),
					() => resolve(true),
					() => resolve(false)
				);
			});
			if (!confirmed) return;
			await save_changes();
		}

		try {
			const result = await frappe.call({
				method: "flexirule.ruleflow.api.transition_rule",
				args: {
					rule_name: rule_name.value,
					target_status: "Active",
				},
			});

			await fetch();
			frappe.show_alert({
				message: result.message?.message || __("Rule activated and locked"),
				indicator: "green",
			});
		} catch (e) {
			// The lifecycle service returns structured validation errors
			const errorMsg = e.message || e._server_messages || __("Activation failed");
			frappe.msgprint({
				title: __("Cannot Activate"),
				message: errorMsg,
				indicator: "red",
			});
		} finally {
			is_loading.value = false;
		}
	}

	async function deactivate_rule() {
		if (!is_active.value || is_loading.value) return;
		is_loading.value = true;

		try {
			const result = await frappe.call({
				method: "flexirule.ruleflow.api.transition_rule",
				args: {
					rule_name: rule_name.value,
					target_status: "Draft",
				},
			});

			await fetch();
			frappe.show_alert({
				message: result.message?.message || __("Rule unlocked for editing"),
				indicator: "blue",
			});
		} catch (e) {
			frappe.msgprint({
				title: __("Unlock Failed"),
				message: e.message || __("Unknown error"),
				indicator: "red",
			});
		} finally {
			is_loading.value = false;
		}
	}

	/**
	 * Simulate rule execution (Phase 2 Testing API).
	 * Runs dry-run mode without side effects.
	 */
	async function simulate_rule(docname) {
		if (!rule_name.value || !docname) return null;

		try {
			const result = await frappe.call({
				method: "flexirule.ruleflow.api.simulate_rule",
				args: {
					rule_name: rule_name.value,
					docname: docname,
				},
			});

			const data = result.message;
			if (data) {
				const uiStore = useUIStore();
				uiStore.set_test_execution_visuals(data);
			}
			return data;
		} catch (e) {
			console.error("FlexiRule: Simulation failed", e);
			return null;
		}
	}

	/**
	 * Get predicted execution path (Phase 2 Testing API).
	 * Evaluates conditions without running handlers.
	 */
	async function preview_execution(docname) {
		if (!rule_name.value || !docname) return null;

		try {
			const result = await frappe.call({
				method: "flexirule.ruleflow.api.get_execution_preview",
				args: {
					rule_name: rule_name.value,
					docname: docname,
				},
			});
			return result.message;
		} catch (e) {
			console.error("FlexiRule: Preview failed", e);
			return null;
		}
	}

	// ── Dirty tracking ──
	function mark_dirty() {
		const uiStore = useUIStore();
		if (
			is_read_only.value ||
			is_loading.value ||
			uiStore.is_initializing ||
			uiStore.is_performing_layout
		) {
			return;
		}

		if (checkDirty()) {
			_is_dirty.value = true;
			const historyStore = useHistoryStore();
			const graphStore = useGraphStore();
			historyStore.commit(() => graphStore.getGraphSnapshot());
		}
	}

	function mark_position_change() {
		const uiStore = useUIStore();
		if (
			is_read_only.value ||
			is_loading.value ||
			uiStore.is_initializing ||
			uiStore.is_performing_layout
		) {
			return;
		}

		if (checkDirty()) {
			_is_dirty.value = true;
			const graphStore = useGraphStore();
			const historyStore = useHistoryStore();
			historyStore.commit(() => graphStore.getGraphSnapshot());
		}
	}

	function checkDirty() {
		if (is_read_only.value || !initial_state.value) return false;
		const graphStore = useGraphStore();

		// Access nodes/edges for reactivity
		const _nodes = graphStore.nodes;
		const _edges = graphStore.edges;

		const current = JSON.stringify(graphStore.getStateSnapshot());
		return current !== initial_state.value;
	}

	/**
	 * Reset the rule's initial state to the current graph snapshot.
	 * Used after fetches, saves, and initial layout settling.
	 */
	function clear_dirty() {
		const graphStore = useGraphStore();
		initial_state.value = JSON.stringify(graphStore.getStateSnapshot());
		_is_dirty.value = false;
	}

	/**
	 * Sync only positions to the initial state baseline.
	 * Used after layout operations to ensure the new positions don't
	 * trigger a dirty state, while preserving other unsaved changes.
	 */
	function sync_initial_state_positions() {
		if (!initial_state.value) return;

		const graphStore = useGraphStore();
		const currentSnapshot = graphStore.getStateSnapshot();
		let initialSnapshot;
		try {
			initialSnapshot = JSON.parse(initial_state.value);
		} catch (e) {
			return;
		}

		// Map current positions by ID
		const currentPositions = new Map(
			currentSnapshot.filter((el) => el.position).map((el) => [el.id, el.position])
		);

		// Update initial snapshot with current positions
		const updatedInitialSnapshot = initialSnapshot.map((el) => {
			if (el.position && currentPositions.has(el.id)) {
				return {
					...el,
					position: currentPositions.get(el.id),
				};
			}
			return el;
		});

		initial_state.value = JSON.stringify(updatedInitialSnapshot);
	}

	// ── UI Helpers (Delegated to UI Store) ──
	function open_config(nodeId) {
		const uiStore = useUIStore();
		uiStore.select(nodeId);
		if (settings.value?.action_config_mode === "Dialog") {
			uiStore.open_config_modal();
		} else {
			uiStore.show_sidebar = true;
		}
	}

	function next_config_node() {
		const uiStore = useUIStore();
		const graphStore = useGraphStore();
		uiStore.config_modal_mode = "setup";
		uiStore.navigate_node(graphStore.nodes, 1);
	}

	function prev_config_node() {
		const uiStore = useUIStore();
		const graphStore = useGraphStore();
		uiStore.config_modal_mode = "setup";
		uiStore.navigate_node(graphStore.nodes, -1);
	}

	// ── Undo/Redo coordination ──
	function undo() {
		if (is_read_only.value) return;
		const historyStore = useHistoryStore();
		const graphStore = useGraphStore();
		historyStore.undo((snap) => {
			graphStore.applyGraphSnapshot(snap);
			// Force a reactivity check for is_dirty after undo
			_is_dirty.value = checkDirty();
		});
	}

	function redo() {
		if (is_read_only.value) return;
		const historyStore = useHistoryStore();
		const graphStore = useGraphStore();
		historyStore.redo((snap) => {
			graphStore.applyGraphSnapshot(snap);
			// Force a reactivity check for is_dirty after redo
			_is_dirty.value = checkDirty();
		});
	}

	function can_undo() {
		return useHistoryStore().can_undo;
	}

	function can_redo() {
		return useHistoryStore().can_redo;
	}

	// ── Field serialization ──
	function serializeField(val) {
		if (val === undefined || val === null) return null;
		if (typeof val === "string") return val;
		try {
			const plain = JSON.parse(JSON.stringify(val));
			return JSON.stringify(plain);
		} catch (e) {
			console.warn("FlexiRule: Field serialization failed", e, val);
			return null;
		}
	}

	function getActionIdForNode(node) {
		return node?.data?.action_id || node?.id || null;
	}

	function canonicalizeGraphData(graphData, nodeIdToActionId) {
		return (graphData || []).map((element) => {
			const canonical = { ...element };

			if (canonical.id && nodeIdToActionId.has(canonical.id)) {
				canonical.id = nodeIdToActionId.get(canonical.id);
			}
			if (canonical.source && nodeIdToActionId.has(canonical.source)) {
				canonical.source = nodeIdToActionId.get(canonical.source);
			}
			if (canonical.target && nodeIdToActionId.has(canonical.target)) {
				canonical.target = nodeIdToActionId.get(canonical.target);
			}
			if (canonical.data) {
				const data = { ...canonical.data };
				if (data.action_id && nodeIdToActionId.has(data.action_id)) {
					data.action_id = nodeIdToActionId.get(data.action_id);
				} else if (element.id && nodeIdToActionId.has(element.id)) {
					data.action_id = nodeIdToActionId.get(element.id);
				}
				if (data.next_step_if_true && nodeIdToActionId.has(data.next_step_if_true)) {
					data.next_step_if_true = nodeIdToActionId.get(data.next_step_if_true);
				}
				if (data.next_step_if_false && nodeIdToActionId.has(data.next_step_if_false)) {
					data.next_step_if_false = nodeIdToActionId.get(data.next_step_if_false);
				}
				canonical.data = data;
			}

			return canonical;
		});
	}

	// ── Process/SubRule fetching ──
	async function fetch_processes() {
		try {
			const response = await frappe.call({
				method: "flexirule.ruleflow.doctype.process.process.get_process_list",
			});
			processes.value = response.message || [];
		} catch (e) {
			console.error("FlexiRule: Failed to fetch processes:", e);
			frappe.show_alert({
				message: __("Failed to load processes"),
				indicator: "red",
			});
			processes.value = [];
		}
	}

	async function get_process_operations(process_name) {
		const raw_ops = await flexirule.utils.get_process_operations(process_name);

		const document_type = rule_doc.value?.document_type;
		const doctype_meta = document_type ? frappe.get_meta(document_type) : null;

		return flexirule.utils.filter_eligible_operations(raw_ops, {
			document_type,
			has_doc: true,
			doctype_meta: doctype_meta
				? {
						issingle: doctype_meta.issingle,
						istable: doctype_meta.istable,
						is_submittable: doctype_meta.is_submittable,
						track_changes: doctype_meta.track_changes,
				  }
				: null,
		});
	}

	async function get_operation_config_fields(process_name, operation_name, frm) {
		return await flexirule.utils.get_operation_config_fields(process_name, operation_name, frm);
	}

	async function fetch_available_rules() {
		try {
			const result = await frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Rule",
					fields: [
						"name",
						"rule_name",
						"trigger_type",
						"trigger_event",
						"is_active",
						"exposed_as_subrule",
						"document_type",
					],
					filters: {
						trigger_type: "Callable Event",
						exposed_as_subrule: 1,
						is_active: 1,
						name: ["!=", rule_name.value || ""],
					},
					limit: 0,
				},
			});
			available_rules.value = result.message || [];
		} catch (e) {
			console.error("FlexiRule: Failed to fetch rules:", e);
			available_rules.value = [];
		}
	}

	// ── Breadcrumbs (Frappe pattern) ──
	function setup_breadcrumbs() {
		let breadcrumbs = `
			<li><a href="/app/rule">${__("Rule")}</a></li>
			<li><a href="/app/rule/${rule_name.value}">${__(
			rule_doc.value?.rule_name || rule_name.value
		)}</a></li>
			<li class="disabled"><a href="#">${__("Builder")}</a></li>
		`;
		frappe.breadcrumbs.clear();
		frappe.breadcrumbs.$breadcrumbs.append(breadcrumbs);
	}

	return {
		// State
		rule_name,
		rule_doc,
		settings,
		is_dirty,
		is_loading,
		processes,
		available_rules,
		trigger_event_options,
		trigger_type_options,
		nodes,
		edges,

		// Computed
		is_active,
		is_read_only,
		doc_fields,
		raw_meta,

		// Lifecycle
		fetch,
		save_changes,
		activate_rule,
		deactivate_rule,

		// Testing (Phase 2)
		simulate_rule,
		preview_execution,

		// Dirty tracking
		mark_dirty,
		mark_position_change,
		clear_dirty,
		sync_initial_state_positions,

		// Undo/Redo coordination
		undo,
		redo,
		can_undo,
		can_redo,

		// Processes/SubRules
		fetch_processes,
		get_process_operations,
		get_operation_config_fields,
		fetch_available_rules,

		// UI/Legacy
		open_config,
		next_config_node,
		prev_config_node,
	};
});
