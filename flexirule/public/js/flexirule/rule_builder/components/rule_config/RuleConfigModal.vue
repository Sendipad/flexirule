<template>
	<Teleport to="body">
		<transition name="modal-fade">
			<div v-if="modelValue" class="config-modal-overlay" @click.self="cancel">
				<div class="config-modal-container">
					<header class="config-modal-header">
						<div class="header-left">
							<div
								class="header-icon"
								:style="{
									background: contract?.css?.bg || '#f1f5f9',
									color: contract?.css?.color || '#64748b',
								}"
							>
								<i
									:class="
										getIcon(draftNode?.data?.action_type || draftNode?.type)
									"
								></i>
							</div>
							<div class="header-titles">
								<h3>{{ title }}</h3>
								<div class="modal-breadcrumb">
									<span
										class="type-badge"
										:style="{ color: contract?.css?.color }"
									>
										{{ draftNode?.data?.action_id }}
									</span>
									<i
										class="fa fa-chevron-right small mx-1 text-muted opacity-50"
									></i>
									<span class="text-muted">{{
										draftNode?.data?.action_type
									}}</span>
								</div>
							</div>
						</div>

						<div class="header-right">
							<div class="header-toolbar">
								<!-- Navigation Group -->
								<div class="toolbar-group navigation">
									<button
										class="toolbar-btn"
										@click="ruleStore.prev_config_node()"
										:disabled="currentNodeIndex <= 0"
										:title="__('Previous')"
									>
										<i class="fa fa-chevron-left"></i>
									</button>
									<div class="toolbar-status">
										<span class="current">{{ currentNodeIndex + 1 }}</span>
										<span class="total">/ {{ totalNodes }}</span>
									</div>
									<button
										class="toolbar-btn"
										@click="ruleStore.next_config_node()"
										:disabled="currentNodeIndex >= totalNodes - 1"
										:title="__('Next')"
									>
										<i class="fa fa-chevron-right"></i>
									</button>
								</div>

								<div class="toolbar-divider"></div>

								<!-- Toggles Group -->
								<div class="toolbar-group toggles">
									<button
										class="toolbar-btn"
										:class="{ active: showContextSidebar }"
										@click="showContextSidebar = !showContextSidebar"
										:title="__('Context Variables')"
									>
										<i class="fa fa-database"></i>
										<span>{{ __("Variables") }}</span>
									</button>
									<button
										class="toolbar-btn"
										:class="{ active: showSettingsBar }"
										@click="showSettingsBar = !showSettingsBar"
										:title="__('Action Settings')"
									>
										<i class="fa fa-cog"></i>
										<span>{{ __("Settings") }}</span>
									</button>
								</div>

								<div class="toolbar-divider"></div>

								<!-- Close -->
								<button
									class="toolbar-btn close"
									@click="cancel"
									:title="__('Close')"
								>
									<i class="fa fa-times"></i>
								</button>
							</div>
						</div>
					</header>

					<div class="config-modal-body">
						<!-- Logic Mode (Conditions) -->
						<div
							v-show="uiStore.config_modal_mode === 'logic'"
							class="conditions-container"
						>
							<div class="conditions-view">
								<ConditionStep
									:node="draftNode"
									:read-only="ruleStore.is_read_only"
									:ref="panelRefs.logic"
								/>
							</div>
						</div>

						<!-- Standard Action Setup -->
						<div
							v-show="uiStore.config_modal_mode !== 'logic'"
							class="standard-config-container"
						>
							<!-- Start Node Setup (Full width) -->
							<div v-if="draftNode?.type === 'start'" class="start-node-setup">
								<div class="setup-container">
									<header class="section-header mb-4">
										<h4>{{ __("Trigger Configuration") }}</h4>
										<p class="text-muted">
											{{
												__("Configure how and when this rule is triggered.")
											}}
										</p>
									</header>
									<StartNodeProperties
										:nodeData="draftNode.data"
										:readOnly="ruleStore.is_read_only"
										@update:field="(f, v) => (draftNode.data[f] = v)"
										@open:conditions="uiStore.config_modal_mode = 'logic'"
									/>
								</div>
							</div>

							<!-- Unified Action Setup -->
							<div v-else-if="draftNode" class="panels-container-modern">
								<!-- Context Variable Sidebar (Left) -->
								<aside class="sidebar-variables" v-if="showContextSidebar">
									<InputPanel
										:node="draftNode"
										:readOnly="ruleStore.is_read_only"
										mode="variables"
									/>
								</aside>

								<!-- Main Config Area -->
								<div class="config-main-area">
									<div class="config-scroll-container">
										<div class="config-content-wrapper">
											<!-- Top Settings Bar (Integrated) -->
											<div
												class="integrated-settings-bar"
												v-if="showSettingsBar"
											>
												<ActionSettings
													:node="draftNode"
													:readOnly="ruleStore.is_read_only"
													@update:field="on_update_action_field"
												/>
											</div>

											<!-- Split View: Setup (Left) & Config (Right/Center) -->
											<div
												class="action-core-layout"
												:class="{
													'input-panel-collapsed': collapseInputPanel,
												}"
											>
												<div class="core-setup-panel">
													<button
														class="panel-collapse-btn left"
														type="button"
														@click="
															collapseInputPanel = !collapseInputPanel
														"
														:title="
															collapseInputPanel
																? __('Expand Input Panel')
																: __('Collapse Input Panel')
														"
													>
														<i
															class="fa"
															:class="
																collapseInputPanel
																	? 'fa-chevron-right'
																	: 'fa-chevron-left'
															"
														></i>
													</button>
													<InputPanel
														:node="draftNode"
														:readOnly="ruleStore.is_read_only"
														:ref="panelRefs.input"
														mode="config"
													/>
												</div>
												<div class="core-config-panel">
													<ConfigurationPanel
														:node="draftNode"
														:readOnly="ruleStore.is_read_only"
														:ref="panelRefs.config"
													/>
												</div>
											</div>
										</div>
									</div>

									<!-- Right Side Utility Panel (Mutation & Results) -->
									<aside
										class="sidebar-mutation"
										:class="{ collapsed: collapseOutputPanel }"
									>
										<button
											class="panel-collapse-btn right"
											type="button"
											@click="collapseOutputPanel = !collapseOutputPanel"
											:title="
												collapseOutputPanel
													? __('Expand Output Panel')
													: __('Collapse Output Panel')
											"
										>
											<i
												class="fa"
												:class="
													collapseOutputPanel
														? 'fa-chevron-left'
														: 'fa-chevron-right'
												"
											></i>
										</button>
										<OutputPanel
											v-show="!collapseOutputPanel"
											:node="draftNode"
											:readOnly="ruleStore.is_read_only"
											:ref="panelRefs.output"
										/>
									</aside>
								</div>
							</div>

							<!-- Guide Sidebar (Right Sliding) -->
							<aside class="sidebar guide-sidebar" v-if="showGuideSidebar">
								<div class="guide-panel p-4">
									<h5>{{ __("Action Guide") }}</h5>
									<div class="guide-content mt-3" v-if="contract">
										<p>{{ contract.description }}</p>
									</div>
								</div>
							</aside>
						</div>
					</div>

					<footer class="config-modal-footer">
						<div class="footer-left">
							<div
								v-if="ruleStore.is_dirty && !ruleStore.is_read_only"
								class="dirty-indicator"
							>
								<i class="fa fa-circle mr-1"></i>
								{{ __("Unsaved Changes") }}
							</div>
						</div>
						<div class="footer-right">
							<button class="btn btn-default btn-sm" @click="cancel">
								{{ ruleStore.is_read_only ? __("Close") : __("Cancel") }}
							</button>
							<button
								v-if="!ruleStore.is_read_only"
								class="btn btn-primary btn-sm ml-2"
								@click="save"
							>
								{{ __("Save Action") }}
							</button>
						</div>
					</footer>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { ref, computed } from "vue";
