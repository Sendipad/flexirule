<template>
	<Teleport to="body">
		<transition name="modal-fade">
			<div v-if="modelValue" class="config-modal-overlay" @click.self="cancel">
				<div class="config-modal-container">
					<header
						class="config-modal-header"
						@touchstart="handleTouchStart"
						@touchmove="handleTouchMove"
						@touchend="handleTouchEnd"
					>
						<div class="header-left">
							<div
								class="header-icon"
								:style="{
									background: actionPresentation.background,
									color: actionPresentation.color,
								}"
							>
								<i :class="actionPresentation.icon"></i>
							</div>
							<div class="header-titles">
								<div class="title-wrapper">
									<template v-if="isEditingLabel">
										<input
											ref="labelInputRef"
											v-model="labelInput"
											class="title-input"
											@blur="saveLabel"
											@keyup.enter="saveLabel"
											@keyup.esc="isEditingLabel = false"
										/>
									</template>
									<h3
										v-else
										@click="startEditingLabel"
										:class="{ editable: canEditLabel }"
										:title="canEditLabel ? __('Click to edit label') : ''"
									>
										{{ title }}
									</h3>
									<div
										v-if="ruleStore.is_dirty && !ruleStore.is_read_only"
										class="dirty-badge"
									>
										<i class="fa fa-circle"></i>
										<span>{{ __("Unsaved") }}</span>
									</div>
								</div>
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
								<!-- Standard Desktop Layout -->
								<template v-if="!isMobile">
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
								</template>

								<!-- Mobile/Compact Minimal Info -->
								<template v-else>
									<div class="toolbar-status mobile">
										<span class="current">{{ currentNodeIndex + 1 }}</span>
										<span class="total">/ {{ totalNodes }}</span>
									</div>
									<div class="toolbar-divider"></div>
								</template>

								<!-- Primary Actions (Always Visible) -->
								<div class="toolbar-group actions" v-if="!ruleStore.is_read_only">
									<button
										class="toolbar-btn save-action"
										@click="save"
										:title="__('Save')"
									>
										<i class="fa fa-save"></i>
										<span class="btn-label" v-if="!isMobile">{{
											__("Save")
										}}</span>
									</button>
								</div>

								<div class="toolbar-divider" v-if="!ruleStore.is_read_only"></div>

								<!-- Overflow Menu for Mobile -->
								<template v-if="isMobile">
									<div class="overflow-menu-wrapper">
										<button
											ref="overflowTriggerRef"
											class="toolbar-btn overflow-trigger"
											:class="{ active: isOverflowOpen }"
											@click="toggleOverflow"
											@keydown="handleOverflowTriggerKeydown"
											:title="__('More Actions')"
											aria-haspopup="true"
											:aria-expanded="isOverflowOpen"
											aria-controls="config-overflow-menu"
											id="config-overflow-trigger"
										>
											<i class="fa fa-ellipsis-v"></i>
										</button>

										<Teleport to="body">
											<div
												v-if="isOverflowOpen"
												class="fxr-overflow-dropdown"
												:style="overflowMenuStyle"
												ref="overflowMenuRef"
												id="config-overflow-menu"
												role="menu"
												aria-labelledby="config-overflow-trigger"
												@keydown="handleOverflowMenuKeydown"
											>
												<div class="overflow-menu-items">
													<div class="menu-section" role="none">
														<div
															class="section-label"
															role="presentation"
														>
															{{ __("Navigation") }}
														</div>
														<button
															class="menu-item"
															role="menuitem"
															@click="
																ruleStore.prev_config_node();
																closeOverflow();
															"
															:disabled="currentNodeIndex <= 0"
														>
															<i class="fa fa-chevron-left"></i>
															<span>{{ __("Previous Action") }}</span>
														</button>
														<button
															class="menu-item"
															role="menuitem"
															@click="
																ruleStore.next_config_node();
																closeOverflow();
															"
															:disabled="
																currentNodeIndex >= totalNodes - 1
															"
														>
															<i class="fa fa-chevron-right"></i>
															<span>{{ __("Next Action") }}</span>
														</button>
													</div>

													<div
														class="menu-divider"
														role="separator"
													></div>

													<div class="menu-section" role="none">
														<div
															class="section-label"
															role="presentation"
														>
															{{ __("Views & Settings") }}
														</div>
														<button
															class="menu-item"
															role="menuitem"
															:class="{
																active: showContextSidebar,
															}"
															@click="
																showContextSidebar =
																	!showContextSidebar;
																closeOverflow();
															"
														>
															<i class="fa fa-database"></i>
															<span>{{
																__("Context Variables")
															}}</span>
														</button>
														<button
															class="menu-item"
															role="menuitem"
															:class="{ active: showSettingsBar }"
															@click="
																showSettingsBar = !showSettingsBar;
																closeOverflow();
															"
														>
															<i class="fa fa-cog"></i>
															<span>{{ __("Action Settings") }}</span>
														</button>
													</div>
												</div>
											</div>
										</Teleport>
									</div>
									<div class="toolbar-divider"></div>
								</template>

								<!-- Close (Always Visible) -->
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
						<transition :name="transitionName">
							<div :key="draftNode?.id || 'empty'" class="config-transition-wrapper">
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
									<div
										v-if="draftNode?.type === 'start'"
										class="start-node-setup"
									>
										<div class="setup-container">
											<header class="section-header mb-4">
												<h4>{{ __("Trigger Configuration") }}</h4>
												<p class="text-muted">
													{{
														__(
															"Configure how and when this rule is triggered."
														)
													}}
												</p>
											</header>
											<StartNodeProperties
												:nodeData="draftNode.data"
												:readOnly="ruleStore.is_read_only"
												@update:field="(f, v) => (draftNode.data[f] = v)"
												@open:conditions="
													uiStore.config_modal_mode = 'logic'
												"
											/>
										</div>
									</div>

									<!-- Unified Action Setup -->
									<div v-else-if="draftNode" class="panels-container-modern">
										<template v-if="!isCompactLayout">
											<aside
												class="sidebar-variables"
												v-if="showContextSidebar"
											>
												<InputPanel
													:node="draftNode"
													:readOnly="ruleStore.is_read_only"
													mode="variables"
												/>
											</aside>

											<div class="config-main-area">
												<div class="config-scroll-container">
													<div class="config-content-wrapper">
														<div
															class="integrated-settings-bar"
															v-if="showSettingsBar"
														>
															<ActionFieldProperties
																:nodeData="draftNode.data"
																:readOnly="ruleStore.is_read_only"
																@update:field="
																	on_update_action_field
																"
																@open:conditions="
																	uiStore.config_modal_mode =
																		'logic'
																"
															/>
														</div>

														<div
															class="action-core-layout"
															:class="{
																'input-panel-collapsed':
																	collapseInputPanel,
															}"
														>
															<div class="core-setup-panel">
																<button
																	class="panel-collapse-btn left"
																	type="button"
																	@click="
																		collapseInputPanel =
																			!collapseInputPanel
																	"
																	:title="
																		collapseInputPanel
																			? __(
																					'Expand Input Panel'
																			  )
																			: __(
																					'Collapse Input Panel'
																			  )
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
																	:readOnly="
																		ruleStore.is_read_only
																	"
																	:ref="panelRefs.input"
																	mode="config"
																/>
															</div>
															<div class="core-config-panel">
																<ConfigurationPanel
																	:node="draftNode"
																	:readOnly="
																		ruleStore.is_read_only
																	"
																	:ref="panelRefs.config"
																/>
															</div>
														</div>
													</div>
												</div>

												<aside
													class="sidebar-mutation"
													:class="{ collapsed: collapseOutputPanel }"
												>
													<button
														class="panel-collapse-btn right"
														type="button"
														@click="
															collapseOutputPanel =
																!collapseOutputPanel
														"
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
										</template>

										<template v-else>
											<div class="compact-config-layout">
												<div
													class="compact-tabs"
													role="tablist"
													@keydown="onCompactTabKeydown"
												>
													<button
														v-for="tab in compactTabs"
														:key="tab.key"
														class="compact-tab-btn"
														role="tab"
														:aria-selected="
															activeCompactTab === tab.key
														"
														:class="{
															active: activeCompactTab === tab.key,
														}"
														@click="activateCompactTab(tab.key)"
													>
														{{ tab.label }}
													</button>
												</div>

												<div class="compact-tab-content">
													<section
														v-show="activeCompactTab === 'input'"
														v-if="isCompactTabRendered('input')"
														ref="compactInputRef"
														class="compact-panel-shell"
														@scroll="
															rememberCompactScroll('input', $event)
														"
													>
														<InputPanel
															:node="draftNode"
															:readOnly="ruleStore.is_read_only"
															mode="config"
														/>
													</section>

													<section
														v-show="activeCompactTab === 'config'"
														v-if="isCompactTabRendered('config')"
														ref="compactConfigRef"
														class="compact-panel-shell"
														@scroll="
															rememberCompactScroll('config', $event)
														"
													>
														<div
															class="integrated-settings-bar"
															v-if="showSettingsBar"
														>
															<ActionFieldProperties
																:nodeData="draftNode.data"
																:readOnly="ruleStore.is_read_only"
																@update:field="
																	on_update_action_field
																"
																@open:conditions="
																	uiStore.config_modal_mode =
																		'logic'
																"
															/>
														</div>
														<ConfigurationPanel
															:node="draftNode"
															:readOnly="ruleStore.is_read_only"
														/>
													</section>

													<section
														v-show="activeCompactTab === 'output'"
														v-if="isCompactTabRendered('output')"
														ref="compactOutputRef"
														class="compact-panel-shell"
														@scroll="
															rememberCompactScroll('output', $event)
														"
													>
														<OutputPanel
															:node="draftNode"
															:readOnly="ruleStore.is_read_only"
														/>
													</section>
												</div>
											</div>
										</template>
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
						</transition>
					</div>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import InputPanel from "./InputPanel.vue";
