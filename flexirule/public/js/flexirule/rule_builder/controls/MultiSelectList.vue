<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import { useMetaStore } from "../stores/useMetaStore";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import { useAsyncOptionsSource } from "../composables/useAsyncOptionsSource";

const props = defineProps({
	modelValue: { type: [Array, String], default: () => [] },
	fieldname: String,
	df: { type: Object, default: () => ({}) },
	options: { type: Array, default: null },
	get_data: { type: Function, default: null },
	columns: { type: Number, default: 1 },
	displayMode: { type: String, default: "badges" }, // compact|badges|list|numbered|columns
	read_only: { type: Boolean, default: false },
	hideLabel: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
	documentType: { type: String, default: "" },
	expanded: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	loadingState: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	errorMessage: { type: String, default: "" },
	showValidation: { type: Boolean, default: false },
	compactMaxVisible: { type: Number, default: 2 },
	badgeCollapseAfter: { type: Number, default: 4 },
	allowWrap: { type: Boolean, default: true },
	allowInvertSelection: { type: Boolean, default: true },
	dropdownMinWidth: { type: Number, default: 260 },
	dropdownMaxWidth: { type: Number, default: 760 },
	dropdownMaxHeight: { type: Number, default: 380 },
	virtualThreshold: { type: Number, default: 120 },
	itemHeight: { type: Number, default: 36 },
	map: {
		type: Object,
		default: () => ({
			value: "value",
			label: "label",
			description: "description",
			icon: "icon",
		}),
	},
});

const emit = defineEmits(["update:modelValue", "change"]);
const metaStore = useMetaStore();

const query = ref("");
const activeIndex = ref(-1);
const viewportRef = ref(null);
const searchInputRef = ref(null);
const scrollTop = ref(0);
let typeaheadTimeout = null;
const typeaheadBuffer = ref("");

const {
	triggerRef: wrapperRef,
	dropdownRef,
	isOpen: isDropdownOpen,
	dropdownStyle,
	openDropdown: openFloatingDropdown,
	closeDropdown: closeFloatingDropdown,
	toggleDropdown: toggleFloatingDropdown,
	updatePosition,
	cleanup,
} = useFloatingDropdown({
	minWidth: props.dropdownMinWidth,
	maxWidth: props.dropdownMaxWidth,
	maxHeight: props.dropdownMaxHeight,
	matchTriggerWidth: true,
});

const selectedValues = computed(() => {
	if (Array.isArray(props.modelValue)) return props.modelValue.map((v) => String(v));
	if (!props.modelValue) return [];
	if (typeof props.modelValue === "string") {
		return props.modelValue
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
	}
	return [String(props.modelValue)];
});

const isRemote = computed(() =>
	Boolean(props.get_data || props.documentType || props.df?.fieldtype === "Link")
);

const {
	options: fetchedOptions,
	loading,
	error,
	run: runFetch,
	loadMore,
	hasMore,
	reset,
} = useAsyncOptionsSource(async ({ query: search, start, pageSize }) => {
	if (props.get_data) {
		const rows = await props.get_data(search || "");
		return metaStore.uniqueOptions(metaStore.normalizeLinkRows(rows || []));
	}

	if (props.documentType) {
		const fields = await metaStore.get_doctype_field_options(props.documentType);
		if (!search) return fields || [];
		const q = String(search || "").toLowerCase();
		return (fields || []).filter((row) =>
			String(`${row.label} ${row.description || ""} ${row.value}`)
				.toLowerCase()
				.includes(q)
		);
	}

	if (props.df?.fieldtype === "Link" && props.df?.options) {
		return await metaStore.search_link_options({
			doctype: props.df.options,
			txt: search || "",
			filters: props.df.filters || {},
			start,
			page_length: pageSize,
		});
	}

	return [];
});