import ResizablePanel from "./ResizablePanel.vue";
import InputPanel from "./InputPanel.vue";
import ConfigurationPanel from "./ConfigurationPanel.vue";
import OutputPanel from "./OutputPanel.vue";
import ActionSettings from "./ActionSettings.vue";
import ConditionStep from "./types/ConditionStep.vue";
import StartNodeProperties from "../StartNodeProperties.vue";
import { useRuleStore, useGraphStore, useUIStore } from "../../stores";
import { useRuleConfig } from "../../composables/useRuleConfig";
import { getContract } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: Boolean,
	node: Object,
});

const emit = defineEmits(["update:modelValue", "save"]);
const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const uiStore = useUIStore();
// Legacy support
const store = uiStore;

const { draftNode, panelRefs, save, cancel } = useRuleConfig(props, emit);

// -- Sidebar / Slide States --
const showContextSidebar = ref(false);
const showGuideSidebar = ref(false);
const showSettingsBar = ref(false);
const collapseInputPanel = ref(false);
const collapseOutputPanel = ref(false);

const contract = computed(() => {
	const type = draftNode.value?.data?.action_type || draftNode.value?.type;
	return type ? getContract(type) : null;
});

const totalNodes = computed(() => graphStore.nodes.length);
const currentNodeIndex = computed(() => {
	if (!uiStore.selected_id) return -1;
	return graphStore.nodes.findIndex((n) => n.id === uiStore.selected_id);
});

