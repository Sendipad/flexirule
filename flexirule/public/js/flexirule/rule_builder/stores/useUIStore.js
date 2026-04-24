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

	// ── Test Execution Visualization ──
	const test_execution_path = ref([]);
	const test_context = ref({});

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

	function clear_test_result() {
		test_execution_path.value = [];
		test_context.value = {};
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
		test_execution_path,
		test_context,
		local_clipboard,

		// Computed
		has_selection,
		has_test_path,

		// Actions
		select,
		deselect,
		open_config_modal,
		close_config_modal,
		set_test_result,
		clear_test_result,
		navigate_node,
	};
});
