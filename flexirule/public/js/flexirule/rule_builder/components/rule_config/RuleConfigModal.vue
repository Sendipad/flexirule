<template>
	<Teleport to="body">
		<transition name="modal-fade">
			<div
				v-if="modelValue"
				class="config-modal-overlay"
				@click.self="cancel"
				@keydown.tab="handleTab"
			>
				<div class="config-modal-container" ref="modalRef">
					<header
						class="config-modal-header"
						@touchstart="handleTouchStart"
						@touchmove="handleTouchMove"
						@touchend="handleTouchEnd"
					>
						<div class="header-left">
							<div
								v-if="!isMobile || !isEditingLabel"
								class="header-icon"
								:style="{
									background: actionPresentation.background,
									color: actionPresentation.color,
								}"
							>
								<i :class="actionPresentation.icon"></i>
							</div>
							<div class="header-titles">
								<div
									class="title-wrapper"
									:class="{ 'is-editing': isEditingLabel }"
								>
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
										v-if="isDirty && !ruleStore.is_read_only && !isMobile"
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
								<!-- Desktop Controls -->
								<template v-if="!isMobile">
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

								<!-- Action Group: Save, More, Close -->
								<div class="toolbar-group actions">
									<!-- Save (Primary) -->
									<button
										v-if="
											!ruleStore.is_read_only &&
											(!isMobile || (isDirty && !isEditingLabel))
										"
										class="toolbar-btn save-action"
										:disabled="!isDirty"
										@click="save"
										:title="__('Save Changes')"
									>
										<i class="fa fa-save"></i>
										<span class="btn-label" v-if="!isMobile">{{
											__("Save")
										}}</span>
									</button>

									<!-- Overflow Menu (Mobile Only) -->
									<div
										v-if="isMobile && !isEditingLabel"
										class="overflow-menu-wrapper"
									>
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

									<!-- Close -->
									<button
										class="toolbar-btn close-action"
										@click="cancel"
										:title="__('Close')"
									>
										<i class="fa fa-times"></i>
									</button>
								</div>
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
											:showValidation="showValidation"
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
															<ActionSettings
																:node="draftNode"
																:readOnly="ruleStore.is_read_only"
																:showValidation="showValidation"
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
																	:showValidation="showValidation"
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
																	:showValidation="showValidation"
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
														:showValidation="showValidation"
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
															:showValidation="showValidation"
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
															<ActionSettings
																:node="draftNode"
																:readOnly="ruleStore.is_read_only"
																:showValidation="showValidation"
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
															:showValidation="showValidation"
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
															:showValidation="showValidation"
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
import { deepClone, fromCodeString } from "../../utils/serialization.js";
import InputPanel from "./InputPanel.vue";
import ConfigurationPanel from "./ConfigurationPanel.vue";
import OutputPanel from "./OutputPanel.vue";
import ActionSettings from "./ActionSettings.vue";
import ActionFieldProperties from "../ActionFieldProperties.vue";
import ConditionStep from "./types/ConditionStep.vue";
import StartNodeProperties from "../StartNodeProperties.vue";
import { useRuleStore, useGraphStore, useUIStore } from "../../stores";
import { useRuleConfig } from "../../composables/useRuleConfig";
import { useResponsiveConfigLayout } from "../../composables/useResponsiveConfigLayout";
import { useFloatingDropdown } from "../../composables/useFloatingDropdown";
import { useKeyboardRegistry } from "../../composables/useKeyboardRegistry";
import { useFocusTrap } from "../../composables/useFocusTrap";
import { getContract, getActionPresentation } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: Boolean,
	node: Object,
});

const emit = defineEmits(["update:modelValue", "save"]);
const ruleStore = useRuleStore();
const modalRef = ref(null);
const graphStore = useGraphStore();
const uiStore = useUIStore();
// Legacy support
const store = uiStore;

const { draftNode, panelRefs, save, cancel, isDirty, showValidation } = useRuleConfig(props, emit);
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