const title = computed(() => {
	if (!draftNode.value) return __("Rule Configuration");
	let baseTitle =
		draftNode.value.data?.action_label || draftNode.value.label || __("Rule Configuration");
	let suffix = uiStore.config_modal_mode === "logic" ? ` [${__("Logic")}]` : "";
	return baseTitle + suffix;
});

function on_update_action_field({ fieldname, value, scope }) {
	if (!draftNode.value?.data) return;
	if (fieldname && scope === "config") {
		let baseConfig = {};
		if (draftNode.value.data.config && typeof draftNode.value.data.config === "object") {
			baseConfig = draftNode.value.data.config;
		} else if (typeof draftNode.value.data.config === "string") {
			try {
				baseConfig = JSON.parse(draftNode.value.data.config) || {};
			} catch (e) {
				baseConfig = {};
			}
		}
		const nextConfig = {
			...baseConfig,
		};
		if (
			value === null ||
			value === undefined ||
			value === "" ||
			(typeof value === "object" && !Array.isArray(value) && !Object.keys(value).length)
		) {
			delete nextConfig[fieldname];
		} else {
			nextConfig[fieldname] = value;
		}
		draftNode.value.data.config = nextConfig;
		ruleStore.mark_dirty();
		return;
	}
	draftNode.value.data[fieldname] = value;
	ruleStore.mark_dirty();
}

function getIcon(type) {
	if (!type) return "fa fa-circle";
	const icons = {
		process: "fa fa-cog",
		condition: "fa fa-code-fork",
		loop: "fa fa-refresh",
		switch: "fa fa-random",
		"sub-rule": "fa fa-cube",
		wait: "fa fa-clock-o",
		start: "fa fa-play",
		stop: "fa fa-stop",
		"query records": "fa fa-search",
		"document action": "fa fa-plus-circle",
		"set value": "fa fa-edit",
		notify: "fa fa-bell",
	};
	return icons[type.toLowerCase()] || "fa fa-circle";
}
</script>

<style scoped>
.config-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(15, 23, 42, 0.4);
	backdrop-filter: blur(12px);
	z-index: 1040;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 24px;
}

.config-modal-container {
	background: #fff;
	width: 100%;
	height: 100%;
	max-width: 1800px;
	border-radius: 20px;
	box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.3);
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid #e2e8f0;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.config-modal-header {
	height: 80px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 32px;
	border-bottom: 1px solid #e2e8f0;
	background: #fff;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 16px;
	min-width: 300px;
}

