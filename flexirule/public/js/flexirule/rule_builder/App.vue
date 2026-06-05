<template>
	<div class="rule-builder-container" :class="{ 'is-read-only': isReadOnly, 'is-rtl': isRTL }">
		<!-- Main Canvas + Sidebar -->
		<div class="builder-main">
			<div class="canvas-container" ref="flowWrapper" @dragover="onDragOver" @drop="onDrop">
				<VueFlow
					:dir="isRTL ? 'rtl' : 'ltr'"
					:edges-editable="false"
					v-model:nodes="graphStore.nodes"
					v-model:edges="graphStore.edges"
					:default-viewport="{ zoom: 1 }"
					:min-zoom="0.1"
					:max-zoom="4"
					:zoom-on-scroll="false"
					:pan-on-scroll="true"
					:pan-on-scroll-mode="'free'"
					:zoom-on-pinch="true"
					:snap-to-grid="true"
					:snap-grid="[15, 15]"
					:nodes-draggable="!isReadOnly"
					:nodes-connectable="!isReadOnly"
					:elements-selectable="true"
					:selection-on-drag="false"
					:pan-on-drag="true"
					:delete-key-active="!isReadOnly"
					fit-view-on-init
					:edge-types="edgeTypes"
					:class="{ 'is-read-only-flow': isReadOnly }"
					@node-click="onNodeClick"
					@node-dblclick="onNodeDblClick"
					@pane-click="onPaneClick"
					@connect="onConnect"
					@nodes-change="onNodesChange"
					@edges-change="onEdgesChange"
					@edge-click="onEdgeClick"
					@pane-ready="onPaneReady"
				>
					<template #node-start="nodeProps">
						<StartNode v-bind="nodeProps" />
					</template>
					<template #node-process="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-condition="nodeProps">
						<ConditionNode v-bind="nodeProps" />
					</template>
					<template #node-loop="nodeProps">
						<LoopNode v-bind="nodeProps" />
					</template>
					<template #node-stop="nodeProps">
						<StopNode v-bind="nodeProps" />
					</template>
					<template #node-selector="nodeProps">
						<ActionSelectorNode v-bind="nodeProps" />
					</template>
					<template #node-set-value="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-notify="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-wait="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-sub-rule="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-query="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-documentaction="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-raise-error="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-assignment="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>
					<template #node-switch="nodeProps">
						<ProcessNode v-bind="nodeProps" />
					</template>

					<template #edge-add="edgeProps">
						<AddNodeEdge v-bind="edgeProps" @insert-node="insertNodeOnEdge" />
					</template>

					<Background :gap="15" />
					<Panel :position="PanelPosition.TopLeft" class="controls-panel">
						<div class="btn-group controls-row">
							<button
								class="btn btn-sm btn-default"
								@click="zoomIn"
								:title="__('Zoom In')"
							>
								+
							</button>
							<button
								class="btn btn-sm btn-default"
								@click="zoomOut"
								:title="__('Zoom Out')"
							>
								-
							</button>
							<button
								class="btn btn-sm btn-default"
								@click="fitView()"
								:title="__('Fit View')"
							>
								{{ __("Fit") }}
							</button>
						</div>

						<div class="divider-vertical"></div>

						<div v-if="isReadOnly" class="read-only-badge mr-2">
							<i class="fa fa-lock"></i> {{ __("Read Only") }}
						</div>

						<div class="quick-actions-wrap">
							<button
								ref="quickActionsButtonRef"
								class="btn btn-sm btn-default quick-actions-btn"
								@click="toggleQuickActions"
								:title="__('Quick Actions')"
								aria-haspopup="menu"
								:aria-expanded="showQuickActions ? 'true' : 'false'"
							>
								<i class="fa fa-gear"></i>
							</button>
						</div>
					</Panel>
					<Panel
						v-if="uiStore.test_execution_steps?.length"
						:position="PanelPosition.TopRight"
						class="execution-panel"
					>
						<div class="execution-panel-header">
							<strong>{{ __("Test Execution") }}</strong>
							<span class="execution-final-status">{{
								uiStore.test_final_status || __("Unknown")
							}}</span>
						</div>
						<div class="execution-panel-steps">
							<div
								v-for="step in uiStore.test_execution_steps"
								:key="`${step.node_id}-${step.order}`"
								class="execution-step"
								:class="`status-${step.status}`"
							>
								<span>#{{ step.order }}</span>
								<span class="step-label">{{ step.action }}</span>
							</div>
						</div>
					</Panel>
				</VueFlow>
			</div>
			<div
				class="sidebar-container"
				:class="{ 'sidebar-rtl': isRTL }"
				:style="{ order: sidebarOrder }"
				v-if="showSidebar"
				@click.stop
			>
				<Sidebar @close="closeSidebar" />
			</div>
		</div>
		<RuleConfigModal
			v-if="uiStore.show_config_modal"
			v-model="uiStore.show_config_modal"
			:node="graphStore.nodes.find((n) => n.id === uiStore.selected_id)"
			@save="ruleStore.mark_dirty()"
		/>
		<ShortcutsHelp v-model="uiStore.show_shortcuts_help" />
		<Teleport to="body">
			<div
				v-if="showQuickActions"
				ref="quickActionsMenuRef"
				class="quick-actions-menu fxr-headless-menu"
				:style="quickActionsMenuStyle"
				role="menu"
				@keydown="handleQuickActionsKeydown"
			>
				<div class="quick-actions-section">
					<button
						v-for="item in quickActionItems"
						:key="item.key"
						class="quick-action-item"
						role="menuitem"
						:disabled="item.disabled"
						@click="runQuickAction(item)"
					>
						<i :class="['fa', item.icon]"></i>
						<span>{{ item.label }}</span>
						<small v-if="item.shortcut">{{ item.shortcut }}</small>
					</button>
				</div>
			</div>
			<div
				v-if="fieldInspector.visible"
				class="fxr-field-inspector"
				:style="fieldInspectorStyle"
				@mousedown.prevent="copyInspectedFieldname"
			>
				<i class="fa fa-code"></i>
				<span>{{ fieldInspector.fieldname }}</span>
				<small>{{ __("Click to copy") }}</small>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick, provide } from "vue";