const { registerShortcut, pushContext, popContext } = useKeyboardRegistry();
const { handleTab: trapTab, trapFocus, untrapFocus } = useFocusTrap();

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
			trapFocus(modalRef.value);
		} else {
			untrapFocus();
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

const totalNodes = computed(() => graphStore.orderedConfigurableNodes.length);
const currentNodeIndex = computed(() => {
	if (!uiStore.selected_id) return -1;
	return graphStore.orderedConfigurableNodes.findIndex((n) => n.id === uiStore.selected_id);
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
			baseConfig = fromCodeString(draftNode.value.data.config) || {};
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
		return;
	}
	draftNode.value.data[fieldname] = value;
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

function handleTab(e) {
	trapTab(e, modalRef.value);
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
const unregisterShortcuts = ref([]);

onMounted(() => {
	window.addEventListener("resize", updateViewportWidth);
	updateViewportWidth();

	pushContext("modal");
	unregisterShortcuts.value = [
		registerShortcut({
			key: "Escape",
			context: "modal",
			priority: 10,
			callback: () => cancel(),
		}),
		registerShortcut({
			key: "s",
			mod: true,
			context: "modal",
			priority: 11,
			callback: () => {
				if (!ruleStore.is_read_only) save();
			},
		}),
		registerShortcut({
			key: "ArrowUp",
			mod: true,
			context: "modal",
			priority: 10,
			callback: () => {
				if (currentNodeIndex.value > 0) ruleStore.prev_config_node();
			},
		}),
		registerShortcut({
			key: "ArrowLeft",
			mod: true,
			context: "modal",
			priority: 10,
			callback: () => {
				if (currentNodeIndex.value > 0) ruleStore.prev_config_node();
			},
		}),
		registerShortcut({
			key: "ArrowDown",
			mod: true,
			context: "modal",
			priority: 10,
			callback: () => {
				if (currentNodeIndex.value < totalNodes.value - 1) ruleStore.next_config_node();
			},
		}),
		registerShortcut({
			key: "ArrowRight",
			mod: true,
			context: "modal",
			priority: 10,
			callback: () => {
				if (currentNodeIndex.value < totalNodes.value - 1) ruleStore.next_config_node();
			},
		}),
		registerShortcut({
			key: "1",
			alt: true,
			context: "modal",
			priority: 10,
			callback: () => {
				showContextSidebar.value = true;
				nextTick(() => panelRefs.input.value?.focusSearch());
			},
		}),
		registerShortcut({
			key: "2",
			alt: true,
			context: "modal",
			priority: 10,
			callback: () => panelRefs.config.value?.focusFirst(),
		}),
		registerShortcut({
			key: "3",
			alt: true,
			context: "modal",
			priority: 10,
			callback: () => (showSettingsBar.value = !showSettingsBar.value),
		}),
	];
});

onUnmounted(() => {
	window.removeEventListener("resize", updateViewportWidth);
	unregisterShortcuts.value.forEach((unreg) => unreg());
	popContext("modal");
	closeOverflow();
});
</script>

<style>
/* Ensure Save button is prominent and visible in all themes */
.toolbar-btn.save-action {
	background: var(--fxr-accent) !important;
	color: #ffffff !important;
	border-color: var(--fxr-accent) !important;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.toolbar-btn.save-action:hover {
	background: var(--fxr-accent) !important;
	filter: brightness(1.1);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.toolbar-btn.save-action:active {
	transform: translateY(1px);
	filter: brightness(0.95);
}

html[data-theme="dark"] .toolbar-btn.save-action {
	background: var(--fxr-accent) !important;
	color: #ffffff !important;
	border-color: var(--fxr-accent) !important;
}
</style>

<style scoped>
.config-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background-color: rgba(0, 0, 0, 0.5);
	backdrop-filter: blur(10px);
	z-index: 1040;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 12px;
}

.config-modal-container {
	background-color: var(--fxr-surface);
	width: 100%;
	height: 100%;
	max-width: 1800px;
	border-radius: 20px;
	box-shadow: var(--fxr-shadow-lg);
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid var(--fxr-border-subtle);
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.config-modal-header {
	height: 60px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 16px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface);
}

.header-left {
	display: flex;
	align-items: center;
	gap: 12px;
	min-width: 0;
	flex: 1;
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
	gap: 8px;
}

.title-input {
	border: 1px solid var(--fxr-accent);
	border-radius: 10px;
	padding: 4px 8px;
	font-size: 18px;
	font-weight: 700;
	color: var(--fxr-text-strong);
	flex: 1;
	min-width: 120px;
	outline: none;
	background: var(--fxr-surface);
}

.header-titles h3.editable {
	cursor: pointer;
	padding: 2px 4px;
	border-radius: 4px;
	transition: background 0.2s;
}

.header-titles h3.editable:hover {
	background: var(--fxr-surface-2);
}

.header-titles h3 {
	margin: 0;
	font-size: 18px;
	font-weight: 700;
	color: var(--fxr-text-strong);
}

.dirty-badge {
	display: flex;
	align-items: center;
	gap: 6px;
	background-color: var(--fxr-warning-soft);
	color: var(--fxr-text-secondary);
	padding: 4px 10px;
	border-radius: 20px;
	font-size: 11px;
	font-weight: 700;
	border: 1px solid var(--fxr-border);
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
	align-items: center;
	background: var(--fxr-surface-2);
	padding: 2px;
	border-radius: 11px;
	gap: 2px;
}

.header-toolbar:empty {
	display: none;
}

.toolbar-group {
	display: flex;
	align-items: center;
	gap: 4px;
}

.toolbar-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	padding: 0 10px;
	border-radius: 10px;
	border: 1px solid transparent;
	background: transparent;
	color: var(--fxr-text-soft);
	font-size: 12px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	height: 32px;
	min-width: 32px;
}

.toolbar-btn:hover:not(:disabled) {
	background: var(--fxr-surface);
	color: var(--fxr-text-strong);
	border-color: var(--fxr-border-subtle);
	box-shadow: var(--fxr-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.04));
}

.toolbar-btn.active {
	background: var(--fxr-accent, var(--primary));
	color: #fff;
	border-color: var(--fxr-accent, var(--primary));
}

.toolbar-btn:disabled {
	opacity: 0.35;
	cursor: not-allowed;
}

.toolbar-btn.close-action {
	background: var(--fxr-bg-muted) !important;
	color: var(--fxr-text-muted) !important;
	border: none !important;
	transition: all 0.2s ease;
}

.toolbar-btn.close-action:hover {
	background: var(--fxr-danger-soft, #fee2e2) !important;
	color: var(--red-600, #ef4444) !important;
	transform: rotate(90deg);
}

.toolbar-btn.save-action {
	background: var(--fxr-accent-soft);
	color: var(--fxr-accent);
	border-color: var(--fxr-accent-border);
}

.toolbar-btn.save-action:hover {
	background: var(--fxr-accent);
	color: #ffffff !important;
	border-color: var(--fxr-accent);
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
	background-color: var(--fxr-bg-card);
	border-radius: 6px;
	height: 28px;
	box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
}

.toolbar-divider {
	width: 1px;
	height: 14px;
	background-color: var(--fxr-border-subtle);
	opacity: 0.6;
	margin: 0 2px;
	flex-shrink: 0;
}

.config-modal-body {
	flex: 1;
	overflow: hidden;
	display: flex;
	position: relative;
	background-color: var(--fxr-bg-page);
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
	border-right: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface);
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
	background-color: var(--fxr-bg-page);
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
	background-color: var(--fxr-surface);
	border-radius: 12px;
	padding: 12px;
	border: 1px solid var(--fxr-border-subtle);
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
	background: var(--fxr-surface);
	border-radius: 16px;
	border: 1px solid var(--fxr-border-subtle);
	overflow: hidden;
	position: relative;
	height: 100%;
}

.sidebar-mutation {
	width: 20%;
	min-width: 220px;
	max-width: 380px;
	border-left: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface);
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
	border: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-bg-card);
	color: var(--fxr-text-soft);
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.2s ease;
}

.panel-collapse-btn:hover {
	color: var(--fxr-text-strong);
	border-color: var(--fxr-border-strong);
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
	background-color: var(--fxr-surface-2);
	border-color: var(--fxr-border-subtle);
	z-index: 8;
}

.sidebar-mutation.collapsed .panel-collapse-btn.right {
	left: 50%;
	transform: translateX(-50%);
	background-color: var(--fxr-surface-2);
	border-color: var(--fxr-border-subtle);
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
	background: var(--fxr-surface-2);
	padding: 4px;
	border-radius: 10px;
}

.compact-tab-btn {
	flex: 1;
	height: 34px;
	border: none;
	border-radius: 8px;
	background: transparent;
	color: var(--fxr-text-soft);
	font-size: 12px;
	font-weight: 700;
	cursor: pointer;
	transition: all 0.2s ease;
}

.compact-tab-btn:hover {
	background: var(--fxr-surface);
	color: var(--fxr-text-strong);
}

.compact-tab-btn.active {
	background: var(--fxr-surface);
	color: var(--fxr-text-strong);
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
	background: var(--fxr-surface);
	border: 1px solid var(--fxr-border-subtle);
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
	border-left: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface);
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
	background: var(--fxr-surface);
	border-radius: 12px;
	box-shadow: var(--fxr-shadow-lg, 0 22px 48px rgba(15, 23, 42, 0.12));
	border: 1px solid var(--fxr-border-subtle);
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
	background: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
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
		padding: 8px 12px;
		height: 48px;
		min-height: 48px;
		flex-wrap: nowrap;
		gap: 8px;
	}

	.header-left {
		gap: 6px;
		min-width: 0;
		flex: 1;
	}

	.header-icon {
		width: 24px;
		height: 24px;
		border-radius: 6px;
		flex-shrink: 0;
	}

	.header-icon i {
		font-size: 12px;
	}

	.header-titles {
		min-width: 0;
		flex: 1;
	}

	.header-titles h3 {
		font-size: 14px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 100%;
		margin: 0;
	}

	.title-wrapper {
		gap: 4px;
	}

	.header-toolbar {
		background: var(--fxr-surface-2);
		border-radius: 10px;
		padding: 2px;
	}

	.modal-breadcrumb {
		display: none;
	}

	.header-toolbar {
		padding: 0;
		background: transparent;
		gap: 4px;
		flex-wrap: nowrap;
		justify-content: flex-end;
	}

	.toolbar-btn {
		padding: 0;
		height: 36px;
		width: 36px;
		min-width: 36px;
		border-radius: 10px;
	}

	.toolbar-btn .btn-label {
		display: none;
	}

	.title-wrapper.is-editing {
		width: 100%;
		flex: 1;
	}

	.title-input {
		font-size: 15px;
		height: 36px;
		border-radius: 8px;
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