const normalizedOptions = computed(() => {
	let source = props.options;

	if (!source) {
		// For remote/link fields, NEVER fallback to df.options string as it represents the target DocType name
		source = isRemote.value ? fetchedOptions.value : props.df.options;
	}

	source = source || [];
	if (typeof source === "string") {
		source = source
			.split("\n")
			.map((o) => o.trim())
			.filter(Boolean);
	}
	if (!Array.isArray(source)) return [];

	const mapped = source.map((opt, idx) => {
		if (!opt) return null;
		if (typeof opt === "string") return { value: opt, label: __(opt), raw: opt };
		if (Array.isArray(opt)) {
			return {
				value: String(opt[0]),
				label: __(opt[1] || opt[0]),
				description: opt[2] || "",
				raw: opt,
			};
		}
		if (typeof opt === "object") {
			// If it's already a normalized object from our store, use its properties
			const value = String(
				opt[props.map.value] ?? opt.value ?? opt.fieldname ?? opt.name ?? `opt_${idx}`
			);
			const label = String(opt[props.map.label] ?? opt.label ?? opt.value ?? "");

			return {
				value,
				label,
				description: String((opt[props.map.description] ?? opt.description) || ""),
				icon: (opt[props.map.icon] ?? opt.icon) || "",
				group: opt.group || "",
				raw: opt,
			};
		}
		return null;
	});

	return metaStore.uniqueOptions((mapped || []).filter(Boolean));
});

const filteredOptions = computed(() => {
	const options = normalizedOptions.value || [];
	if (!query.value || typeof query.value !== "string") return options;
	const q = query.value.toLowerCase();
	return options.filter((opt) =>
		String(`${opt.label} ${opt.description || ""} ${opt.value}`)
			.toLowerCase()
			.includes(q)
	);
});

const selectedOptionObjects = computed(() => {
	const map = new Map(normalizedOptions.value.map((opt) => [String(opt.value), opt]));
	return selectedValues.value.map((value) => {
		const opt = map.get(String(value));
		return opt || { value: String(value), label: String(value) };
	});
});

const compactVisible = computed(() =>
	selectedOptionObjects.value.slice(0, props.compactMaxVisible)
);
const compactHiddenCount = computed(() =>
	Math.max(0, selectedOptionObjects.value.length - compactVisible.value.length)
);

const collapsedBadges = computed(() => {
	if (props.badgeCollapseAfter <= 0) return selectedOptionObjects.value;
	return selectedOptionObjects.value.slice(0, props.badgeCollapseAfter);
});
const collapsedBadgeHiddenCount = computed(() =>
	Math.max(0, selectedOptionObjects.value.length - collapsedBadges.value.length)
);

const isVirtualized = computed(
	() => (filteredOptions.value || []).length >= props.virtualThreshold
);
const viewportHeight = computed(() => Math.min(props.dropdownMaxHeight - 110, 260));
const overscan = 6;
const startIndex = computed(() =>
	isVirtualized.value ? Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - overscan) : 0
);
const endIndex = computed(() => {
	const options = filteredOptions.value || [];
	if (!isVirtualized.value) return options.length;
	const visibleCount = Math.ceil(viewportHeight.value / props.itemHeight) + overscan * 2;
	return Math.min(options.length, startIndex.value + visibleCount);
});
const visibleOptions = computed(() => {
	const options = filteredOptions.value || [];
	return isVirtualized.value ? options.slice(startIndex.value, endIndex.value) : options;
});
const topSpacer = computed(() => (isVirtualized.value ? startIndex.value * props.itemHeight : 0));
const bottomSpacer = computed(() => {
	const options = filteredOptions.value || [];
	return isVirtualized.value ? (options.length - endIndex.value) * props.itemHeight : 0;
});

const canInteract = computed(() => !props.read_only && !props.disabled);
const showExpanded = computed(() => props.expanded);
const isCompactMode = computed(() => props.displayMode === "compact");
const isBadgeMode = computed(() => props.displayMode === "badges");

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	return selectedValues.value.length > 0;
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