import { VueFlow, Panel, PanelPosition, useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";

import { useRuleStore } from "./stores/useRuleStore";
import { useGraphStore } from "./stores/useGraphStore";
import { useUIStore } from "./stores/useUIStore";
import { useMetaStore } from "./stores/useMetaStore";

import { useRuleGraph } from "./composables/useRuleGraph";
import { useClipboard } from "./composables/useClipboard";
import { isTerminalAction } from "../core/contracts";
import { mapActionTypeToNodeType } from "./composables/useActionTypeMapper";

import { generateShortId } from "./utils/schema_utils.js";
import "../utils/utils.js";

import StartNode from "./components/nodes/StartNode.vue";
import ProcessNode from "./components/nodes/ProcessNode.vue";
import ConditionNode from "./components/nodes/ConditionNode.vue";
import LoopNode from "./components/nodes/LoopNode.vue";
import StopNode from "./components/nodes/StopNode.vue";
import ActionSelectorNode from "./components/nodes/ActionSelectorNode.vue";

import Sidebar from "./components/Sidebar.vue";
import RuleConfigModal from "./components/rule_config/RuleConfigModal.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import AddNodeEdge from "./components/AddNodeEdge.vue";

const edgeTypes = {
	add: AddNodeEdge,
};

const props = defineProps({ rule: String });

const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const uiStore = useUIStore();
const metaStore = useMetaStore();

const { zoomIn, zoomOut, removeEdges, fitView } = useVueFlow();
const { layoutGraph } = useRuleGraph();
const { copySelectedToClipboard, pasteFromClipboard } = useClipboard();
const showQuickActions = ref(false);
const quickActionsButtonRef = ref(null);
const quickActionsMenuRef = ref(null);
const quickActionsMenuStyle = ref({});

const flowWrapper = ref(null);
const mousePos = ref({ x: 0, y: 0 });
const showDisabledNodes = ref(true);
const lastAltFieldname = ref("");
const fieldInspector = ref({
	visible: false,
	fieldname: "",
	x: 0,
	y: 0,
	copied: false,
});

const quickActionItems = computed(() => [
	{ key: "save", label: __("Save"), icon: "fa-floppy-o", shortcut: "Ctrl S" },
	{ key: "test", label: __("Test"), icon: "fa-play" },
	{
		key: "status",
		label: isReadOnly.value ? __("Unlock for editing") : __("Set to active"),
		icon: isReadOnly.value ? "fa-unlock" : "fa-rocket",
	},
	{ key: "shortcuts", label: __("Keyboard shortcuts"), icon: "fa-keyboard-o" },
	{ key: "layout", label: __("Auto Layout"), icon: "fa-sitemap" },
	{ key: "permissions", label: __("Set Permission"), icon: "fa-shield" },
	{ key: "copy", label: __("Copy"), icon: "fa-copy", shortcut: "Ctrl C" },
	{
		key: "disabled_nodes",
		label: showDisabledNodes.value ? __("Hide Disabled Nodes") : __("Show Disabled Nodes"),
		icon: showDisabledNodes.value ? "fa-eye-slash" : "fa-eye",
	},
	{ key: "preferences", label: __("Preference"), icon: "fa-sliders" },
]);

const fieldInspectorStyle = computed(() => ({
	left: `${Math.min(fieldInspector.value.x + 14, window.innerWidth - 220)}px`,
	top: `${Math.min(fieldInspector.value.y + 16, window.innerHeight - 48)}px`,
}));

function showShortcutsHelp() {
	uiStore.show_shortcuts_help = true;
}

function updateMousePos(e) {
	mousePos.value = { x: e.clientX, y: e.clientY };
}

watch(
	[showDisabledNodes, () => graphStore.nodes],
	() => {
		const showAll = showDisabledNodes.value;
		graphStore.nodes.forEach((node) => {
			if (node.type === "start") {
				node.hidden = false;
				return;
			}
			const isDisabled = node.data?.is_enabled === 0;
			node.hidden = !showAll && isDisabled;
		});
	},
	{ immediate: true, deep: false }
);

// Watch for layout direction or nodes changes to re-layout the graph
watch(
	[() => ruleStore.settings?.layout_direction, () => graphStore.nodes.length],
	([newDir, nodeCount], [oldDir, oldNodeCount]) => {
		if (newDir && nodeCount > 0) {
			// Only auto-layout if direction changed OR if it's the first time nodes are loaded
			if (newDir !== oldDir || (nodeCount > 0 && oldNodeCount === 0)) {
				const dir = newDir === "Top to Bottom" ? "TB" : "LR";
				// Use nextTick to ensure VueFlow has nodes
				nextTick(() => {
					setTimeout(() => layoutGraph(dir), 50);
				});
			}
		}
	}
);

const showSidebar = computed(() => {
	if (ruleStore.settings?.action_config_mode === "Dialog") return false;
	return uiStore.show_sidebar && uiStore.selected_id !== null;
});
const sidebarOrder = computed(() => (ruleStore.settings?.sidebar_position === "Right" ? 2 : 0));
const isRTL = computed(() => {
	const dir = document.documentElement.getAttribute("dir") || document.body.getAttribute("dir");
	if (dir === "rtl") return true;
	return window.frappe?.utils?.is_rtl() ? true : false;
});
const isReadOnly = computed(() => ruleStore.is_read_only);

function closeSidebar() {
	uiStore.selected_id = null;
	uiStore.show_sidebar = false;
}

function toggleQuickActions() {
	if (showQuickActions.value) {
		closeQuickActions();
		return;
	}
	openQuickActions();
}

function openQuickActions() {
	updateQuickActionsPosition();
	showQuickActions.value = true;
	nextTick(() => {
		quickActionsMenuRef.value?.querySelector(".quick-action-item:not(:disabled)")?.focus();
	});
}

function closeQuickActions() {
	showQuickActions.value = false;
}

function updateQuickActionsPosition() {
	const rect = quickActionsButtonRef.value?.getBoundingClientRect();
	if (!rect) return;
	const width = 236;
	quickActionsMenuStyle.value = {
		position: "fixed",
		top: `${rect.bottom + 8}px`,
		left: `${Math.max(12, Math.min(rect.right - width, window.innerWidth - width - 12))}px`,
		width: `${width}px`,
		zIndex: 12000,
	};
}

function runQuickAction(item) {
	const actions = {
		save: () => ruleStore.save_changes(),
		test: () => window.fxrRuleBuilder?.show_test_dialog?.(),
		status: () => toggleRuleAccess(),
		shortcuts: () => (uiStore.show_shortcuts_help = true),
		layout: () => runAutoLayout(),
		permissions: () => openPermissionsSettings(),
		copy: () => copySelectedToClipboard(),
		disabled_nodes: () => (showDisabledNodes.value = !showDisabledNodes.value),
		preferences: () => openRuleSettingsTab(),
	};
	actions[item.key]?.();
	closeQuickActions();
}

function handleQuickActionsKeydown(e) {
	if (e.key === "Escape") {
		closeQuickActions();
		quickActionsButtonRef.value?.focus();
		return;
	}
	const items = Array.from(
		quickActionsMenuRef.value?.querySelectorAll(".quick-action-item:not(:disabled)") || []
	);
	const current = items.indexOf(document.activeElement);
	if (e.key === "ArrowDown" || e.key === "ArrowUp") {
		e.preventDefault();
		const delta = e.key === "ArrowDown" ? 1 : -1;
		const next = (current + delta + items.length) % items.length;
		items[next]?.focus();
	}
}

function runAutoLayout() {
	const dir = ruleStore.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
	layoutGraph(dir);
	showQuickActions.value = false;
}

function openPermissionsSettings() {
	uiStore.show_sidebar = true;
	uiStore.selected_id = "start";
	showQuickActions.value = false;
}

function openRuleSettingsTab() {
	frappe.set_route("Form", "RuleFlow Settings", "RuleFlow Settings");
	showQuickActions.value = false;
}

function toggleRuleAccess() {
	if (isReadOnly.value) {
		ruleStore.deactivate_rule();
	} else {
		ruleStore.activate_rule();
	}
	showQuickActions.value = false;
}

function onPaneReady(instance) {
	instance.fitView();
}

onMounted(async () => {
	document.body.classList.add("fxr-builder-active");
	if (props.rule) ruleStore.rule_name = props.rule;
	await ruleStore.fetch();
	graphStore.autoConnectStartNode();
	window.addEventListener("keydown", handleKeydown);
	window.addEventListener("keyup", handleKeyup);
	window.addEventListener("mousemove", updateMousePos);
	window.addEventListener("mousemove", handleAltFieldInspect, true);
	window.addEventListener("mousedown", handleGlobalMouseDown, true);
	window.addEventListener("resize", updateQuickActionsPosition);
	window.addEventListener("flexirule:show-shortcuts-help", showShortcutsHelp);

	setTimeout(() => {
		if (graphStore.nodes.length > 0) {
			const dir = ruleStore.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
			layoutGraph(dir);
		}
	}, 100);
});

onUnmounted(() => {
	document.body.classList.remove("fxr-builder-active");
	window.removeEventListener("keydown", handleKeydown);
	window.removeEventListener("keyup", handleKeyup);
	window.removeEventListener("mousemove", updateMousePos);
	window.removeEventListener("mousemove", handleAltFieldInspect, true);
	window.removeEventListener("mousedown", handleGlobalMouseDown, true);
	window.removeEventListener("resize", updateQuickActionsPosition);
	window.removeEventListener("flexirule:show-shortcuts-help", showShortcutsHelp);
});

async function pasteFromClipboardWrapper() {
	await pasteFromClipboard(mousePos.value, flowWrapper.value);
}

function onDragOver(event) {
	event.preventDefault();
	if (event.dataTransfer) {
		event.dataTransfer.dropEffect = "move";
	}
}

function onDrop(event) {
	event.preventDefault();
	// Handle drop if any drag-and-drop node creation is implemented
}

function handleKeydown(e) {
	// If the config modal is open, let it handle keypress events
	if (uiStore.show_config_modal) return;

	// Don't trigger if typing in an input
	if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) || e.target.isContentEditable)
		return;

	// Save: Ctrl+S
	if ((e.ctrlKey || e.metaKey) && e.key === "s") {
		e.preventDefault();
		ruleStore.save_changes();
	}
	// Undo: Ctrl+Z
	if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
		e.preventDefault();
		if (ruleStore.can_undo()) ruleStore.undo();
	}
	// Redo: Ctrl+Y or Ctrl+Shift+Z
	if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
		e.preventDefault();
		if (ruleStore.can_redo()) ruleStore.redo();
	}
	// Copy: Ctrl+C
	if ((e.ctrlKey || e.metaKey) && e.key === "c") {
		if (window.getSelection().toString().length > 0) return;
		copySelectedToClipboard();
	}
	// Paste: Ctrl+V
	if ((e.ctrlKey || e.metaKey) && e.key === "v") {
		pasteFromClipboardWrapper();
	}

	// Shortcuts Help: Shift+?
	if (e.shiftKey && e.key === "?") {
		uiStore.show_shortcuts_help = !uiStore.show_shortcuts_help;
	}

	// Alt+1: Focus Sidebar
	if (e.altKey && e.key === "1") {
		if (uiStore.selected_id) {
			uiStore.show_sidebar = true;
			e.preventDefault();
		}
	}

	// Alt+2: Variable Search (Global Sidebar)
	if (e.altKey && e.key === "2") {
		// Not implemented in sidebar yet, but could be added if Sidebar had a search
	}
}