import ConfigurationPanel from "./ConfigurationPanel.vue";
import OutputPanel from "./OutputPanel.vue";
import ActionFieldProperties from "../ActionFieldProperties.vue";
import ConditionStep from "./types/ConditionStep.vue";
import StartNodeProperties from "../StartNodeProperties.vue";
import { useRuleStore, useGraphStore, useUIStore } from "../../stores";
import { useRuleConfig } from "../../composables/useRuleConfig";
import { useResponsiveConfigLayout } from "../../composables/useResponsiveConfigLayout";
import { useFloatingDropdown } from "../../composables/useFloatingDropdown";
import { getContract, getActionPresentation } from "../../../core/contracts.js";

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
const {
	activeTab: activeCompactTab,
	tabs: compactTabs,
	isCompact: isCompactLayout,
	isMobile,
	updateViewportWidth,
	setActiveTab,
	rememberScroll,
	getRememberedScroll,
} = useResponsiveConfigLayout(1200, 768);

const {
	triggerRef: overflowTriggerRef,
	dropdownRef: overflowMenuRef,
	isOpen: isOverflowOpen,
	dropdownStyle: overflowMenuStyle,
	toggleDropdown: toggleOverflow,
	closeDropdown: closeOverflow,
} = useFloatingDropdown({
	matchTriggerWidth: false,
	minWidth: 200,
	offset: 8,
});