function emitValue(nextValues) {
	emit("update:modelValue", nextValues);
	emit("change", nextValues);
}

function validateSelection() {
	if (!canInteract.value) return;

	const options = normalizedOptions.value || [];
	// For remote fields, we only purge when the source entity changes (handled in watchers)
	if (isRemote.value) return;

	// Do not purge if options are empty (could be loading/intermediate)
	if (options.length === 0) return;

	const validValues = new Set(options.map((opt) => String(opt.value)));
	const next = selectedValues.value.filter((val) => validValues.has(val));

	if (next.length !== selectedValues.value.length) {
		emitValue(next);
	}
}

function selectOption(value) {
	if (!canInteract.value) return;
	const key = String(value);
	const next = [...selectedValues.value];
	const idx = next.indexOf(key);
	if (idx > -1) next.splice(idx, 1);
	else next.push(key);
	emitValue(next);
}

function removeValue(value) {
	if (!canInteract.value) return;
	emitValue(selectedValues.value.filter((v) => v !== String(value)));
}

function selectAllVisible() {
	if (!canInteract.value) return;
	const visible = filteredOptions.value.map((opt) => String(opt.value));
	emitValue([...new Set([...selectedValues.value, ...visible])]);
}

function unselectAllVisible() {
	if (!canInteract.value) return;
	const visible = new Set(filteredOptions.value.map((opt) => String(opt.value)));
	emitValue(selectedValues.value.filter((val) => !visible.has(String(val))));
}

function clearAll() {
	if (!canInteract.value) return;
	emitValue([]);
}

function invertSelectionVisible() {
	if (!canInteract.value) return;
	const current = new Set(selectedValues.value.map(String));
	const visible = filteredOptions.value.map((opt) => String(opt.value));
	const next = selectedValues.value.filter((v) => !visible.includes(String(v)));
	for (const value of visible) {
		if (!current.has(value)) next.push(value);
	}
	emitValue([...new Set(next)]);
}

function onViewportScroll(event) {
	scrollTop.value = event?.target?.scrollTop || 0;
	if (!hasMore.value || loading.value || !viewportRef.value) return;
	const el = viewportRef.value;
	const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
	if (nearBottom) loadMore();
}

function scrollToActive() {
	nextTick(() => {
		if (!viewportRef.value || activeIndex.value < 0) return;
		if (isVirtualized.value) {
			const targetTop = activeIndex.value * props.itemHeight;
			const targetBottom = targetTop + props.itemHeight;
			if (targetTop < viewportRef.value.scrollTop) {
				viewportRef.value.scrollTop = targetTop;
			}
			if (targetBottom > viewportRef.value.scrollTop + viewportRef.value.clientHeight) {
				viewportRef.value.scrollTop = targetBottom - viewportRef.value.clientHeight;
			}
			return;
		}
		const activeEl = dropdownRef.value?.querySelector(".option-item.is-active");
		activeEl?.scrollIntoView({ block: "nearest" });
	});
}

function runTypeahead(key) {
	typeaheadBuffer.value += String(key || "").toLowerCase();
	if (typeaheadTimeout) clearTimeout(typeaheadTimeout);
	typeaheadTimeout = setTimeout(() => {
		typeaheadBuffer.value = "";
	}, 420);
	const options = filteredOptions.value || [];
	const idx = options.findIndex((opt) =>
		String(opt.label || "")
			.toLowerCase()
			.startsWith(typeaheadBuffer.value)
	);
	if (idx > -1) {
		activeIndex.value = idx;
		scrollToActive();
	}
}

