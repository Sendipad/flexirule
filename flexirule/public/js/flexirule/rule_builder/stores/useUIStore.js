/**
 * useUIStore — Selection, modals, sidebar, toolbar state.
 *
 * Follows Frappe builder pattern (workflow_builder/store.js):
 *   - Single Pinia defineStore with Composition API
 *   - Minimal UI-only state, no business logic
 *   - Refs/computed exposed directly
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useUIStore = defineStore("rule-builder-ui", () => {
	// ── Selection ──
	const selected_id = ref(null);
	const show_sidebar = ref(false);
	const local_clipboard = ref(null);

	// ── Config Modal ──
	const show_config_modal = ref(false);
	const config_modal_mode = ref("setup"); // "setup" | "logic"
	const use_modern_layout = ref(true); // Enable unified layout by default
	const show_shortcuts_help = ref(false);

	// ── Debug Session Visualization ──
	const debug_execution_path = ref([]);
	const debug_context = ref({});
	const debug_trace = ref(null);
	const node_execution_state = ref({});
	const current_running_node_id = ref(null);
	const debug_final_status = ref(null);
	const debug_execution_steps = ref([]);
	const last_execution_id = ref(null);
	const show_debug_sidebar = ref(false);

	// ── Derived ──
	const has_selection = computed(() => selected_id.value !== null);
	const has_debug_path = computed(
		() => Array.isArray(debug_execution_path.value) && debug_execution_path.value.length > 0
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

	function set_debug_result(path, context) {
		debug_execution_path.value = path || [];
		debug_context.value = context || {};
	}

	function set_debug_execution_visuals(payload = {}) {
		const path = payload.path_trace || payload.execution_path || [];
		debug_execution_path.value = Array.isArray(path) ? path : [];
		debug_context.value = payload.vars || payload.context_snapshot || {};
		debug_final_status.value = payload.status || null;
		debug_trace.value = payload.execution_trace || null;
		last_execution_id.value = payload.execution_id || payload.execution?.execution_id || null;

		const nodeState = {};
		const steps = [];
		for (let i = 0; i < debug_execution_path.value.length; i++) {
			const entry = debug_execution_path.value[i] || {};
			const nodeId = entry.action_id || entry.node_id || entry.id;
			if (!nodeId) continue;
			const status = entry.status || "success";
			nodeState[nodeId] = { order: i + 1, status, error: entry.error || null };
			steps.push({
				order: i + 1,
				node_id: nodeId,
				action: entry.action || nodeId,
				status,
				error: entry.error || null,
				duration_ms: entry.duration_ms || null,
			});
		}
		node_execution_state.value = nodeState;
		debug_execution_steps.value = steps;
		current_running_node_id.value = null;
		show_debug_sidebar.value = true;
	}

	function clear_debug_result() {
		debug_execution_path.value = [];
		debug_context.value = {};
		debug_trace.value = null;
		node_execution_state.value = {};
		current_running_node_id.value = null;
		debug_final_status.value = null;
		debug_execution_steps.value = [];
		show_debug_sidebar.value = false;
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
		debug_execution_path,
		debug_context,
		debug_trace,
		node_execution_state,
		current_running_node_id,
		debug_final_status,
		debug_execution_steps,
		last_execution_id,
		show_debug_sidebar,
		local_clipboard,

		// Computed
		has_selection,
		has_debug_path,

		// Actions
		select,
		deselect,
		open_config_modal,
		close_config_modal,
		set_debug_result,
		set_debug_execution_visuals,
		clear_debug_result,
		navigate_node,
	};
});