function handleOverflowTriggerKeydown(e) {
	if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
		e.preventDefault();
		if (!isOverflowOpen.value) {
			toggleOverflow();
		}
		nextTick(() => {
			const firstItem = overflowMenuRef.value?.querySelector(".menu-item:not(:disabled)");
			firstItem?.focus();
		});
	}
}

function handleOverflowMenuKeydown(e) {
	if (e.key === "Escape") {
		e.preventDefault();
		e.stopPropagation();
		closeOverflow();
		overflowTriggerRef.value?.focus();
		return;
	}

	const items = Array.from(
		overflowMenuRef.value?.querySelectorAll(".menu-item:not(:disabled)") || []
	);
	const currentIndex = items.indexOf(document.activeElement);

	if (e.key === "ArrowDown") {
		e.preventDefault();
		const nextIdx = (currentIndex + 1) % items.length;
		items[nextIdx]?.focus();
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		const prevIdx = (currentIndex - 1 + items.length) % items.length;
		items[prevIdx]?.focus();
	}
}

watch(isOverflowOpen, (val) => {
	if (!val) {
		// Restore focus to trigger when menu closes, if it was inside the menu
		if (overflowMenuRef.value?.contains(document.activeElement)) {
			overflowTriggerRef.value?.focus();
		}
	}
});

const renderedCompactTabs = ref(new Set(["config"]));
const compactInputRef = ref(null);
const compactConfigRef = ref(null);
const compactOutputRef = ref(null);