function onKeydown(event) {
	if (event.key === "ArrowDown") {
		event.preventDefault();
		const options = filteredOptions.value || [];
		if (activeIndex.value < options.length - 1) {
			activeIndex.value++;
			scrollToActive();
		}
		return;
	}
	if (event.key === "ArrowUp") {
		event.preventDefault();
		if (activeIndex.value > 0) {
			activeIndex.value--;
			scrollToActive();
		}
		return;
	}
	if (event.key === "Enter") {
		event.preventDefault();
		const options = filteredOptions.value || [];
		if (activeIndex.value > -1) {
			const selected = options[activeIndex.value];
			if (selected) selectOption(selected.value);
		}
		return;
	}
	if (event.key === "Escape") {
		event.preventDefault();
		event.stopPropagation();
		event.stopImmediatePropagation();
		closeDropdown(true);
		return;
	}
	if (/^[\w\s-]$/.test(event.key) && !event.ctrlKey && !event.metaKey) {
		runTypeahead(event.key);
	}
}

async function fetchOptions(value = "") {
	if (!isRemote.value) return;
	await runFetch(value || "");
	nextTick(() => updatePosition());
}

function openDropdown() {
	if (!canInteract.value || showExpanded.value) return;
	openFloatingDropdown();
	query.value = "";
	activeIndex.value = -1;
	nextTick(() => {
		searchInputRef.value?.focus();
		updatePosition();
	});
	fetchOptions("");
}

function closeDropdown(restoreFocus = false) {
	const active = document.activeElement;
	const wasInsideDropdown = dropdownRef.value && dropdownRef.value.contains(active);
	closeFloatingDropdown();

	if (restoreFocus || wasInsideDropdown) {
		nextTick(() => {
			if (wrapperRef.value) {
				const trigger = wrapperRef.value.querySelector(".multi-select-trigger");
				if (trigger) trigger.focus();
			}
		});
	}
}

function toggleDropdown() {
	if (!canInteract.value || showExpanded.value) return;
	toggleFloatingDropdown();
	if (isDropdownOpen.value) {
		openDropdown();
	}
}

function displaySummaryText() {
	if (!selectedOptionObjects.value.length) {
		return props.placeholder || props.df.placeholder || __("Select options...");
	}
	return selectedOptionObjects.value.map((opt) => opt.label).join(", ");
}

function handleClickOutside(event) {
	if (!isDropdownOpen.value) return;
	if (wrapperRef.value?.contains(event.target)) return;
	if (dropdownRef.value?.contains(event.target)) return;
	closeDropdown(false);
}

const debouncedFetch = flexirule.utils.debounce(fetchOptions, 220);
watch(query, (value) => {
	activeIndex.value = -1;
	if (isRemote.value) debouncedFetch(value || "");
});

watch(
	() => props.options,
	(newVal) => {
		if (!canInteract.value) return;
		if (Array.isArray(newVal) && newVal.length > 0) {
			validateSelection();
		} else if (
			(newVal === null || (Array.isArray(newVal) && newVal.length === 0)) &&
			!props.loadingState
		) {
			clearAll();
		}
	},
	{ deep: true }
);

watch(
	() => props.documentType,
	() => {
		reset();
		if (canInteract.value) clearAll();
		if (showExpanded.value || isDropdownOpen.value) fetchOptions(query.value || "");
	}
);

watch(
	() => props.df?.options,
	() => {
		reset();
		if (!canInteract.value) return;
		if (isRemote.value) {
			clearAll();
		} else {
			validateSelection();
		}
	}
);

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
	if (showExpanded.value) fetchOptions("");
	if (canInteract.value && !isRemote.value) {
		validateSelection();
	}
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	cleanup();
	if (typeaheadTimeout) clearTimeout(typeaheadTimeout);
});
</script>

