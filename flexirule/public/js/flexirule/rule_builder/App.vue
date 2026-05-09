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
					:zoom-on-pinch="true"
					:snap-to-grid="true"
					:snap-grid="[15, 15]"
					:nodes-draggable="!isReadOnly"
					:nodes-connectable="!isReadOnly"
					:elements-selectable="true"
					:selection-on-drag="true"
					:pan-on-drag="[2]"
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

					<template #edge-add="edgeProps">
						<AddNodeEdge v-bind="edgeProps" @insert-node="insertNodeOnEdge" />
					</template>

					<Background :gap="15" />
					<Panel :position="PanelPosition.BottomLeft" class="controls-panel">
						<div class="btn-group">
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
							<button
								class="btn btn-sm btn-default"
								@click="
									() =>
										layoutGraph(
											ruleStore.settings?.layout_direction === 'Top to Bottom'
												? 'TB'
												: 'LR'
										)
								"
								:title="__('Auto Layout')"
							>
								<i class="fa fa-sitemap"></i> {{ __("Auto Layout") }}
							</button>
						</div>

						<div class="divider-vertical"></div>

						<div class="show-disabled-control" :title="__('Show Disabled Nodes')">
							<label class="switch small-switch">
								<input type="checkbox" v-model="showDisabledNodes" />
								<span class="slider round"></span>
							</label>
							<span class="small text-muted">{{ __("Disabled") }}</span>
						</div>

						<button
							class="btn btn-sm btn-default"
							@click="copySelectedToClipboard"
							:title="__('Copy Selected Nodes (Ctrl+C)')"
						>
							<i class="fa fa-copy"></i> {{ __("Copy") }}
						</button>

						<div class="divider-vertical"></div>

						<div v-if="isReadOnly" class="read-only-badge mr-2">
							<i class="fa fa-lock"></i> {{ __("Read Only") }}
						</div>

						<button
							v-if="!isReadOnly"
							class="btn btn-sm btn-primary btn-activate"
							@click="ruleStore.activate_rule"
							:disabled="ruleStore.is_loading"
						>
							<i
								:class="[
									'fa',
									ruleStore.is_loading ? 'fa-spinner fa-spin' : 'fa-rocket',
								]"
							></i>
							{{ __("Set to Active") }}
						</button>
						<button
							v-else
							class="btn btn-sm btn-outline-warning btn-unlock"
							@click="ruleStore.deactivate_rule"
							:disabled="ruleStore.is_loading"
						>
							<i
								:class="[
									'fa',
									ruleStore.is_loading ? 'fa-spinner fa-spin' : 'fa-unlock',
								]"
							></i>
							{{ __("Unlock for Editing") }}
						</button>
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

const flowWrapper = ref(null);
const mousePos = ref({ x: 0, y: 0 });
const showDisabledNodes = ref(true);

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

function onPaneReady(instance) {
	instance.fitView();
}

onMounted(async () => {
	if (props.rule) ruleStore.rule_name = props.rule;
	await ruleStore.fetch();
	graphStore.autoConnectStartNode();
	window.addEventListener("keydown", handleKeydown);
	window.addEventListener("mousemove", updateMousePos);

	setTimeout(() => {
		if (graphStore.nodes.length > 0) {
			const dir = ruleStore.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
			layoutGraph(dir);
		}
	}, 100);
});

onUnmounted(() => {
	window.removeEventListener("keydown", handleKeydown);
	window.removeEventListener("mousemove", updateMousePos);
});

async function pasteFromClipboardWrapper() {
	await pasteFromClipboard(mousePos.value, flowWrapper.value);
}

function handleKeydown(e) {
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
	gap: 10px;
}
/* ... */
.controls-panel {
	display: flex;
	align-items: center;
	gap: 10px;
	background: rgba(255, 255, 255, 0.8);
	padding: 5px 10px;
	border-radius: 4px;
	border: 1px solid var(--border-color);
	backdrop-filter: blur(2px);
}
.divider-vertical {
	width: 1px;
	height: 20px;
	background-color: var(--border-color);
}
.show-disabled-control {
	display: flex;
	align-items: center;
	gap: 5px;
}
.sidebar-container {
	position: relative;
	width: 360px;
	min-width: 320px;
	max-width: 440px;
	height: 100%;
	border-radius: var(--border-radius-lg);
	border: 1px solid var(--border-color);
	background-color: var(--fg-color);
	order: 2;
	overflow: hidden;
	z-index: 5;
}
.canvas-container {
	flex: 1;
	min-width: 0;
	height: 100%;
	border-radius: var(--border-radius-lg);
	border: 1px solid var(--border-color);
	background-color: var(--fg-color);
	position: relative;
	order: 1;
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
	background: rgba(246, 248, 250, 0.4) !important;
	border: 2px dashed #94a3b8 !important;
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
	stroke: #cbd5e1 !important;
	stroke-opacity: 0.6;
}

.is-read-only-flow :deep(.vue-flow__node.test-executed) {
	filter: none !important;
	opacity: 1 !important;
}

.read-only-badge {
	background: #fff7ed;
	color: #9a3412;
	padding: 4px 10px;
	border-radius: 6px;
	border: 1px solid #ffedd5;
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
