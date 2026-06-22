/**
 * useUIStore — Selection, modals, sidebar, toolbar state.
 *
 * Follows Frappe builder pattern (workflow_builder/store.js):
 *   - Single Pinia defineStore with Composition API
 *   - Minimal UI-only state, no business logic
 *   - Refs/computed exposed directly
 */
import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";

export const useUIStore = defineStore("rule-builder-ui", () => {
	// ── Selection ──
	const selected_id = ref(null);
	const show_sidebar = ref(false);
	const local_clipboard = ref(null);
	const is_initializing = ref(false);
	const is_performing_layout = ref(false);
	const layout_preference = ref("LR"); // "LR" | "TB"
	const show_layout_mismatch_banner = ref(false);
	const dismissed_layout_banner = ref(false);

	// ── Developer / Debug ──
	const is_field_reveal_active = ref(false);
	const is_developer_mode = computed(() => {
		return !!(window.frappe && frappe.boot && frappe.boot.developer_mode);
	});

	// ── Config Modal ──
	const show_config_modal = ref(false);
	const config_modal_mode = ref("setup"); // "setup" | "logic"
	const use_modern_layout = ref(true); // Enable unified layout by default
	const show_shortcuts_help = ref(false);

	// ── Test Execution Visualization ──
	const test_execution_path = ref([]);
	const test_context = ref({});
	const node_execution_state = ref({});
	const current_running_node_id = ref(null);
	const test_final_status = ref(null);
	const test_execution_steps = ref([]);
	const test_selected_step_index = ref(null);
	const show_test_sidebar = ref(false);

	// ── Multi-document Visualization ──
	const test_multi_results = ref([]);
	const test_current_multi_index = ref(0);

	// ── Derived ──
	const has_selection = computed(() => selected_id.value !== null);
	const has_test_path = computed(
		() => Array.isArray(test_execution_path.value) && test_execution_path.value.length > 0
	);

	// ── Actions ──
	function select(nodeId) {
		selected_id.value = nodeId;
	}

	function deselect() {
		selected_id.value = null;
	}

	function open_config_modal(mode = "setup") {
		config_modal_mode.value = mode;
		show_config_modal.value = true;
	}

	function close_config_modal() {
		show_config_modal.value = false;
	}

	function set_test_result(path, context) {
		test_execution_path.value = path || [];
		test_context.value = context || {};
	}

	function set_test_execution_visuals(payload = {}) {
		const path = payload.path_trace || payload.execution_path || [];
		test_execution_path.value = Array.isArray(path) ? path : [];
		test_context.value = payload.vars || payload.context_snapshot || {};
		test_final_status.value = payload.status || null;

		const nodeState = {};
		const steps = [];
		const executionCounts = {};

		for (let i = 0; i < test_execution_path.value.length; i++) {
			const entry = test_execution_path.value[i] || {};
			const nodeId = entry.action_id || entry.node_id || entry.id;
			if (!nodeId) continue;

			// Track execution counts for loop labeling
			executionCounts[nodeId] = (executionCounts[nodeId] || 0) + 1;
			const currentCount = executionCounts[nodeId];

			const status = entry.status || "success";
			nodeState[nodeId] = {
				order: i + 1,
				status,
				error: entry.error || null,
				executed: true,
			};

			let actionLabel = entry.action || nodeId;
			// If node is executed more than once, add (N) suffix
			// We scan the whole path to see if it will eventually be executed more than once
			// or just check if it was already executed once.
			// Actually, to know if we SHOULD add (1) to the first execution, we need a lookahead or pre-pass.
			steps.push({
				...entry,
				order: i + 1,
				node_id: nodeId,
				action: actionLabel,
				execution_count: currentCount,
				type: entry.type,
				status,
				error: entry.error || null,
				duration_ms: entry.duration_ms !== undefined ? entry.duration_ms : null,
				input: entry.input || null,
				output: entry.output || null,
				result: entry.result !== undefined ? entry.result : null,
			});
		}

		// Second pass to append (N) to labels if multiple executions exist
		steps.forEach((step) => {
			if (executionCounts[step.node_id] > 1) {
				step.action = `${step.action} (${step.execution_count})`;
			}
		});
		node_execution_state.value = nodeState;
		test_execution_steps.value = steps;
		current_running_node_id.value = null;
		test_selected_step_index.value = steps.length > 0 ? 0 : null;
		show_test_sidebar.value = true;
	}

	function clear_test_result() {
		test_execution_path.value = [];
		test_context.value = {};
		node_execution_state.value = {};
		current_running_node_id.value = null;
		test_final_status.value = null;
		test_execution_steps.value = [];
		test_selected_step_index.value = null;
		show_test_sidebar.value = false;
		test_multi_results.value = [];
		test_current_multi_index.value = 0;
	}

	function add_test_progress_result(payload) {
		test_multi_results.value.push(payload);
		if (test_multi_results.value.length === 1) {
			set_active_multi_result(0);
		}
	}

	function set_active_multi_result(index) {
		if (index >= 0 && index < test_multi_results.value.length) {
			test_current_multi_index.value = index;
			set_test_execution_visuals(test_multi_results.value[index]);
		}
	}

	/**
	 * Navigate to the next or previous node in the node list.
	 * @param {Array} nodes - Current node list from graph store
	 * @param {number} direction - 1 for next, -1 for previous
	 */
	function navigate_node(nodes, direction = 1) {
		if (!selected_id.value || !nodes?.length) return;
		const currentIndex = nodes.findIndex((n) => n.id === selected_id.value);
		if (currentIndex === -1) return;

		const nextIndex = (currentIndex + direction + nodes.length) % nodes.length;
		selected_id.value = nodes[nextIndex].id;
	}

	return {
		// State
		selected_id,
		show_sidebar,
		show_config_modal,
		config_modal_mode,
		use_modern_layout,
		show_shortcuts_help,
		test_execution_path,
		test_context,
		node_execution_state,
		current_running_node_id,
		test_final_status,
		test_execution_steps,
		test_selected_step_index,
		show_test_sidebar,
		local_clipboard,
		test_multi_results,
		test_current_multi_index,
		is_initializing,
		show_layout_mismatch_banner,
		dismissed_layout_banner,

		// Computed
		has_selection,
		has_test_path,
		is_field_reveal_active,
		is_developer_mode,

		// Actions
		select,
		deselect,
		open_config_modal,
		close_config_modal,
		set_test_result,
		set_test_execution_visuals,
		clear_test_result,
		navigate_node,
		add_test_progress_result,
		set_active_multi_result,
		layout_preference,
		is_performing_layout,
	};
});