<template>
	<div
		class="fxr-control multi-select-list"
		:class="{ 'no-label': hideLabel }"
		ref="wrapperRef"
		v-field-inspect="{ name: df?.fieldname || fieldname, label: df?.label }"
	>
		<div v-if="df.label && !hideLabel" class="fxr-label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>

		<div
			class="multi-select-trigger"
			:class="{
				'is-active': isDropdownOpen,
				disabled: !canInteract,
				invalid: invalid || (showValidation && !isValid),
				compact: isCompactMode,
			}"
			tabindex="0"
			@click="toggleDropdown"
			@keydown.enter.prevent="toggleDropdown"
			@keydown.space.prevent="toggleDropdown"
		>
			<template v-if="isCompactMode">
				<div class="compact-content" :title="displaySummaryText()">
					<span v-for="opt in compactVisible" :key="opt.value" class="compact-pill">
						{{ opt.label }}
					</span>
					<span v-if="compactHiddenCount" class="compact-pill muted">{{
						__("+{0} more", [compactHiddenCount])
					}}</span>
					<span v-if="!selectedOptionObjects.length" class="placeholder-text">
						{{ props.placeholder || props.df.placeholder || __("Select options...") }}
					</span>
				</div>
			</template>

			<template v-else-if="isBadgeMode">
				<div class="selected-badges" :class="{ 'no-wrap': !allowWrap }">
					<div v-for="opt in collapsedBadges" :key="opt.value" class="selected-badge">
						<span>{{ opt.label }}</span>
						<i
							v-if="canInteract"
							class="fa fa-times remove-icon"
							tabindex="0"
							@click.stop="removeValue(opt.value)"
							@keydown.enter.stop.prevent="removeValue(opt.value)"
							@keydown.space.stop.prevent="removeValue(opt.value)"
						></i>
					</div>
					<span v-if="collapsedBadgeHiddenCount" class="selected-badge collapsed"
						>+{{ collapsedBadgeHiddenCount }}</span
					>
					<span v-if="!selectedValues.length" class="placeholder-text">
						{{ placeholder || df.placeholder || __("Select options...") }}
					</span>
				</div>
			</template>

			<template v-else>
				<div class="mode-summary" :title="displaySummaryText()">
					{{ displaySummaryText() }}
				</div>
			</template>
			<i class="fa fa-chevron-down trigger-icon"></i>
		</div>

		<div
			v-if="!showExpanded && !isCompactMode && !isBadgeMode"
			class="selected-list"
			:class="`mode-${displayMode}`"
		>
			<component :is="displayMode === 'numbered' ? 'ol' : 'div'" class="list-inner">
				<component
					:is="displayMode === 'numbered' ? 'li' : 'div'"
					v-for="(opt, idx) in selectedOptionObjects"
					:key="opt.value"
					class="list-item"
				>
					<span class="item-label">
						<span v-if="displayMode === 'numbered'" class="mr-1">{{ idx + 1 }}.</span>
						{{ opt.label }}
					</span>
					<button
						v-if="canInteract"
						class="btn btn-xs btn-link text-danger p-0"
						@click="removeValue(opt.value)"
					>
						<i class="fa fa-trash-o"></i>
					</button>
				</component>
			</component>
			<div v-if="!selectedOptionObjects.length" class="empty-selection-text">
				{{ __("No selections made") }}
			</div>
		</div>

		<div v-if="showExpanded" class="expanded-options-container">
			<div class="dropdown-search sticky-row">
				<i class="fa fa-search text-muted mr-2"></i>
				<input
					ref="searchInputRef"
					v-model="query"
					class="search-input"
					:placeholder="__('Search options...')"
					@keydown="onKeydown"
				/>
			</div>
			<div class="dropdown-actions sticky-row">
				<button class="action-btn select-all" @click="selectAllVisible">
					{{ __("Select Visible") }}
				</button>
				<button class="action-btn unselect-all" @click="unselectAllVisible">
					{{ __("Unselect Visible") }}
				</button>
				<button class="action-btn clear-all" @click="clearAll">
					{{ __("Clear All") }}
				</button>
				<button
					v-if="allowInvertSelection"
					class="action-btn invert"
					@click="invertSelectionVisible"
				>
					{{ __("Invert") }}
				</button>
			</div>
			<div
				ref="viewportRef"
				class="dropdown-options-container"
				@scroll="onViewportScroll"
				:style="{ '--columns': columns, '--viewport-height': `${viewportHeight}px` }"
			>
				<div v-if="topSpacer" :style="{ height: `${topSpacer}px` }"></div>
				<div
					v-for="(opt, idx) in visibleOptions"
					:key="`${opt.value}-${startIndex + idx}`"
					class="option-item"
					:class="{
						'is-active': startIndex + idx === activeIndex,
						'is-selected': selectedValues.includes(String(opt.value)),
					}"
					:data-value="opt.value"
					:data-label="opt.label"
					@click="selectOption(opt.value)"
				>
					<input
						type="checkbox"
						:checked="selectedValues.includes(String(opt.value))"
						@click.stop="selectOption(opt.value)"
					/>
					<div v-if="opt.icon" class="option-icon">
						<i :class="opt.icon"></i>
					</div>
					<div class="option-info">
						<div class="option-label-row">
							<div class="option-label">{{ opt.label || opt.value }}</div>
							<span
								v-if="opt.raw?.fieldtype || opt.raw?.type"
								class="option-badge"
								:class="
									'type-' +
									String(opt.raw?.fieldtype || opt.raw?.type || '')
										.toLowerCase()
										.replace(' ', '-')
								"
							>
								{{ opt.raw?.fieldtype || opt.raw?.type }}
							</span>
						</div>
						<div v-if="opt.description" class="option-desc">{{ opt.description }}</div>
					</div>
				</div>
				<div v-if="bottomSpacer" :style="{ height: `${bottomSpacer}px` }"></div>
			</div>
		</div>

		<Teleport to="body">
			<transition name="dropdown-fade">
				<div
					v-if="isDropdownOpen && !showExpanded"
					class="fxr-dropdown multi-select-dropdown"
					:style="dropdownStyle"
					ref="dropdownRef"
				>
					<div class="dropdown-search sticky-row">
						<i class="fa fa-search text-muted mr-2"></i>
						<input
							ref="searchInputRef"
							v-model="query"
							class="search-input"
							:placeholder="__('Search options...')"
							@keydown="onKeydown"
						/>
					</div>

					<div class="dropdown-actions sticky-row">
						<button class="action-btn select-all" @click="selectAllVisible">
							{{ __("Select Visible") }}
						</button>
						<button class="action-btn unselect-all" @click="unselectAllVisible">
							{{ __("Unselect Visible") }}
						</button>
						<button class="action-btn clear-all" @click="clearAll">
							{{ __("Clear All") }}
						</button>
						<button
							v-if="allowInvertSelection"
							class="action-btn invert"
							@click="invertSelectionVisible"
						>
							{{ __("Invert") }}
						</button>
					</div>

					<div class="dropdown-state" v-if="loading || loadingState">
						<i class="fa fa-spinner fa-spin mr-2"></i>{{ __("Loading...") }}
					</div>
					<div class="dropdown-state" v-else-if="error || errorMessage">
						{{ error || errorMessage }}
					</div>
					<div class="dropdown-state" v-else-if="!filteredOptions.length">
						{{ __("No options found") }}
					</div>

					<div
						v-else
						ref="viewportRef"
						class="dropdown-options-container"
						@scroll="onViewportScroll"
						:style="{
							'--columns': columns,
							'--viewport-height': `${viewportHeight}px`,
						}"
					>
						<div v-if="topSpacer" :style="{ height: `${topSpacer}px` }"></div>
						<div
							v-for="(opt, idx) in visibleOptions"
							:key="`${opt.value}-${startIndex + idx}`"
							class="option-item"
							:class="{
								'is-active': startIndex + idx === activeIndex,
								'is-selected': selectedValues.includes(String(opt.value)),
							}"
							:data-value="opt.value"
							:data-label="opt.label"
							@click="selectOption(opt.value)"
						>
							<input
								type="checkbox"
								:checked="selectedValues.includes(String(opt.value))"
								@click.stop="selectOption(opt.value)"
							/>
							<div v-if="opt.icon" class="option-icon">
								<i :class="opt.icon"></i>
							</div>
							<div class="option-info">
								<div class="option-label-row">
									<div class="option-label">
										{{ opt.label || opt.value }}
									</div>
									<span
										v-if="opt.raw?.fieldtype || opt.raw?.type"
										class="option-badge"
										:class="
											'type-' +
											String(opt.raw?.fieldtype || opt.raw?.type || '')
												.toLowerCase()
												.replace(' ', '-')
										"
									>
										{{ opt.raw?.fieldtype || opt.raw?.type }}
									</span>
								</div>
								<div v-if="opt.description" class="option-desc">
									{{ opt.description }}
								</div>
							</div>
						</div>
						<div v-if="bottomSpacer" :style="{ height: `${bottomSpacer}px` }"></div>
					</div>
				</div>
			</transition>
		</Teleport>

		<div v-if="(error || errorMessage) && !isDropdownOpen" class="fxr-description text-danger">
			{{ error || errorMessage }}
		</div>
		<div v-if="df.description && !hideLabel" class="fxr-description">
			{{ __(df.description) }}
		</div>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