function handleKeyup(e) {
	if (!e.altKey) {
		lastAltFieldname.value = "";
		fieldInspector.value.visible = false;
	}
}

function handleAltFieldInspect(event) {
	if (!event.altKey) {
		fieldInspector.value.visible = false;
		lastAltFieldname.value = "";
		return;
	}
	const fieldEl = event.target?.closest?.("[data-fxr-fieldname]");
	const fieldname = fieldEl?.dataset?.fxrFieldname;
	if (!fieldname) {
		fieldInspector.value.visible = false;
		return;
	}
	fieldInspector.value = {
		visible: true,
		fieldname,
		x: event.clientX,
		y: event.clientY,
		copied: fieldInspector.value.copied,
	};
	if (fieldname === lastAltFieldname.value) return;
	lastAltFieldname.value = fieldname;
}

function copyInspectedFieldname() {
	const fieldname = fieldInspector.value.fieldname;
	if (!fieldname) return;
	navigator.clipboard?.writeText(fieldname).catch(() => {});
	frappe.show_alert(
		{ message: __("Copied fieldname: {0}").replace("{0}", fieldname), indicator: "green" },
		2
	);
}

function handleGlobalMouseDown(event) {
	if (
		showQuickActions.value &&
		!quickActionsMenuRef.value?.contains(event.target) &&
		!quickActionsButtonRef.value?.contains(event.target)
	) {
		closeQuickActions();
	}
	if (event.altKey && event.target?.closest?.("[data-fxr-fieldname]")) {
		copyInspectedFieldname();
	}
}

