<template>
	<div class="rule-builder-container" :class="{ 'is-read-only': isReadOnly, 'is-rtl': isRTL }">
		<!-- Main Canvas + Sidebar -->
		<div class="builder-main">
			<div
				class="canvas-container"
				:class="{
					'has-execution-bottom':
						uiStore.test_execution_steps?.length &&
						ruleStore.settings?.layout_direction !== 'Top to Bottom',
					'has-execution-right':
						uiStore.test_execution_steps?.length &&
						ruleStore.settings?.layout_direction === 'Top to Bottom',
				}"
				ref="flowWrapper"
				@dragover="onDragOver"
				@drop="onDrop"
			>
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
						<ActionZone mode="node" v-bind="nodeProps" />
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

						<div class="btn-group controls-row">
							<button
								class="btn btn-sm btn-default d-inline-flex align-items-center gap-2"
								@click="toggleLayout"
								:title="__('Switch Layout Orientation')"
							>
								<i
									class="fa"
									:class="isHorizontal ? 'fa-columns' : 'fa-align-justify'"
								></i>
								<span class="small font-weight-bold">{{
									isHorizontal ? __("Vertical") : __("Horizontal")
								}}</span>
							</button>
						</div>

						<div class="divider-vertical"></div>

						<div v-if="isReadOnly" class="read-only-badge mr-2">
							<i class="fa fa-lock"></i> {{ __("Read Only") }}
						</div>

						<div class="quick-actions-wrap">
							<button
								ref="quickActionsButtonRef"
								class="btn btn-sm btn-default quick-actions-btn d-inline-flex align-items-center"
								@click="toggleQuickActions"
								:title="__('Settings')"
								aria-haspopup="menu"
								:aria-expanded="showQuickActions ? 'true' : 'false'"
							>
								<svg
									class="flexirule-icon"
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 804 804"
								>
									<g stroke="none" fill="currentColor">
										<g transform="matrix(.96409 0 0 .98565 -125.5 -146.24)">
											<path
												d="m705.63 245.23v118.94c.00063 24.266-20.136 43.924-44.944 43.878l-49.363-.0951c-24.822-.047-65.066-.12134-89.888-.21996-50.6-.20106-61.754-.36246-100.28.90558-56.763.37714-83.543 57.19-85.606 80.327-2.0629 23.136-3.3285 111.05-3.3285 111.05v113.63c-7.1191 5.6674-11.252 14.168-11.252 23.147.00031 16.482 13.661 29.842 30.512 29.842 16.852.00077 30.513-13.359 30.514-29.842-.00026-9.0611-4.2091-17.631-11.44-23.295l2.3581-111.33c.55829-44.584-8.4702-133.06 55.566-153.26 45.662-1.3891 147.5-.89275 201.43-2.8019l-97.502 109.65h-110.99v286.22c-6e-4 13.945-11.559 25.25-25.816 25.249h-114.21l.0223-290.41c.0104-104 .43581-192.84.94406-197.59 6.2131-57.668 47.784-107.74 104.83-126.24 22.996-7.458 12.25-6.9996 173.48-7.3932zm-26.802 200.29c7.8366.43409 14.932 1.6116 24.728 3.9592 39.654 9.5054 71.883 33.601 90.605 67.72 11.607 21.161 16.48 40.47 16.408 64.95-.16596 57.15-35.276 105.76-91.298 126.39-13.152 4.8445-28.587 7.4679-44.063 7.4923-6.5036.0101-11.099.41716-10.891.96502 38.356 47.659 91.974 89.215 133.56 135.25l7.6376 7.6112c2.7446 2.7354.7641 7.3526-3.1543 7.3536h-216.81l-25.153-47.431c-33.352-62.837-67.301-125.44-99.556-188.8 0-.80962 21.969-1.2031 78.572-1.4029 0 0 78.59-.16015 78.572-.27742-.0184-.11728 28.006-12.313 28.006-36.502s-27.871-35.848-31.002-36.473c-3.1311-.62449-62.35-1.2662-62.35-1.2662l97.015-109.05c12.763-.62606 21.34-.93543 29.177-.50133z"
											/>
										</g>
										<path
											transform="matrix(.81811 0 0 .81811 -80.123 -11.959)"
											d="m383.94 723.53c0 13.919-11.284 25.203-25.203 25.203-13.919 0-25.203-11.284-25.203-25.203 0-13.919 11.284-25.203 25.203-25.203 13.919 0 25.203 11.284 25.203 25.203z"
										/>
									</g>
								</svg>
							</button>
						</div>
					</Panel>
				</VueFlow>
				<DebuggerPath
					v-if="uiStore.test_execution_steps?.length"
					:layout="ruleStore.settings?.layout_direction === 'Top to Bottom' ? 'TB' : 'LR'"
				/>
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
		<CommandPalette v-model="uiStore.show_command_palette" />
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
					<template v-for="item in quickActionItems" :key="item.key || item.type">
						<div v-if="item.type === 'divider'" class="quick-action-divider"></div>
						<button
							v-else
							class="quick-action-item"
							role="menuitem"
							:disabled="item.disabled"
							@click="runQuickAction(item)"
						>
							<i :class="['fa', item.icon]"></i>
							<span>{{ item.label }}</span>
							<kbd v-if="item.shortcut" class="shortcut-badge">{{
								item.shortcut
							}}</kbd>
						</button>
					</template>
				</div>
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
import { useCanvasLayout } from "./composables/useCanvasLayout";
import { useClipboard } from "./composables/useClipboard";
import { useKeyboardRegistry } from "./composables/useKeyboardRegistry";
import { isTerminalAction } from "../core/contracts";
import { mapActionTypeToNodeType } from "./composables/useActionTypeMapper";