</template>

<style scoped>
.multi-select-list {
	position: relative;
	width: 100%;
}

.multi-select-trigger {
	min-height: var(--fxr-input-height);
	background-color: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	padding: 4px 8px;
	display: flex;
	align-items: center;
	gap: 8px;
	cursor: pointer;
	transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.multi-select-trigger.invalid {
	border-color: var(--fxr-border-danger);
}

.multi-select-trigger.is-active {
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}

.multi-select-trigger.disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.compact-content,
.mode-summary {
	flex: 1;
	min-width: 0;
	display: flex;
	align-items: center;
	gap: 6px;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
}

.compact-pill {
	max-width: 220px;
	min-width: 60px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	padding: 2px 10px;
	border-radius: var(--fxr-radius-pill);
	background-color: var(--fxr-surface-2);
	border: 1px solid var(--fxr-border-subtle);
	font-size: 11px;
	font-weight: 700;
	color: var(--fxr-text-strong);
}

.compact-pill.muted {
	color: var(--fxr-text-soft);
}

.selected-badges {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	flex: 1;
	min-width: 0;
}

.selected-badges.no-wrap {
	flex-wrap: nowrap;
	overflow: hidden;
	align-items: center;
	height: 100%;
}

.selected-badge {
	background-color: var(--fxr-accent-soft);
	color: var(--fxr-accent);
	padding: 2px 8px;
	border-radius: var(--fxr-radius-sm);
	font-size: 11px;
	font-weight: 600;
	display: inline-flex;
	align-items: center;
	gap: 6px;
	white-space: nowrap;
	flex-shrink: 0;
}

.selected-badge.collapsed {
	background-color: var(--fxr-bg-muted);
	color: var(--fxr-text-soft);
	flex-shrink: 0;
}

.remove-icon {
	cursor: pointer;
	opacity: 0.75;
}

.remove-icon:hover {
	opacity: 1;
}

.placeholder-text {
	color: var(--fxr-text-muted);
	font-size: var(--fxr-input-font-size);
}

.trigger-icon {
	color: var(--fxr-text-muted);
	font-size: 10px;
	margin-left: auto;
	flex-shrink: 0;
}

.multi-select-dropdown,
.expanded-options-container {
	background-color: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
	box-shadow: var(--fxr-shadow-lg);
	overflow: hidden;
}

.expanded-options-container {
	margin-top: 8px;
}

.selected-list {
	margin-top: 8px;
	background-color: var(--fxr-surface);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 10px;
	max-height: 240px;
	overflow: auto;
}

.list-inner {
	margin: 0;
	padding: 6px;
}

.list-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding: 6px 8px;
	border-radius: 8px;
}