function insertNodeOnEdge(payload) {
	if (payload.isPaste) {
		let clipboard = null;
		try {
			const local = localStorage.getItem("flexirule-clipboard") || uiStore.local_clipboard;
			if (local) clipboard = JSON.parse(local);
		} catch (e) {
			console.error("Paste on edge failed:", e);
		}

		if (clipboard && clipboard.nodes?.length) {
			const newNodeId = graphStore.paste_on_edge(
				payload.edgeId,
				clipboard.nodes,
				clipboard.edges
			);
			if (newNodeId) {
				const dir = ruleStore.settings?.layout_direction === "Left to Right" ? "LR" : "TB";
				setTimeout(() => layoutGraph(dir), 50);
				frappe.show_alert({ message: __("Nodes pasted on edge"), indicator: "green" }, 2);
			}
		}
		return;
	}

	const newNodeId = graphStore.insert_node_on_edge(
		payload.edgeId,
		payload.actionType || "selector",
		payload
	);
	if (newNodeId) {
		const dir = ruleStore.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
		setTimeout(() => {
			layoutGraph(dir);
			// Auto-open config for nodes that require immediate configuration
			const NEEDS_CONFIG_NOW = ["Condition", "Loop", "Switch"];
			const insertedNode = graphStore.nodes.find((n) => n.id === newNodeId);
			if (insertedNode && NEEDS_CONFIG_NOW.includes(insertedNode.data?.action_type)) {
				ruleStore.open_config(newNodeId);
			}
		}, 80);
	}
}