.header-icon {
	width: 48px;
	height: 48px;
	border-radius: 12px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.header-icon i {
	font-size: 20px;
}

.header-titles h3 {
	margin: 0;
	font-size: 18px;
	font-weight: 700;
	color: #1e293b;
}

.modal-breadcrumb {
	display: flex;
	align-items: center;
	font-size: 12px;
	margin-top: 2px;
}

.header-right {
	display: flex;
	align-items: center;
}

.header-toolbar {
	display: flex;
	align-items: center;
	background: #f1f5f9;
	padding: 4px;
	border-radius: 12px;
	gap: 4px;
}

.toolbar-group {
	display: flex;
	align-items: center;
	gap: 2px;
}

.toolbar-btn {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 12px;
	border-radius: 8px;
	border: none;
	background: transparent;
	color: #64748b;
	font-size: 12px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
	height: 32px;
}

.toolbar-btn:hover:not(:disabled) {
	background: #fff;
	color: #1e293b;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.toolbar-btn.active {
	background: var(--primary);
	color: #fff;
}

.toolbar-btn:disabled {
	opacity: 0.3;
	cursor: default;
}

.toolbar-btn.close {
	padding: 0;
	width: 32px;
	justify-content: center;
}

.toolbar-btn.close:hover {
	background: #fee2e2;
	color: #ef4444;
}

.toolbar-status {
	display: flex;
	align-items: center;
	padding: 0 8px;
	font-size: 11px;
	font-weight: 800;
	color: #475569;
	user-select: none;
}

.toolbar-status .total {
	opacity: 0.4;
	margin-left: 4px;
}

.toolbar-divider {
	width: 1px;
	height: 16px;
	background: #cbd5e1;
	margin: 0 4px;
}

.config-modal-body {
	flex: 1;
	overflow: hidden;
	display: flex;
	position: relative;
	background: #f8fafc;
}

.conditions-container,
.standard-config-container {
	flex: 1;
	display: flex;
	flex-direction: column;
	height: 100%;
	width: 100%;
}

.conditions-view {
	padding: 32px;
	max-width: 1200px;
	margin: 0 auto;
	width: 100%;
}

.start-node-setup {
	padding: 40px;
	overflow-y: auto;
	height: 100%;
}

.setup-container {
	max-width: 900px;
	margin: 0 auto;
}

.panels-container-modern {
	flex: 1;
	display: flex;
	overflow: hidden;
	height: 100%;
}

.sidebar-variables {
	width: 260px;
	border-right: 1px solid #e2e8f0;
	background: #fff;
	display: flex;
	flex-direction: column;
}

.config-main-area {
	flex: 1;
	display: flex;
	overflow: hidden;
}

.config-scroll-container {
	flex: 1;
	overflow-y: auto;
	background: #f8fafc;
	padding: 10px;
}

.config-content-wrapper {
	max-width: 1600px;
	margin: 0 auto;
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.integrated-settings-bar {
	background: #fff;
	border-radius: 12px;
	padding: 16px;
	border: 1px solid #e2e8f0;
}

.action-core-layout {
	display: grid;
	grid-template-columns: minmax(220px, 25%) minmax(0, 75%);
	gap: 8px;
	align-items: start;
}

.core-setup-panel,
.core-config-panel {
	background: #fff;
	border-radius: 16px;
	border: 1px solid #e2e8f0;
	overflow: hidden;
	position: relative;
}

.sidebar-mutation {
	width: 20%;
	min-width: 220px;
	max-width: 380px;
	border-left: 1px solid #e2e8f0;
	background: #fff;
	display: flex;
	flex-direction: column;
	position: relative;
	transition: width 0.2s ease;
	margin-left: 8px;
}

.action-core-layout.input-panel-collapsed {
	grid-template-columns: 44px minmax(0, 1fr);
}

.action-core-layout.input-panel-collapsed .core-setup-panel {
	min-width: 44px;
}

.action-core-layout.input-panel-collapsed .core-setup-panel :deep(.input-panel) {
	display: none;
}

.sidebar-mutation.collapsed {
	width: 44px;
	min-width: 44px;
	max-width: 44px;
}

.panel-collapse-btn {
	position: absolute;
	top: 10px;
	z-index: 5;
	width: 26px;
	height: 26px;
	border-radius: 50%;
	border: 1px solid #dbe2ea;
	background: #fff;
	color: #64748b;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.2s ease;
}

.panel-collapse-btn:hover {
	color: #1e293b;
	border-color: #94a3b8;
}

.panel-collapse-btn.left {
	right: 8px;
}

.panel-collapse-btn.right {
	left: 8px;
}

.action-core-layout.input-panel-collapsed .panel-collapse-btn.left {
	left: 50%;
	right: auto;
	transform: translateX(-50%);
	background: #f8fafc;
	border-color: #cbd5e1;
	z-index: 8;
}

.sidebar-mutation.collapsed .panel-collapse-btn.right {
	left: 50%;
	transform: translateX(-50%);
	background: #f8fafc;
	border-color: #cbd5e1;
}

@media (min-width: 1400px) {
	.config-main-area {
		display: grid;
		grid-template-columns: minmax(0, 80%) minmax(220px, 20%);
		column-gap: 8px;
	}
}

.guide-sidebar {
	width: 350px;
	border-left: 1px solid #e2e8f0;
	background: #fff;
	position: absolute;
	right: 0;
	top: 0;
	height: 100%;
	z-index: 10;
	box-shadow: -10px 0 30px rgba(0, 0, 0, 0.05);
}

.config-modal-footer {
	height: 72px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 32px;
	border-top: 1px solid #e2e8f0;
	background: #fff;
}

.footer-left {
	display: flex;
	align-items: center;
}

.dirty-indicator {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12px;
	font-weight: 600;
	color: #f59e0b;
	padding: 6px 12px;
	background: #fffbeb;
	border-radius: 20px;
	border: 1px solid #fef3c7;
}

.dirty-indicator i {
	font-size: 8px;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
	transition: all 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
	opacity: 0;
	transform: scale(0.95);
}

@media (max-width: 1199px) {
	.config-main-area {
		display: flex;
	}

	.action-core-layout {
		grid-template-columns: minmax(220px, 34%) minmax(0, 66%);
		gap: 8px;
	}

	.sidebar-mutation {
		width: 280px;
		min-width: 240px;
		margin-left: 8px;
	}
}
</style>