.list-item:hover {
	background-color: var(--fxr-bg-hover);
}

.item-label {
	font-size: 13px;
	line-height: 1.3;
	color: var(--fxr-text-strong);
	min-width: 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.mode-columns .list-inner {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
	gap: 6px;
}

.empty-selection-text {
	padding: 10px 12px;
	font-size: 12px;
	color: var(--fxr-text-muted);
}

.sticky-row {
	position: sticky;
	z-index: 2;
	background-color: var(--fxr-surface-elevated);
}

.dropdown-search {
	top: 0;
	padding: 10px 12px;
	display: flex;
	align-items: center;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.dropdown-actions {
	top: 44px;
	padding: 8px 12px;
	display: flex;
	gap: 6px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.action-btn {
	padding: 4px 8px;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	background-color: var(--fxr-bg-card);
	color: var(--fxr-text-soft);
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.15s ease;
	white-space: nowrap;
}

.action-btn:hover {
	background-color: var(--fxr-bg-hover);
	border-color: var(--fxr-border-strong);
	color: var(--fxr-text-strong);
}

.action-btn.select-all {
	color: var(--fxr-accent);
	border-color: var(--fxr-accent-border);
	background-color: var(--fxr-accent-soft);
}

.action-btn.select-all:hover {
	background-color: var(--fxr-accent);
	color: #ffffff;
	border-color: var(--fxr-accent);
}

.action-btn.clear-all {
	color: var(--fxr-text-danger);
}

.action-btn.clear-all:hover {
	background-color: var(--fxr-bg-danger-soft);
	border-color: var(--fxr-border-danger-subtle);
}

.search-input {
	flex: 1;
	border: none;
	background: transparent;
	outline: none;
	font-size: var(--fxr-text-sm);
}

.dropdown-state {
	padding: 18px 12px;
	text-align: center;
	color: var(--fxr-text-muted);
	font-size: 12px;
}

.dropdown-options-container {
	max-height: var(--viewport-height);
	overflow: auto;
	display: grid;
	grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
	gap: 4px;
	padding: 4px;
}

.option-item {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 8px 12px;
	border-radius: 8px;
	cursor: pointer;
	transition: background 0.12s ease;
	min-height: 40px;
}

.option-item:hover,
.option-item.is-active {
	background-color: var(--fxr-bg-hover);
}

.option-item.is-selected {
	background-color: var(--fxr-accent-soft);
}

.option-icon {
	flex-shrink: 0;
	width: 16px;
	height: 16px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--fxr-accent);
	font-size: 12px;
}

.option-info {
	flex: 1;
	min-width: 0;
}

.option-label-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
}

.option-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	line-height: 1.25;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.option-badge {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 4px;
	letter-spacing: 0.05em;
	background-color: var(--fxr-bg-muted);
	color: var(--fxr-text-soft);
	flex-shrink: 0;
}

.option-desc {
	font-size: 11px;
	color: var(--fxr-text-soft);
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
	transition: opacity 0.2s ease, transform 0.2s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
	opacity: 0;
	transform: translateY(-6px) scale(0.99);
}
</style>

<style>
/* Global styles for teleported dropdown content */
.multi-select-dropdown .option-info {
	flex: 1;
	min-width: 0;
}

.multi-select-dropdown .option-label-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
}

.multi-select-dropdown .option-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	line-height: 1.25;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.multi-select-dropdown .option-badge {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 4px;
	letter-spacing: 0.05em;
	background-color: var(--fxr-bg-muted);
	color: var(--fxr-text-soft);
	flex-shrink: 0;
}

.multi-select-dropdown .option-desc {
	font-size: 11px;
	color: var(--fxr-text-soft);
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