function onNodeClick(event) {
	uiStore.selected_id = event.node.id;
	if (event.node.type === "selector") {
		// Selector nodes must stay interactive for action type search/create.
		return;
	}

	// Bypass config opening if we are likely performing multi-selection
	if (event.event.shiftKey || event.event.ctrlKey || event.event.metaKey) {
		return;
	}

	const trigger = ruleStore.settings?.open_config_on || "Click";
	if (trigger === "Click" && event.node.type !== "start") {
		ruleStore.open_config(event.node.id);
	}
}

function onNodeDblClick(event) {
	uiStore.selected_id = event.node.id;
	if (event.node.type === "selector") {
		return;
	}

	const trigger = ruleStore.settings?.open_config_on || "Click";
	if (trigger === "Double Click" && event.node.type !== "start") {
		ruleStore.open_config(event.node.id);
	}
}

function onPaneClick() {
	uiStore.selected_id = null;
	uiStore.show_sidebar = false;
}

function onConnect(params) {
	const sourceHandle = params.sourceHandle || "default";
	const id = `e-${params.source}-${params.target}-${sourceHandle}`;

	// Enforce single connection per source handle
	const existingEdgeIndex = (graphStore.edges || []).findIndex(
		(e) => e.source === params.source && (e.sourceHandle || "default") === sourceHandle
	);

	if (existingEdgeIndex !== -1) {
		const existingEdge = graphStore.edges[existingEdgeIndex];
		// If connecting to the same target, ignore
		if (existingEdge.target === params.target) return;

		// Otherwise, remove the old one to replace it
		graphStore.edges.splice(existingEdgeIndex, 1);
	}

	const newEdge = {
		id,
		source: params.source,
		target: params.target,
		sourceHandle,
		targetHandle: params.targetHandle,
		type: "add",
		animated: graphStore.nodes.find((el) => el.id === params.source)?.type === "start",
		data: {
			isReturn: params.targetHandle === "return",
		},
	};
	graphStore.edges = [...graphStore.edges, newEdge];
	ruleStore.mark_dirty();
}

function onNodesChange(changes) {
	const hasDrag = changes.some((c) => c.type === "position" && c.dragging === false);
	if (hasDrag) ruleStore.mark_position_change();
}

function onEdgesChange(changes) {
	changes.forEach((change) => {
		if (change.type === "remove") {
			graphStore.delete_edge(change.id, ruleStore.is_read_only);
			ruleStore.mark_dirty();
		}
	});
}