import { generateShortId } from "./utils/schema_utils.js";
import "../utils/utils.js";

import StartNode from "./components/nodes/StartNode.vue";
import ProcessNode from "./components/nodes/ProcessNode.vue";
import ConditionNode from "./components/nodes/ConditionNode.vue";
import LoopNode from "./components/nodes/LoopNode.vue";
import StopNode from "./components/nodes/StopNode.vue";
import ActionZone from "./components/ActionZone.vue";

import Sidebar from "./components/Sidebar.vue";
import RuleConfigModal from "./components/rule_config/RuleConfigModal.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import AddNodeEdge from "./components/AddNodeEdge.vue";
import DebuggerPath from "./components/debugger/DebuggerPath.vue";

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
const { isHorizontal, toggleLayout } = useCanvasLayout();
const { copySelectedToClipboard, pasteFromClipboard } = useClipboard();
const { registerShortcut, pushContext, popContext } = useKeyboardRegistry();
const showQuickActions = ref(false);
const quickActionsButtonRef = ref(null);
const quickActionsMenuRef = ref(null);
const quickActionsMenuStyle = ref({});

const flowWrapper = ref(null);
const mousePos = ref({ x: 0, y: 0 });
const showDisabledNodes = ref(true);

const quickActionItems = computed(() => [
	{
		key: "undo",
		label: __("Undo"),
		icon: "fa-undo",
		shortcut: "Ctrl Z",
		disabled: !ruleStore.can_undo(),
	},
	{
		key: "redo",
		label: __("Redo"),
		icon: "fa-repeat",
		shortcut: "Ctrl Y",
		disabled: !ruleStore.can_redo(),
	},
	{ type: "divider" },
	{ key: "save", label: __("Save"), icon: "fa-floppy-o", shortcut: "Ctrl S" },
	{ key: "test", label: __("Debug"), icon: "fa-bug", shortcut: "Alt D" },
	{
		key: "status",
		label: isReadOnly.value ? __("Unlock for editing") : __("Set to active"),
		icon: isReadOnly.value ? "fa-unlock" : "fa-rocket",
		shortcut: "Alt Shift A",
	},
	{ key: "shortcuts", label: __("Keyboard shortcuts"), icon: "fa-keyboard-o", shortcut: "?" },
	{ key: "layout", label: __("Auto Layout"), icon: "fa-sitemap", shortcut: "Alt L" },
	{ key: "permissions", label: __("Set Permission"), icon: "fa-shield" },
	{ key: "copy", label: __("Copy"), icon: "fa-copy", shortcut: "Ctrl C" },
	{
		key: "disabled_nodes",
		label: showDisabledNodes.value ? __("Hide Disabled Nodes") : __("Show Disabled Nodes"),
		icon: showDisabledNodes.value ? "fa-eye-slash" : "fa-eye",
	},
	{ key: "preferences", label: __("Preference"), icon: "fa-sliders" },
]);

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
	uiStore.show_test_sidebar = false;
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
	const isRTLValue = isRTL.value;
	const leftPos = isRTLValue ? rect.right - width : rect.left;

	quickActionsMenuStyle.value = {
		position: "fixed",
		top: `${rect.bottom + 8}px`,
		left: `${Math.max(12, Math.min(leftPos, window.innerWidth - width - 12))}px`,
		width: `${width}px`,
		zIndex: 12000,
	};
}