// -- Sidebar / Slide States --
const showContextSidebar = ref(false);
const showGuideSidebar = ref(false);
const showSettingsBar = ref(false);
const collapseInputPanel = ref(false);
const collapseOutputPanel = ref(false);

// -- Swipe Navigation --
const touchStartX = ref(0);
const touchStartY = ref(0);
const touchCurrentX = ref(0);
const isSwiping = ref(false);
const SWIPE_THRESHOLD = 50;

function handleTouchStart(e) {
	if (!isMobile.value) return;
	touchStartX.value = e.touches[0].clientX;
	touchStartY.value = e.touches[0].clientY;
	isSwiping.value = false;
}

function handleTouchMove(e) {
	if (!isMobile.value) return;
	const currentX = e.touches[0].clientX;
	const currentY = e.touches[0].clientY;
	const diffX = currentX - touchStartX.value;
	const diffY = currentY - touchStartY.value;

	// If horizontal movement is more than vertical, it's a swipe
	if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 10) {
		isSwiping.value = true;
		touchCurrentX.value = currentX;
		// Prevent scrolling when swiping header
		if (e.cancelable) e.preventDefault();
	}
}

function handleTouchEnd() {
	if (!isMobile.value || !isSwiping.value) return;

	const diffX = touchCurrentX.value - touchStartX.value;

	if (Math.abs(diffX) > SWIPE_THRESHOLD) {
		if (diffX > 0) {
			// Swipe Right -> Previous
			if (currentNodeIndex.value > 0) {
				ruleStore.prev_config_node();
			}
		} else {
			// Swipe Left -> Next
			if (currentNodeIndex.value < totalNodes.value - 1) {
				ruleStore.next_config_node();
			}
		}
	}
	isSwiping.value = false;
}

// -- Inline Label Editing --
const isEditingLabel = ref(false);
const labelInput = ref("");
const labelInputRef = ref(null);

const canEditLabel = computed(() => {
	// Allow editing if not read-only and rule is not active
	return !ruleStore.is_read_only && !ruleStore.rule_doc?.is_active;
});

function startEditingLabel() {
	if (!canEditLabel.value) return;
	labelInput.value =
		draftNode.value.data?.action_label || draftNode.value.label || __("New Action");
	isEditingLabel.value = true;
	// Auto-focus after render
	setTimeout(() => {
		labelInputRef.value?.focus();
		labelInputRef.value?.select();
	}, 50);
}

function saveLabel() {
	if (!isEditingLabel.value) return;
	if (draftNode.value?.data) {
		const oldLabel = draftNode.value.data.action_label;
		if (oldLabel !== labelInput.value) {
			draftNode.value.data.action_label = labelInput.value;
			ruleStore.mark_dirty();
		}
	}
	isEditingLabel.value = false;
}

watch(
	() => props.modelValue,
	(isOpen) => {
		if (isOpen) {
			collapseInputPanel.value = false;
			collapseOutputPanel.value = false;
			activateCompactTab("config");
		}
	}
);

watch(
	() => uiStore.selected_id,
	() => {
		collapseInputPanel.value = false;
		collapseOutputPanel.value = false;
		activateCompactTab("config");
	}
);

const contract = computed(() => {
	const type = draftNode.value?.data?.action_type || draftNode.value?.type;
	return type ? getContract(type) : null;
});
const actionPresentation = computed(() => {
	const type = draftNode.value?.data?.action_type || draftNode.value?.type;
	return getActionPresentation(type);
});

const totalNodes = computed(() => graphStore.nodes.length);
const currentNodeIndex = computed(() => {
	if (!uiStore.selected_id) return -1;
	return graphStore.nodes.findIndex((n) => n.id === uiStore.selected_id);
});

const transitionName = ref("slide-right");

watch(currentNodeIndex, (newIdx, oldIdx) => {
	if (oldIdx === -1) return;
	transitionName.value = newIdx > oldIdx ? "slide-left" : "slide-right";
});

const title = computed(() => {
	if (!draftNode.value) return __("Rule Configuration");
	let baseTitle =
		draftNode.value.data?.action_label || draftNode.value.label || __("Rule Configuration");
	let suffix = uiStore.config_modal_mode === "logic" ? ` [${__("Logic")}]` : "";
	return baseTitle + suffix;
});

