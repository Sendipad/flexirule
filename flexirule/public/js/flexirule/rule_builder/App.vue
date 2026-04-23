<template>
	<div class="rule-builder-container" :class="{ 'is-read-only': isReadOnly, 'is-rtl': isRTL }">
		<!-- Main Canvas + Sidebar -->
		<div class="builder-main">
			<div class="canvas-container" ref="flowWrapper" @dragover="onDragOver" @drop="onDrop">
				<VueFlow
					:dir="isRTL ? 'rtl' : 'ltr'"
					:edges-editable="false"
					v-model:nodes="store.nodes"
					v-model:edges="store.edges"
					:default-viewport="{ zoom: 1 }"
					:min-zoom="0.2"
					:max-zoom="2"
					:snap-to-grid="true"
					:snap-grid="[15, 15]"
					:nodes-draggable="!isReadOnly"
					:nodes-connectable="!isReadOnly"
					:elements-selectable="true"
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
											store.settings?.layout_direction === 'Top to Bottom'
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
							@click="store.activate_rule"
							:disabled="store.is_loading"
						>
							<i
								:class="[
									'fa',
									store.is_loading ? 'fa-spinner fa-spin' : 'fa-rocket',
								]"
							></i>
							{{ __("Set to Active") }}
						</button>
						<button
							v-else
							class="btn btn-sm btn-outline-warning btn-unlock"
							@click="store.deactivate_rule"
							:disabled="store.is_loading"
						>
							<i
								:class="[
									'fa',
									store.is_loading ? 'fa-spinner fa-spin' : 'fa-unlock',
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
			v-if="store.show_config_modal"
			v-model="store.show_config_modal"
			:node="store.nodes.find((n) => n.id === store.selected_id)"
			@save="store.mark_dirty()"
		/>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { VueFlow, Panel, PanelPosition } from "@vue-flow/core";
import { useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { useStore } from "./store";
import { useRuleGraph } from "./composables/useRuleGraph";
import { isTerminalAction } from "../core/contracts";
import { mapActionTypeToNodeType } from "./composables/useActionTypeMapper";

import { generateShortId } from "../utils/index.js";
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
const store = useStore();
const { zoomIn, zoomOut, removeEdges, getSelectedNodes, getSelectedEdges, project } = useVueFlow();
const { layoutGraph } = useRuleGraph();
let vfInstance = null;

const showDisabledNodes = ref(true);

// Watch for changes in showDisabledNodes or store.nodes to update 'hidden' flag
watch(
	[showDisabledNodes, () => store.nodes],
	() => {
		const showAll = showDisabledNodes.value;
		store.nodes.forEach((node) => {
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
	[() => store.settings?.layout_direction, () => store.nodes.length],
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
	if (store.settings?.action_config_mode === "Dialog") return false;
	return store.show_sidebar && store.selected_id !== null;
});
const sidebarOrder = computed(() => (store.settings?.sidebar_position === "Right" ? 2 : 0));
const isRTL = computed(() => {
	const dir = document.documentElement.getAttribute("dir") || document.body.getAttribute("dir");
	if (dir === "rtl") return true;
	return window.frappe?.utils?.is_rtl() ? true : false;
});
const isReadOnly = computed(() => store.is_read_only);

function closeSidebar() {
	store.selected_id = null;
	store.show_sidebar = false;
}

function onPaneReady(instance) {
	vfInstance = instance;
	instance.fitView();
}

onMounted(async () => {
	if (props.rule) store.rule_name = props.rule;
	await store.fetch();
	autoConnectStartNode();
	window.addEventListener("keydown", handleKeydown);

	setTimeout(() => {
		if (store.nodes.length > 0) {
			const dir = store.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
			layoutGraph(dir);
		}
	}, 100);
});

onUnmounted(() => {
	window.removeEventListener("keydown", handleKeydown);
});

async function copySelectedToClipboard() {
	const selectedNodes = getSelectedNodes.value;
	if (!selectedNodes.length) return;

	// Don't allow copying start node
	const filterNodes = selectedNodes.filter((n) => n.id !== "start" && n.type !== "start");
	if (!filterNodes.length) {
		frappe.show_alert({ message: __("Start node cannot be copied"), indicator: "orange" }, 2);
		return;
	}

	const selectedEdges = getSelectedEdges.value;

	// Map to clean objects to avoid circular references and VueFlow internal state
	const payload = {
		type: "flexirule-clipboard",
		version: 1,
		nodes: filterNodes.map((n) => {
			const nodeData = JSON.parse(JSON.stringify(n.data || {}));
			// Sync condition_json for Condition nodes if missing
			if (
				nodeData.action_type === "Condition" &&
				!nodeData.condition_json &&
				nodeData.config
			) {
				nodeData.condition_json = JSON.stringify(nodeData.config);
			}
			return {
				id: n.id,
				type: n.type,
				position: { ...n.position },
				label: n.label,
				data: nodeData,
			};
		}),
		edges: selectedEdges.map((e) => ({
			id: e.id,
			source: e.source,
			target: e.target,
			sourceHandle: e.sourceHandle,
		})),
	};

	const payloadStr = JSON.stringify(payload);
	store.local_clipboard = payloadStr;
	localStorage.setItem("flexirule-clipboard", payloadStr); // Cross-tab fallback

	try {
		// Try modern clipboard API first
		if (navigator?.clipboard && window.isSecureContext) {
			await navigator.clipboard.writeText(payloadStr);
			frappe.show_alert({ message: __("Nodes copied to clipboard"), indicator: "blue" }, 2);
		} else {
			throw new Error("Clipboard API unavailable");
		}
	} catch (e) {
		// Fallback for insecure contexts or API failure
		const textArea = document.createElement("textarea");
		textArea.value = payloadStr;
		textArea.style.position = "fixed";
		textArea.style.left = "-9999px";
		textArea.style.top = "0";
		document.body.appendChild(textArea);
		textArea.focus();
		textArea.select();

		try {
			const successful = document.execCommand("copy");
			if (successful) {
				frappe.show_alert(
					{
						message: __("Nodes copied to clipboard (system fallback)"),
						indicator: "blue",
					},
					2
				);
			} else {
				throw new Error("execCommand copy failed");
			}
		} catch (err) {
			console.warn("FlexiRule: All clipboard copy methods failed", err);
			frappe.show_alert(
				{
					message: __("Nodes copied to local session only (cross-browser copy failed)"),
					indicator: "orange",
				},
				3
			);
		}
		document.body.removeChild(textArea);
	}
}

async function pasteFromClipboard() {
	if (isReadOnly.value) return;

	let payload = null;

	// 1. Try system clipboard
	try {
		if (navigator?.clipboard && window.isSecureContext) {
			const text = await navigator.clipboard.readText();
			const parsed = JSON.parse(text);
			if (parsed.type === "flexirule-clipboard") {
				payload = parsed;
			}
		}
	} catch (e) {
		console.warn("FlexiRule: System clipboard read failed, trying local fallback", e);
	}

	// 2. Fallback to local clipboard (Pinia or localStorage for cross-tab)
	if (!payload) {
		try {
			const local = localStorage.getItem("flexirule-clipboard") || store.local_clipboard;
			if (local) {
				const parsed = JSON.parse(local);
				if (parsed.type === "flexirule-clipboard") {
					payload = parsed;
				}
			}
		} catch (e) {
			console.error("FlexiRule: Local clipboard fallback failed", e);
		}
	}

	if (!payload) {
		frappe.show_alert({ message: __("Clipboard is empty or invalid"), indicator: "orange" }, 3);
		return;
	}

	// Calculate paste position: mouse position in flow coordinates
	// Fallback to center if mouse is outside canvas
	const bounds = flowWrapper.value.getBoundingClientRect();
	const flowX = mousePos.value.x - bounds.left;
	const flowY = mousePos.value.y - bounds.top;

	const position = project({ x: flowX, y: flowY });

	const newNodes = store.pasteNodes(payload.nodes, payload.edges, position);

	if (newNodes.length) {
		// Select the first pasted node
		store.selected_id = newNodes[0].id;
		frappe.show_alert({ message: __("Nodes pasted"), indicator: "green" }, 2);
	}
}

function handleKeydown(e) {
	// Don't trigger if typing in an input
	if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;

	// Save: Ctrl+S
	if ((e.ctrlKey || e.metaKey) && e.key === "s") {
		e.preventDefault();
		store.save_changes();
	}
	// Undo: Ctrl+Z
	if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
		e.preventDefault();
		if (store.can_undo()) store.undo();
	}
	// Redo: Ctrl+Y or Ctrl+Shift+Z
	if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
		e.preventDefault();
		if (store.can_redo()) store.redo();
	}
	// Copy: Ctrl+C
	if ((e.ctrlKey || e.metaKey) && e.key === "c") {
		if (window.getSelection().toString().length > 0) return;
		copySelectedToClipboard();
	}
	// Paste: Ctrl+V
	if ((e.ctrlKey || e.metaKey) && e.key === "v") {
		pasteFromClipboard();
	}
}

function hasOutgoingEdge(nodeId) {
	return (store.edges || []).some((edge) => edge.source === nodeId);
}

function getAutoConnectSource() {
	const selectedNode = (store.nodes || []).find((node) => node.id === store.selected_id);
	const selectedActionType = selectedNode?.data?.action_type || selectedNode?.type;
	if (
		selectedNode &&
		selectedNode.type !== "selector" &&
		selectedNode.type !== "condition" &&
		!isTerminalAction(selectedActionType) &&
		!hasOutgoingEdge(selectedNode.id)
	) {
		return selectedNode;
	}

	const startNode = (store.nodes || []).find(
		(node) => node.id === "start" || node.type === "start"
	);
	if (startNode && !hasOutgoingEdge(startNode.id)) {
		return startNode;
	}

	return null;
}

function autoConnectNode(nodeId, parentNode = null) {
	const sourceNode = parentNode || getAutoConnectSource();
	if (!sourceNode) return;

	const sourceHandle = sourceNode.type === "condition" ? null : "default";
	const edgeId = `e-${sourceNode.id}-${nodeId}-${sourceHandle || "default"}`;
	const exists = (store.edges || []).some(
		(edge) =>
			edge.source === sourceNode.id &&
			edge.target === nodeId &&
			(edge.sourceHandle || "default") === (sourceHandle || "default")
	);
	if (exists) return;

	store.edges = [
		...store.edges,
		{
			id: edgeId,
			source: sourceNode.id,
			target: nodeId,
			sourceHandle: sourceHandle || "default",
			type: "add",
			animated: sourceNode.type === "start",
		},
	];
}

function insertNodeOnEdge(payload) {
	if (payload.isPaste) {
		let clipboard = null;
		try {
			const local = localStorage.getItem("flexirule-clipboard") || store.local_clipboard;
			if (local) clipboard = JSON.parse(local);
		} catch (e) {
			console.error("Paste on edge failed:", e);
		}

		if (clipboard && clipboard.nodes?.length) {
			const newNodeId = store.paste_on_edge(payload.edgeId, clipboard.nodes, clipboard.edges);
			if (newNodeId) {
				const dir = store.settings?.layout_direction === "Left to Right" ? "LR" : "TB";
				setTimeout(() => layoutGraph(dir), 50);
				frappe.show_alert({ message: __("Nodes pasted on edge"), indicator: "green" }, 2);
			}
		}
		return;
	}

	const newNodeId = store.insert_node_on_edge(
		payload.edgeId,
		payload.actionType || "selector",
		payload
	);
	if (newNodeId) {
		const dir = store.settings?.layout_direction === "Top to Bottom" ? "TB" : "LR";
		setTimeout(() => {
			layoutGraph(dir);
			// Auto-open config for nodes that require immediate configuration
			const NEEDS_CONFIG_NOW = ["Condition", "Loop", "Switch"];
			const insertedNode = store.nodes.find((n) => n.id === newNodeId);
			if (insertedNode && NEEDS_CONFIG_NOW.includes(insertedNode.data?.action_type)) {
				store.open_config(newNodeId);
			}
		}, 80);
	}
}
function autoConnectStartNode() {
	const startNode = (store.nodes || []).find((el) => el.id === "start" || el.type === "start");
	if (!startNode) return;

	// Check if start node has any outgoing edges
	const hasStartEdge = (store.edges || []).some((el) => el.source === startNode.id);
	if (hasStartEdge) return;

	const firstNode = (store.nodes || []).find(
		(el) => el.type !== "start" && el.data?.is_enabled !== 0
	);
	if (firstNode) {
		store.edges.push({
			id: `e-${startNode.id}-${firstNode.id}`,
			source: startNode.id,
			target: firstNode.id,
			sourceHandle: "default",
			type: "add",
			animated: true,
		});
	}
}

function onNodeClick(event) {
	store.selected_id = event.node.id;

	const trigger = store.settings?.open_config_on || "Click";
	if (trigger === "Click" && event.node.type !== "start") {
		store.open_config(event.node.id);
	}
}

function onNodeDblClick(event) {
	store.selected_id = event.node.id;

	const trigger = store.settings?.open_config_on || "Click";
	if (trigger === "Double Click" && event.node.type !== "start") {
		store.open_config(event.node.id);
	}
}
function onPaneClick() {
	store.selected_id = null;
	store.show_sidebar = false;
}

function onConnect(params) {
	const sourceHandle = params.sourceHandle || "default";
	const id = `e-${params.source}-${params.target}-${sourceHandle}`;

	// Check for existing connection to avoid duplicates
	const exists = (store.edges || []).some(
		(e) =>
			e.source === params.source &&
			e.target === params.target &&
			(e.sourceHandle || "default") === sourceHandle
	);

	if (exists) {
		// console.warn("Connection already exists", id);
		return;
	}

	const newEdge = {
		id,
		source: params.source,
		target: params.target,
		sourceHandle,
		type: "add",
		animated: store.nodes.find((el) => el.id === params.source)?.type === "start",
	};
	store.edges = [...store.edges, newEdge];
	store.mark_dirty();
}

function onNodesChange(changes) {
	const hasDrag = changes.some((c) => c.type === "position" && c.dragging === false);
	if (hasDrag) store.mark_position_change();
}

function onEdgesChange(changes) {
	changes.forEach((change) => {
		if (change.type === "remove") {
			store.delete_edge(change.id);
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