function runQuickAction(item) {
	const actions = {
		undo: () => ruleStore.undo(),
		redo: () => ruleStore.redo(),
		save: () => ruleStore.save_changes(),
		test: () => flexirule.debug.show_dialog(),
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
	// Small delay to ensure fitView doesn't trigger a trailing position change
	setTimeout(() => {
		uiStore.is_initializing = false;
	}, 150);
}

function onDebugProgress(data) {
	if (data.rule === ruleStore.rule_name) {
		uiStore.add_test_progress_result(data.result);
	}
}

const unregisterShortcuts = ref([]);

onMounted(async () => {
	document.body.classList.add("fxr-builder-active");
	if (props.rule) ruleStore.rule_name = props.rule;
	await ruleStore.fetch();

	pushContext("canvas");

	// Register shortcuts
	unregisterShortcuts.value = [
		registerShortcut({
			key: "s",
			mod: true,
			callback: () => ruleStore.save_changes(),
			description: "Save changes",
		}),
		registerShortcut({
			key: "z",
			mod: true,
			context: "canvas",
			callback: () => {
				if (ruleStore.can_undo()) ruleStore.undo();
			},
			description: "Undo",
		}),
		registerShortcut({
			key: "y",
			mod: true,
			context: "canvas",
			callback: () => {
				if (ruleStore.can_redo()) ruleStore.redo();
			},
			description: "Redo",
		}),
		registerShortcut({
			key: "z",
			mod: true,
			shift: true,
			context: "canvas",
			callback: () => {
				if (ruleStore.can_redo()) ruleStore.redo();
			},
			description: "Redo",
		}),
		registerShortcut({
			key: "c",
			mod: true,
			context: "canvas",
			callback: () => {
				if (window.getSelection().toString().length === 0) {
					copySelectedToClipboard();
				}
			},
			description: "Copy nodes",
		}),
		registerShortcut({
			key: "v",
			mod: true,
			context: "canvas",
			callback: () => pasteFromClipboardWrapper(),
			description: "Paste nodes",
		}),
		registerShortcut({
			key: "?",
			shift: true,
			callback: () => (uiStore.show_shortcuts_help = !uiStore.show_shortcuts_help),
			description: "Shortcuts Help",
		}),
		registerShortcut({
			key: "1",
			alt: true,
			callback: () => {
				if (uiStore.selected_id) uiStore.show_sidebar = true;
			},
			description: "Focus Sidebar",
		}),
		registerShortcut({
			key: "k",
			mod: true,
			callback: () => (uiStore.show_command_palette = !uiStore.show_command_palette),
			description: "Command Palette",
		}),
		registerShortcut({
			key: "d",
			alt: true,
			callback: () => flexirule.debug.show_dialog(),
			description: "Debug Rule",
		}),
		registerShortcut({
			key: "l",
			alt: true,
			callback: () => runAutoLayout(),
			description: "Auto Layout",
		}),
		registerShortcut({
			key: "a",
			alt: true,
			shift: true,
			callback: () => toggleRuleAccess(),
			description: "Toggle Active/Draft",
		}),
	];

	window.addEventListener("keydown", handleKeydown);
	window.addEventListener("keyup", handleKeyup);
	window.addEventListener("mousemove", updateMousePos);
	window.addEventListener("mousedown", handleGlobalMouseDown, true);
	window.addEventListener("resize", updateQuickActionsPosition);
	window.addEventListener("flexirule:show-shortcuts-help", showShortcutsHelp);

	if (window.frappe?.realtime) {
		frappe.realtime.on("flexirule_debug_progress", onDebugProgress);
	}

	// Expose layoutGraph to window for CommandPalette
	window.fxrRuleBuilder = {
		...window.fxrRuleBuilder,
		layoutGraph,
	};
});

onUnmounted(() => {
	document.body.classList.remove("fxr-builder-active");
	popContext("canvas");
	unregisterShortcuts.value.forEach((unreg) => unreg());
	window.removeEventListener("keydown", handleKeydown);
	window.removeEventListener("keyup", handleKeyup);
	window.removeEventListener("mousemove", updateMousePos);
	window.removeEventListener("mousedown", handleGlobalMouseDown, true);
	window.removeEventListener("resize", updateQuickActionsPosition);
	window.removeEventListener("flexirule:show-shortcuts-help", showShortcutsHelp);
	if (window.frappe?.realtime) {
		frappe.realtime.off("flexirule_debug_progress", onDebugProgress);
	}
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
	if (e.key === "Alt" && uiStore.is_developer_mode) {
		uiStore.is_field_reveal_active = true;
	}
}

function handleKeyup(e) {
	if (e.key === "Alt") {
		uiStore.is_field_reveal_active = false;
	}
}

watch(
	() => uiStore.show_config_modal,
	(val) => {
		if (val) popContext("canvas");
		else pushContext("canvas");
	}
);

watch(
	() => uiStore.is_field_reveal_active,
	(val) => {
		if (val) {
			document.body.classList.add("is-field-reveal-active");
		} else {
			document.body.classList.remove("is-field-reveal-active");
		}
	}
);

function handleGlobalMouseDown(event) {
	if (
		showQuickActions.value &&
		!quickActionsMenuRef.value?.contains(event.target) &&
		!quickActionsButtonRef.value?.contains(event.target)
	) {
		closeQuickActions();
	}

	if (event.altKey && uiStore.is_field_reveal_active) {
		const fieldEl = event.target?.closest?.("[data-fxr-fieldname]");
		const fieldname = fieldEl?.dataset?.fxrFieldname;
		if (fieldname) {
			event.preventDefault();
			event.stopPropagation();
			copyFieldname(fieldname);
		}
	}
}

function copyFieldname(fieldname) {
	if (!fieldname) return;
	const copyText = (text) => {
		if (window.frappe && frappe.utils && frappe.utils.copy_to_clipboard) {
			frappe.utils.copy_to_clipboard(text);
			return Promise.resolve();
		}
		if (navigator.clipboard && navigator.clipboard.writeText) {
			return navigator.clipboard.writeText(text);
		}
		return Promise.reject("Clipboard API not available");
	};

	copyText(fieldname)
		.then(() => {
			frappe.show_alert(
				{
					message: __("Fieldname copied: {0}", [fieldname]),
					indicator: "green",
				},
				2
			);
		})
		.catch((err) => {
			console.error("Failed to copy fieldname:", err);
		});
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
	if (uiStore.is_initializing || uiStore.is_performing_layout) return;
	const hasDrag = changes.some((c) => c.type === "position" && c.dragging === false);
	if (hasDrag) ruleStore.mark_position_change();
}

function onEdgesChange(changes) {
	if (uiStore.is_initializing) return;
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
	min-width: 30px;
	height: 30px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 0;
}

.flexirule-icon {
	width: 16px;
	height: 16px;
	color: currentColor;
	transition: color 0.2s ease;
}

.quick-actions-btn:hover .flexirule-icon,
.quick-actions-btn[aria-expanded="true"] .flexirule-icon {
	color: var(--fxr-accent);
}

.fxr-headless-menu {
	background-color: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border-subtle);
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

.quick-action-divider {
	height: 1px;
	background-color: var(--fxr-border-subtle);
	margin: 4px 8px;
}

.shortcut-badge {
	background: var(--fxr-surface-3);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 4px;
	padding: 2px 5px;
	font-size: 9px;
	font-weight: 600;
	color: var(--fxr-text-soft);
	font-family: var(--font-stack-monospaced);
	line-height: 1;
	box-shadow: 0 1px 0 rgba(0, 0, 0, 0.05);
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
	background-color: color-mix(in srgb, var(--fxr-bg-page) 88%, var(--fxr-surface));
	position: relative;
	order: 1;
	transition: all 0.3s ease;
}

.canvas-container.has-execution-bottom {
	padding-bottom: 90px;
}

.canvas-container.has-execution-right {
	padding-right: 210px;
}

.canvas-container :deep(.vue-flow__pane) {
	cursor: grab;
}

.canvas-container :deep(.vue-flow__pane:active) {
	cursor: grabbing;
}

:deep(.status-error .execution-badge) {
	background: var(--red-500, #dc2626) !important;
}

:deep(.status-running .execution-badge) {
	background: var(--blue-600, #2563eb) !important;
}

:deep(.executed .execution-badge) {
	background: var(--green-600, #16a34a) !important;
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

.is-read-only-flow :deep(.vue-flow__node.executed) {
	filter: none !important;
	opacity: 1 !important;
}

.read-only-badge {
	background: var(--fxr-warning-soft, #fff7ed);
	color: var(--orange-800, #9a3412);
	padding: 4px 10px;
	border-radius: 6px;
	border: 1px solid color-mix(in srgb, var(--orange-300, #ffedd5) 70%, var(--fxr-surface));
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