function on_update_action_field(payload, maybeValue) {
	if (!draftNode.value?.data) return;
	let fieldname = null;
	let value = null;
	let scope = null;
	if (typeof payload === "string") {
		fieldname = payload;
		value = maybeValue;
	} else if (payload && typeof payload === "object") {
		fieldname = payload.fieldname;
		value = payload.value;
		scope = payload.scope;
	}
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

function markCompactTabRendered(tabKey) {
	if (!tabKey) return;
	if (!renderedCompactTabs.value.has(tabKey)) {
		renderedCompactTabs.value.add(tabKey);
	}
}

function isCompactTabRendered(tabKey) {
	return renderedCompactTabs.value.has(tabKey);
}

function panelRefByKey(tabKey) {
	if (tabKey === "input") return compactInputRef.value;
	if (tabKey === "config") return compactConfigRef.value;
	if (tabKey === "output") return compactOutputRef.value;
	return null;
}

function rememberCompactScroll(tabKey, event) {
	rememberScroll(tabKey, event?.target?.scrollTop || 0);
}

function activateCompactTab(tabKey) {
	const prevTab = activeCompactTab.value;
	const prevPanel = panelRefByKey(prevTab);
	if (prevPanel) {
		rememberScroll(prevTab, prevPanel.scrollTop || 0);
	}

	markCompactTabRendered(tabKey);
	setActiveTab(tabKey);

	nextTick(() => {
		const panel = panelRefByKey(tabKey);
		if (panel) {
			panel.scrollTop = getRememberedScroll(tabKey);
		}
	});
}

function onCompactTabKeydown(event) {
	if (!isCompactLayout.value) return;
	const currentIndex = compactTabs.findIndex((t) => t.key === activeCompactTab.value);
	if (currentIndex < 0) return;
	if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
	event.preventDefault();

	if (event.key === "Home") {
		activateCompactTab(compactTabs[0].key);
		return;
	}
	if (event.key === "End") {
		activateCompactTab(compactTabs[compactTabs.length - 1].key);
		return;
	}
	const dir = event.key === "ArrowRight" ? 1 : -1;
	const nextIndex = (currentIndex + dir + compactTabs.length) % compactTabs.length;
	activateCompactTab(compactTabs[nextIndex].key);
}

// -- Keyboard Shortcuts --
function handleKeydown(e) {
	if (!props.modelValue) return;

	// 1. Capture ESC key to close modal
	if (e.key === "Escape") {
		cancel();
		e.preventDefault();
		e.stopPropagation();
		return;
	}

	// 2. Capture Ctrl+S to save (takes precedence even when inputs are focused)
	if ((e.ctrlKey || e.metaKey) && e.key === "s") {
		if (!ruleStore.is_read_only) {
			save();
			e.preventDefault();
			e.stopPropagation();
			return;
		}
	}

	// Don't trigger other shortcuts if typing in an input
	if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) || e.target.isContentEditable) {
		return;
	}

	// Ctrl+Up/Left to previous node
	if ((e.ctrlKey || e.metaKey) && (e.key === "ArrowUp" || e.key === "ArrowLeft")) {
		if (currentNodeIndex.value > 0) {
			ruleStore.prev_config_node();
			e.preventDefault();
			e.stopPropagation();
		}
	}

	// Ctrl+Down/Right to next node
	if ((e.ctrlKey || e.metaKey) && (e.key === "ArrowDown" || e.key === "ArrowRight")) {
		if (currentNodeIndex.value < totalNodes.value - 1) {
			ruleStore.next_config_node();
			e.preventDefault();
			e.stopPropagation();
		}
	}

	// Alt+1: Variables
	if (e.altKey && e.key === "1") {
		e.preventDefault();
		showContextSidebar.value = true;
		nextTick(() => {
			panelRefs.input.value?.focusSearch();
		});
	}

	// Alt+2: Configuration
	if (e.altKey && e.key === "2") {
		e.preventDefault();
		panelRefs.config.value?.focusFirst();
	}

	// Alt+3: Settings Bar
	if (e.altKey && e.key === "3") {
		e.preventDefault();
		showSettingsBar.value = !showSettingsBar.value;
	}
}

onMounted(() => {
	window.addEventListener("keydown", handleKeydown);
	window.addEventListener("resize", updateViewportWidth);
	updateViewportWidth();
});