function onEdgeClick({ edge, event }) {
	event?.stopPropagation();

	frappe.confirm(__("Delete this connection?"), () => {
		removeEdges([edge.id]);
	});
}
</script>

<style>
@import "@vue-flow/core/dist/style.css";
@import "@vue-flow/core/dist/theme-default.css";

.rule-builder-container,
.fxr-builder-active {
	--fxr-bg-page: var(--fg-color, #ffffff);
	--fxr-bg-card: var(--fg-color, #ffffff);
	--fxr-bg-input: var(--fg-color, #ffffff);
	--fxr-surface: var(--fg-color, #ffffff);
	--fxr-surface-2: var(--control-bg, #f3f5f7);
	--fxr-surface-soft: color-mix(in srgb, var(--control-bg, #f3f5f7) 68%, white);
	--fxr-surface-elevated: color-mix(in srgb, var(--fg-color, #ffffff) 94%, transparent);
	--fxr-border: var(--border-color, #d1d8dd);
	--fxr-border-subtle: color-mix(in srgb, var(--border-color, #d1d8dd) 72%, white);
	--fxr-border-strong: color-mix(in srgb, var(--border-color, #d1d8dd) 88%, #334155);
	--fxr-text: var(--text-color, #1f2937);
	--fxr-text-strong: var(--text-color, #1f2937);
	--fxr-text-soft: var(--text-muted, #64748b);
	--fxr-text-muted: var(--text-muted, #64748b);
	--fxr-text-faint: color-mix(in srgb, var(--text-muted, #64748b) 70%, white);
	--fxr-accent: var(--primary, #2490ef);
	--fxr-accent-soft: color-mix(in srgb, var(--primary, #2490ef) 12%, white);
	--fxr-accent-strong: color-mix(in srgb, var(--primary, #2490ef) 84%, black);
	--fxr-success-soft: color-mix(in srgb, var(--green-500, #22c55e) 14%, white);
	--fxr-warning-soft: color-mix(in srgb, var(--orange-500, #f59e0b) 14%, white);
	--fxr-danger-soft: color-mix(in srgb, var(--red-500, #ef4444) 14%, white);
	--fxr-space-1: 4px;
	--fxr-space-2: 6px;
	--fxr-space-3: 8px;
	--fxr-space-4: 12px;
	--fxr-space-5: 16px;
	--fxr-space-6: 20px;
	--fxr-space-8: 24px;
	--fxr-space-10: 32px;
	--fxr-radius-sm: 8px;
	--fxr-radius-md: 12px;
	--fxr-radius-lg: 16px;
	--fxr-radius-xl: 20px;
	--fxr-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
	--fxr-shadow-md: 0 10px 24px rgba(15, 23, 42, 0.08);
	--fxr-shadow-lg: 0 22px 48px rgba(15, 23, 42, 0.12);
}

.rule-builder-container {
	display: flex;
	flex-direction: column;
	height: calc(100vh - var(--navbar-height) - var(--page-head-height) - 60px);
}
/* Removed .builder-toolbar */

.builder-main {
	flex: 1;
	display: flex;
	position: relative;
	overflow: hidden;
	gap: var(--fxr-space-3);
}
/* ... */
.controls-panel {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
	background: var(--fxr-surface-elevated);
	padding: var(--fxr-space-2);
	border-radius: var(--fxr-radius-md);
	border: 1px solid var(--fxr-border-subtle);
	box-shadow: var(--fxr-shadow-md);
	backdrop-filter: blur(12px);
	flex-wrap: wrap;
	max-width: calc(100vw - 28px);
}

.controls-panel .btn {
	border-radius: 7px;
}

.quick-actions-wrap {
	position: relative;
	display: inline-flex;
	gap: var(--fxr-space-2);
	align-items: center;
}

.quick-actions-btn {
	width: 32px;
	height: 32px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 0;
}

.fxr-headless-menu {
	background: var(--fxr-surface, #ffffff);
	border: 1px solid var(--fxr-border-subtle, #d1d8dd);
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-lg);
	overflow: hidden;
	animation: fxr-menu-in 120ms ease-out;
}

.quick-actions-section {
	padding: 4px;
	display: flex;
	flex-direction: column;
	gap: 1px;
	max-height: min(320px, calc(100vh - 180px));
	overflow-y: auto;
}

.quick-action-item {
	display: grid;
	grid-template-columns: 18px 1fr auto;
	align-items: center;
	gap: 8px;
	width: 100%;
	min-height: 30px;
	padding: 7px 10px;
	border: 0;
	border-radius: 8px;
	background: transparent;
	color: var(--fxr-text-strong);
	font-size: 12px;
	font-weight: 500;
	text-align: left;
	cursor: pointer;
}

.quick-action-item i {
	color: var(--fxr-text-soft);
	text-align: center;
}

.quick-action-item small {
	color: var(--fxr-text-faint);
	font-size: 9px;
	font-weight: 600;
}

.quick-action-item:hover,
.quick-action-item:focus {
	background: var(--fxr-surface-2);
	outline: none;
}

.quick-action-item:disabled {
	opacity: 0.55;
	cursor: not-allowed;
}

.fxr-field-inspector {
	position: fixed;
	z-index: 13000;
	display: inline-grid;
	grid-template-columns: 14px auto auto;
	align-items: center;
	gap: 7px;
	max-width: 280px;
	padding: 7px 9px;
	border-radius: 8px;
	border: 1px solid var(--fxr-border-subtle, #d1d8dd);
	background: var(--fxr-surface, #ffffff);
	color: var(--fxr-text-strong, #1f2937);
	font-size: 12px;
	font-weight: 600;
	box-shadow: var(--fxr-shadow-md);
	pointer-events: auto;
	cursor: copy;
}

.fxr-field-inspector i {
	color: var(--fxr-accent);
}

.fxr-field-inspector span {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fxr-field-inspector small {
	color: var(--fxr-text-soft);
	font-size: 10px;
	font-weight: 500;
	white-space: nowrap;
}

@keyframes fxr-menu-in {
	from {
		opacity: 0;
		transform: translateY(-4px) scale(0.98);
	}
	to {
		opacity: 1;
		transform: translateY(0) scale(1);
	}
}
.divider-vertical {
	width: 1px;
	height: 20px;
	background-color: var(--fxr-border-subtle);
}
.sidebar-container {
	position: relative;
	width: 360px;
	min-width: 320px;
	max-width: 440px;
	height: 100%;
	border-radius: var(--fxr-radius-lg);
	border: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface);
	order: 2;
	overflow: hidden;
	z-index: 5;
}
.canvas-container {
	flex: 1;
	min-width: 0;
	height: 100%;
	border-radius: var(--fxr-radius-lg);
	border: 1px solid var(--fxr-border-subtle);
	background-color: color-mix(in srgb, var(--fxr-bg-page) 88%, white);
	position: relative;
	order: 1;
}

.canvas-container :deep(.vue-flow__pane) {
	cursor: grab;
}

.canvas-container :deep(.vue-flow__pane:active) {
	cursor: grabbing;
}

.execution-panel {
	min-width: 260px;
	max-width: 360px;
	background: var(--fxr-surface);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	padding: 10px;
	box-shadow: var(--fxr-shadow-sm);
}

.execution-panel-header {
	display: flex;
	justify-content: space-between;
	margin-bottom: 8px;
}

.execution-final-status {
	font-size: 12px;
	font-weight: 600;
	color: var(--fxr-text-strong);
}

.execution-panel-steps {
	display: flex;
	flex-direction: column;
	gap: 6px;
	max-height: 240px;
	overflow: auto;
}

.execution-step {
	display: flex;
	gap: 8px;
	font-size: 12px;
	padding: 4px 6px;
	border-radius: 4px;
}

.execution-step.status-success {
	background: var(--fxr-success-soft);
	color: var(--green-700, #166534);
}

.execution-step.status-error {
	background: var(--fxr-danger-soft);
	color: var(--red-700, #b91c1c);
}

.execution-step.status-running {
	background: var(--fxr-accent-soft);
	color: var(--fxr-accent-strong);
}

.step-label {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

:deep(.test-error) {
	box-shadow: 0 0 0 3px var(--red-500, #dc2626) !important;
}

:deep(.test-error .execution-badge) {
	background: var(--red-500, #dc2626) !important;
}

:deep(.test-running .execution-badge) {
	background: var(--blue-600, #2563eb) !important;
}
.toolbar-center {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 1;
}

@media (max-width: 1200px) {
	.sidebar-container {
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		width: min(420px, 55vw);
		min-width: 320px;
		border-radius: 0;
	}
	.sidebar-rtl {
		left: 0;
		right: auto;
	}
}

@media (max-width: 768px) {
	.rule-builder-container {
		height: calc(100vh - var(--navbar-height) - 16px);
	}
	.sidebar-container {
		left: 0;
		right: 0;
		top: auto;
		bottom: 0;
		width: 100%;
		min-width: 0;
		max-width: none;
		height: 58%;
		border-radius: 12px 12px 0 0;
	}
}

.sub-rule-group-node {
	background: color-mix(in srgb, var(--fxr-surface-2, #f6f8fa) 40%, transparent) !important;
	border: 2px dashed var(--fxr-text-faint, #94a3b8) !important;
	border-radius: 16px !important;
	min-width: 450px !important;
	min-height: 320px !important;
}

.sub-rule-group-node :deep(.vue-flow__node-default) {
	border-style: solid !important;
}

/* Read Only Flow Visuals */
.is-read-only-flow :deep(.vue-flow__node) {
	filter: grayscale(0.6) opacity(0.8);
	transition: all 0.3s ease;
}

.is-read-only-flow :deep(.vue-flow__node.selected),
.is-read-only-flow :deep(.vue-flow__node:hover) {
	filter: grayscale(0) opacity(1);
}

.is-read-only-flow :deep(.vue-flow__edge-path) {
	stroke: var(--fxr-border-subtle, #cbd5e1) !important;
	stroke-opacity: 0.6;
}

.is-read-only-flow :deep(.vue-flow__node.test-executed) {
	filter: none !important;
	opacity: 1 !important;
}

.read-only-badge {
	background: var(--fxr-warning-soft, #fff7ed);
	color: var(--orange-800, #9a3412);
	padding: 4px 10px;
	border-radius: 6px;
	border: 1px solid color-mix(in srgb, var(--orange-300, #ffedd5) 70%, white);
	font-size: 11px;
	font-weight: 700;
}

/* RTL Support */
.is-rtl,
[dir="rtl"] .rule-builder-container {
	direction: rtl !important;
}

.is-rtl :deep(.process-node-card),
.is-rtl :deep(.start-node-card),
.is-rtl :deep(.condition-node-card),
.is-rtl :deep(.loop-node-card),
.is-rtl :deep(.stop-node-card),
.is-rtl :deep(.action-selector-card),
[dir="rtl"] .process-node-card,
[dir="rtl"] .start-node-card,
[dir="rtl"] .condition-node-card,
[dir="rtl"] .loop-node-card,
[dir="rtl"] .stop-node-card,
[dir="rtl"] .action-selector-card {
	direction: rtl !important;
}

.is-rtl :deep(.node-header),
[dir="rtl"] .node-header {
	flex-direction: row !important;
}

.is-rtl :deep(.detail-row),
[dir="rtl"] .detail-row {
	flex-direction: row !important;
}

.is-rtl :deep(.detail-row i),
[dir="rtl"] .detail-row i {
	margin-left: 6px !important;
	margin-right: 0 !important;
}

.is-rtl :deep(.action-btn),
[dir="rtl"] .action-btn {
	margin-right: auto !important;
	margin-left: 0 !important;
}

/* Process Node RTL */
.is-rtl :deep(.process-node-card:not(.is-vertical)),
[dir="rtl"] .process-node-card:not(.is-vertical) {
	border-left: 1px solid #d1d8dd !important;
	border-right: 4px solid var(--accent-color) !important;
}

.is-rtl :deep(.node-header .type-text),
[dir="rtl"] .node-header .type-text {
	text-align: right !important;
}

/* Start Node RTL */
.is-rtl :deep(.start-node-d:not(.is-vertical) .node-body),
[dir="rtl"] .start-node-d:not(.is-vertical) .node-body {
	border-radius: 40px 4px 4px 40px !important;
	padding: 8px 10px 8px 16px !important;
}

.is-rtl :deep(.start-node-d .icon-section),
[dir="rtl"] .start-node-d .icon-section {
	margin-left: 10px !important;
	margin-right: 0 !important;
}

/* Condition Node RTL */
.is-rtl :deep(.condition-node-card .out-right),
[dir="rtl"] .condition-node-card .out-right {
	right: auto !important;
	left: -30px !important;
}

.is-rtl :deep(.condition-node-card .out-right .port-label),
[dir="rtl"] .condition-node-card .out-right .port-label {
	left: auto !important;
	right: 50% !important;
	transform: translateX(50%) !important;
}

/* Execution Badge RTL */
.is-rtl :deep(.execution-badge),
[dir="rtl"] .execution-badge {
	left: auto !important;
	right: -8px !important;
}

.is-rtl :deep(.node-header .type-text),
[dir="rtl"] .node-header .type-text {
	text-align: right !important;
	margin-right: 8px !important;
	margin-left: 0 !important;
}

/* Sidebar RTL Adjustment */
.is-rtl .sidebar-rtl {
	border-left: none;
	border-right: 1px solid var(--border-color);
}

/* Action Selector RTL */
.is-rtl .search-icon {
	left: auto;
	right: 8px;
}

.is-rtl .search-input-group input {
	padding-left: 10px !important;
	padding-right: 24px !important;
}

.is-rtl .result-option i {
	margin-left: 10px;
	margin-right: 0;
}
</style>