onUnmounted(() => {
	window.removeEventListener("keydown", handleKeydown);
	window.removeEventListener("resize", updateViewportWidth);
	closeOverflow();
});
</script>

<style scoped>
.config-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: color-mix(in srgb, var(--fxr-bg-page, #ffffff) 34%, rgba(15, 23, 42, 0.6));
	backdrop-filter: blur(10px);
	z-index: 1040;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 12px;
}

.config-modal-container {
	background: var(--fxr-surface, #fff);
	width: 100%;
	height: 100%;
	max-width: 1800px;
	border-radius: 20px;
	box-shadow: var(--fxr-shadow-lg, 0 22px 48px rgba(15, 23, 42, 0.12));
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid var(--fxr-border-subtle, var(--border-color));
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.config-modal-header {
	height: 60px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 24px;
	border-bottom: 1px solid var(--fxr-border-subtle, var(--border-color));
	background: var(--fxr-surface, #fff);
}

.header-left {
	display: flex;
	align-items: center;
	gap: 16px;
	min-width: 300px;
}

.header-icon {
	width: 36px;
	height: 36px;
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.header-icon i {
	font-size: 16px;
}

.header-titles {
	display: flex;
	flex-direction: column;
}

.title-wrapper {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 8px;
}

.title-input {
	border: 1px solid var(--fxr-accent, var(--primary));
	border-radius: 10px;
	padding: 4px 8px;
	font-size: 18px;
	font-weight: 700;
	color: var(--fxr-text-strong, var(--text-color));
	width: 100%;
	min-width: 200px;
	outline: none;
	background: var(--fxr-surface, #fff);
}

.header-titles h3.editable {
	cursor: pointer;
	padding: 2px 4px;
	border-radius: 4px;
	transition: background 0.2s;
}

.header-titles h3.editable:hover {
	background: var(--fxr-surface-2, var(--control-bg));
}

.header-titles h3 {
	margin: 0;
	font-size: 18px;
	font-weight: 700;
	color: var(--fxr-text-strong, var(--text-color));
}

.dirty-badge {
	display: flex;
	align-items: center;
	gap: 6px;
	background: var(--fxr-warning-soft, #fffbeb);
	color: var(--orange-700, #d97706);
	padding: 4px 10px;
	border-radius: 20px;
	font-size: 11px;
	font-weight: 700;
	border: 1px solid color-mix(in srgb, var(--orange-400, #f59e0b) 28%, white);
	text-transform: uppercase;
	letter-spacing: 0.5px;
}

.dirty-badge i {
	font-size: 6px;
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
	flex-wrap: wrap;
	align-items: center;
	background: var(--fxr-surface-2, var(--control-bg));
	padding: 2px;
	border-radius: 10px;
	gap: 2px;
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
	color: var(--fxr-text-soft, var(--text-muted));
	font-size: 12px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
	height: 32px;
}

.toolbar-btn:hover:not(:disabled) {
	background: var(--fxr-surface, #fff);
	color: var(--fxr-text-strong, var(--text-color));
	box-shadow: var(--fxr-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.04));
}

.toolbar-btn.active {
	background: var(--fxr-accent, var(--primary));
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
	background: var(--fxr-danger-soft, #fee2e2);
	color: var(--red-600, #ef4444);
}

.toolbar-btn.save-action {
	background: var(--fxr-text-strong, #1e293b);
	color: #fff;
	padding: 0 16px;
}

.toolbar-btn.save-action:hover {
	background: color-mix(in srgb, var(--fxr-text-strong, #1e293b) 84%, black);
	color: #fff;
	box-shadow: var(--fxr-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.04));
}

.toolbar-status {
	display: flex;
	align-items: center;
	padding: 0 8px;
	font-size: 11px;
	font-weight: 800;
	color: var(--fxr-text-soft, var(--text-muted));
	user-select: none;
}

.toolbar-status .total {
	opacity: 0.4;
	margin-left: 4px;
}

.toolbar-status.mobile {
	padding: 0 12px;
	background: var(--fxr-surface, #fff);
	border-radius: 6px;
	height: 28px;
	box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
}

.toolbar-divider {
	width: 1px;
	height: 16px;
	background: var(--fxr-border-subtle, var(--border-color));
	margin: 0 4px;
}

.config-modal-body {
	flex: 1;
	overflow: hidden;
	display: flex;
	position: relative;
	background: color-mix(in srgb, var(--fxr-bg-page, #fff) 92%, var(--fxr-surface-2, #f3f5f7));
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
	border-right: 1px solid var(--fxr-border-subtle, var(--border-color));
	background: var(--fxr-surface, #fff);
	display: flex;
	flex-direction: column;
	overflow-y: auto;
}

.config-main-area {
	flex: 1;
	display: flex;
	overflow: hidden;
}

.config-scroll-container {
	flex: 1;
	overflow: hidden;
	background: color-mix(in srgb, var(--fxr-bg-page, #fff) 92%, var(--fxr-surface-2, #f3f5f7));
	padding: 4px;
	height: 100%;
}

.config-content-wrapper {
	max-width: 1600px;
	margin: 0 auto;
	display: flex;
	flex-direction: column;
	gap: 4px;
	height: 100%;
}

.integrated-settings-bar {
	background: var(--fxr-surface, #fff);
	border-radius: 12px;
	padding: 12px;
	border: 1px solid var(--fxr-border-subtle, var(--border-color));
	max-height: 250px;
	overflow-y: auto;
}

.action-core-layout {
	display: grid;
	grid-template-columns: minmax(220px, 25%) minmax(0, 75%);
	gap: 4px;
	align-items: start;
	height: 100%;
	flex: 1;
	min-height: 0;
}

.core-setup-panel,
.core-config-panel {
	background: var(--fxr-surface, #fff);
	border-radius: 16px;
	border: 1px solid var(--fxr-border-subtle, var(--border-color));
	overflow: hidden;
	position: relative;
	height: 100%;
}

.sidebar-mutation {
	width: 20%;
	min-width: 220px;
	max-width: 380px;
	border-left: 1px solid var(--fxr-border-subtle, var(--border-color));
	background: var(--fxr-surface, #fff);
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
	border: 1px solid var(--fxr-border-subtle, var(--border-color));
	background: var(--fxr-surface, #fff);
	color: var(--fxr-text-soft, var(--text-muted));
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.2s ease;
}

.panel-collapse-btn:hover {
	color: var(--fxr-text-strong, var(--text-color));
	border-color: var(--fxr-border-strong, #94a3b8);
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
	background: var(--fxr-surface-2, var(--control-bg));
	border-color: var(--fxr-border-subtle, var(--border-color));
	z-index: 8;
}

.sidebar-mutation.collapsed .panel-collapse-btn.right {
	left: 50%;
	transform: translateX(-50%);
	background: var(--fxr-surface-2, var(--control-bg));
	border-color: var(--fxr-border-subtle, var(--border-color));
}

.compact-config-layout {
	display: flex;
	flex-direction: column;
	height: 100%;
	width: 100%;
	padding: 8px;
	gap: 8px;
}

.compact-tabs {
	display: flex;
	gap: 6px;
	background: var(--fxr-surface-2, #eef2f7);
	padding: 4px;
	border-radius: 10px;
}

.compact-tab-btn {
	flex: 1;
	height: 34px;
	border: none;
	border-radius: 8px;
	background: transparent;
	color: var(--fxr-text-soft, #64748b);
	font-size: 12px;
	font-weight: 700;
	cursor: pointer;
	transition: all 0.2s ease;
}

.compact-tab-btn:hover {
	background: var(--fxr-surface, #ffffff);
	color: var(--fxr-text-strong, #334155);
}

.compact-tab-btn.active {
	background: var(--fxr-surface, #ffffff);
	color: var(--fxr-text-strong, #1e293b);
	box-shadow: var(--fxr-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.12));
}

.compact-tab-content {
	flex: 1;
	min-height: 0;
	position: relative;
}

.compact-panel-shell {
	height: 100%;
	overflow: auto;
	background: var(--fxr-surface, #ffffff);
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: 14px;
	padding: 8px;
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
	border-left: 1px solid var(--fxr-border-subtle, #e2e8f0);
	background: var(--fxr-surface, #fff);
	position: absolute;
	right: 0;
	top: 0;
	height: 100%;
	z-index: 10;
	box-shadow: -10px 0 30px rgba(15, 23, 42, 0.05);
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

.config-transition-wrapper {
	width: 100%;
	height: 100%;
	display: flex;
}

/* Slide Transitions */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
	transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
}

.slide-left-enter-from {
	opacity: 0;
	transform: translateX(100%);
}
.slide-left-leave-to {
	opacity: 0;
	transform: translateX(-100%);
}

.slide-right-enter-from {
	opacity: 0;
	transform: translateX(-100%);
}
.slide-right-leave-to {
	opacity: 0;
	transform: translateX(100%);
}

.fxr-overflow-dropdown {
	background: var(--fxr-surface, #fff);
	border-radius: 12px;
	box-shadow: var(--fxr-shadow-lg, 0 22px 48px rgba(15, 23, 42, 0.12));
	border: 1px solid var(--fxr-border-subtle, var(--border-color));
	overflow: hidden;
	animation: dropdown-slide 0.2s cubic-bezier(0, 0, 0.2, 1);
}

.overflow-menu-items {
	padding: 8px;
}

.menu-section {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.section-label {
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-text-faint, var(--text-muted));
	text-transform: uppercase;
	letter-spacing: 0.05em;
	padding: 8px 12px 4px;
}

.menu-item {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 10px 12px;
	border-radius: 8px;
	border: none;
	background: transparent;
	color: var(--fxr-text-soft, var(--text-muted));
	font-size: 13px;
	font-weight: 500;
	width: 100%;
	text-align: left;
	cursor: pointer;
	transition: all 0.2s;
}

.menu-item i {
	width: 16px;
	text-align: center;
	color: var(--fxr-text-soft, var(--text-muted));
}

.menu-item:hover:not(:disabled) {
	background: var(--fxr-surface-2, var(--control-bg));
	color: var(--fxr-text-strong, var(--text-color));
}

.menu-item.active {
	background: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, var(--primary));
}

.menu-item.active i {
	color: var(--fxr-accent, var(--primary));
}

.menu-item:disabled {
	opacity: 0.4;
	cursor: not-allowed;
}

.menu-divider {
	height: 1px;
	background: var(--fxr-border-subtle, var(--border-color));
	margin: 8px 4px;
}

@keyframes dropdown-slide {
	from {
		opacity: 0;
		transform: translateY(-8px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

@media (max-width: 767px) {
	.config-modal-overlay {
		padding: 0;
	}

	.config-modal-container {
		border-radius: 0;
		height: 100vh;
	}

	.config-modal-header {
		padding: 0 12px;
		height: auto;
		min-height: 54px;
		padding-top: 8px;
		padding-bottom: 8px;
		flex-wrap: wrap;
		gap: 8px;
	}

	.header-left {
		gap: 8px;
		min-width: 0;
		flex: 1;
	}

	.header-icon {
		width: 30px;
		height: 30px;
		border-radius: 8px;
		flex-shrink: 0;
	}

	.header-titles {
		min-width: 0;
	}

	.header-titles h3 {
		font-size: 15px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 180px;
	}

	.modal-breadcrumb {
		display: none;
	}

	.header-toolbar {
		padding: 0;
		background: transparent;
		gap: 4px;
		flex-wrap: wrap;
		justify-content: flex-end;
	}

	.toolbar-btn {
		padding: 0 10px;
		height: 44px; /* Increased for touch target */
		min-width: 44px;
		justify-content: center;
		border-radius: 8px;
	}

	.toolbar-btn.save-action {
		padding: 0;
		width: 44px;
	}

	.toolbar-btn.close {
		width: 44px;
	}

	.dirty-badge {
		padding: 4px 8px;
		gap: 4px;
	}

	.dirty-badge span {
		font-size: 9px;
	}

	.toolbar-divider {
		margin: 0 2px;
		height: 12px;
	}

	.compact-config-layout {
		padding: 4px;
		gap: 4px;
	}

	.compact-tabs {
		padding: 3px;
		border-radius: 8px;
	}

	.compact-tab-btn {
		height: 44px; /* Increased for touch target */
		font-size: 12px;
		flex: 1;
	}

	.compact-panel-shell {
		border-radius: 10px;
		padding: 12px 8px;
	}
}

@media (max-width: 1199px) {
	.header-left {
		min-width: 0;
	}

	.header-toolbar {
		flex-wrap: wrap;
	}

	.toolbar-btn span {
		display: none;
	}

	.conditions-view {
		padding: 16px;
	}
}
</style>
