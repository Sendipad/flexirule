<script setup>
/**
 * MultiSelectList - Consolidated component for multi-selection.
 * Consolidates MultiCheckControl and MultiSelectListControl functionalities.
 * Features:
 * - Static & Dynamic (Link-based) data sources.
 * - Search, keyboard navigation, and checkboxes.
 * - Multi-column dropdown layout.
 * - Multiple display modes for selected values (Badges, List, Numbered, Multi-column).
 */
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from "vue";

const props = defineProps({
	modelValue: { type: [Array, String], default: () => [] },
	df: { type: Object, default: () => ({}) },
	options: { type: Array, default: null }, // Static override
	get_data: { type: Function, default: null }, // Custom data fetcher
	columns: { type: Number, default: 1 }, // Dropdown columns
	displayMode: { type: String, default: "badges" }, // 'badges', 'list', 'columns', 'numbered'
	read_only: { type: Boolean, default: false },
	hideLabel: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "change"]);

const query = ref("");
const loading = ref(false);
const isDropdownOpen = ref(false);
const activeIndex = ref(-1);
const fetchedOptions = ref([]);

const wrapperRef = ref(null);
const searchInputRef = ref(null);
const dropdownRef = ref(null);
const dropdownStyle = ref({});

// --- Value Normalization ---
const selectedValues = computed(() => {
	const val = props.modelValue;
	if (Array.isArray(val)) return val.map((v) => String(v));
	if (!val) return [];
	if (typeof val === "string") {
		return val
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
	}
	return [String(val)];
});

// --- Option Normalization ---
const normalizedOptions = computed(() => {
	let source = props.options || props.df.options || fetchedOptions.value || [];

	if (typeof source === "string") {
		source = source
			.split("\n")
			.map((o) => o.trim())
			.filter(Boolean);
	}

	if (!Array.isArray(source)) return [];

	return source.map((opt, idx) => {
		if (typeof opt === "string") {
			return { value: opt, label: __(opt) };
		}
		if (Array.isArray(opt)) {
			return { value: opt[0], label: __(opt[1] || opt[0]), description: opt[2] };
		}
		if (typeof opt === "object") {
			const val = opt.value ?? opt.fieldname ?? opt.name ?? `opt_${idx}`;
			return {
				value: String(val),
				label: __(opt.label ?? val),
				description: opt.description,
				icon: opt.icon,
			};
		}
		return opt;
	});
});

const filteredOptions = computed(() => {
	if (!query.value) return normalizedOptions.value;
	const q = query.value.toLowerCase();
	return normalizedOptions.value.filter(
		(opt) =>
			opt.label.toLowerCase().includes(q) ||
			(opt.description || "").toLowerCase().includes(q) ||
			opt.value.toLowerCase().includes(q)
	);
});

// --- Data Fetching ---
async function fetchOptions() {
	if (!props.get_data && props.df.fieldtype !== "Link") return;

	loading.value = true;
	try {
		let results = [];
		if (props.get_data) {
			results = await props.get_data(query.value);
		} else if (props.df.fieldtype === "Link" && props.df.options) {
			const resp = await frappe.call({
				method: "frappe.desk.search.search_link",
				args: {
					txt: query.value,
					doctype: props.df.options,
					filters: props.df.filters || {},
				},
			});
			results = resp.message || [];
		}
		fetchedOptions.value = results;
	} catch (e) {
		console.error("MultiSelectList fetch failed", e);
	} finally {
		loading.value = false;
	}
}

// --- Interaction Logic ---
function toggleDropdown() {
	if (props.read_only) return;
	isDropdownOpen.value = !isDropdownOpen.value;
	if (isDropdownOpen.value) {
		query.value = "";
		activeIndex.value = -1;
		updateDropdownPosition();
		nextTick(() => searchInputRef.value?.focus());
		if (props.df.fieldtype === "Link" || props.get_data) {
			fetchOptions();
		}
	}
}

function updateDropdownPosition() {
	if (!wrapperRef.value) return;
	const rect = wrapperRef.value.getBoundingClientRect();
	const windowHeight = window.innerHeight;
	const spaceBelow = windowHeight - rect.bottom;
	const dropdownHeight = 350;

	let top = rect.bottom + 4;
	if (spaceBelow < dropdownHeight && rect.top > dropdownHeight) {
		top = rect.top - dropdownHeight - 4;
	}

	dropdownStyle.value = {
		position: "fixed",
		top: `${top}px`,
		left: `${rect.left}px`,
		width: `${Math.max(rect.width, 300)}px`,
		zIndex: 2100,
	};
}

function selectOption(value) {
	if (props.read_only) return;
	const current = [...selectedValues.value];
	const idx = current.indexOf(String(value));

	if (idx > -1) {
		current.splice(idx, 1);
	} else {
		// Preserving order of selection as requested
		current.push(String(value));
	}

	emit("update:modelValue", current);
	emit("change", current);
}

function removeValue(value) {
	if (props.read_only) return;
	const current = selectedValues.value.filter((v) => v !== String(value));
	emit("update:modelValue", current);
}

function selectAll() {
	if (props.read_only) return;
	const all = filteredOptions.value.map((o) => o.value);
	// Merge with existing to preserve order of old ones, but add new visible ones
	const next = [...new Set([...selectedValues.value, ...all])];
	emit("update:modelValue", next);
}

function unselectAll() {
	if (props.read_only) return;
	// Only unselect visible filtered options
	const visibleValues = new Set(filteredOptions.value.map((o) => o.value));
	const next = selectedValues.value.filter((v) => !visibleValues.has(v));
	emit("update:modelValue", next);
}

function onKeydown(e) {
	if (e.key === "ArrowDown") {
		e.preventDefault();
		activeIndex.value = Math.min(activeIndex.value + 1, filteredOptions.value.length - 1);
		scrollToActive();
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		activeIndex.value = Math.max(activeIndex.value - 1, 0);
		scrollToActive();
	} else if (e.key === "Enter") {
		e.preventDefault();
		if (activeIndex.value > -1) {
			selectOption(filteredOptions.value[activeIndex.value].value);
		}
	} else if (e.key === "Escape") {
		isDropdownOpen.value = false;
	}
}

function scrollToActive() {
	nextTick(() => {
		const activeEl = dropdownRef.value?.querySelector(".is-active");
		if (activeEl) {
			activeEl.scrollIntoView({ block: "nearest" });
		}
	});
}

function handleClickOutside(e) {
	if (isDropdownOpen.value && !wrapperRef.value?.contains(e.target) && !e.target.closest(".fr-dropdown")) {
		isDropdownOpen.value = false;
	}
}

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
});

const debouncedFetch = flexirule.utils.debounce(fetchOptions, 300);
watch(query, () => {
	if (props.df.fieldtype === "Link" || props.get_data) {
		debouncedFetch();
	}
});

const selectedOptionsObjects = computed(() => {
	const allOpts = normalizedOptions.value;
	return selectedValues.value.map((v) => {
		return allOpts.find((o) => o.value === v) || { value: v, label: v };
	});
});
</script>

<template>
	<div class="fr-control multi-select-list" :class="{ 'no-label': hideLabel }" ref="wrapperRef">
		<div v-if="df.label && !hideLabel" class="fr-label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Display Mode: Badges (Input Trigger) -->
		<div
			v-if="displayMode === 'badges'"
			class="multi-select-trigger"
			:class="{ 'is-active': isDropdownOpen, disabled: read_only }"
			@click="toggleDropdown"
		>
			<div class="selected-badges">
				<div v-for="opt in selectedOptionsObjects" :key="opt.value" class="selected-badge">
					<span>{{ opt.label }}</span>
					<i
						v-if="!read_only"
						class="fa fa-times remove-icon"
						@click.stop="removeValue(opt.value)"
					></i>
				</div>
				<span v-if="!selectedValues.length" class="placeholder-text">
					{{ placeholder || df.placeholder || __("Select options...") }}
				</span>
			</div>
			<i class="fa fa-chevron-down trigger-icon"></i>
		</div>

		<!-- Display Mode: List / Numbered / Columns -->
		<div v-else class="display-mode-container">
			<div class="display-header mb-2" v-if="!read_only">
				<button class="btn btn-xs btn-primary-light" @click="toggleDropdown">
					<i class="fa fa-plus mr-1"></i> {{ __("Add Selection") }}
				</button>
			</div>

			<div
				class="selected-list"
				:class="[
					`mode-${displayMode}`,
					{ 'columns-layout': displayMode === 'columns' }
				]"
			>
				<component :is="displayMode === 'numbered' ? 'ol' : 'div'" class="list-inner">
					<component
						:is="displayMode === 'numbered' ? 'li' : 'div'"
						v-for="(opt, idx) in selectedOptionsObjects"
						:key="opt.value"
						class="list-item"
					>
						<span class="item-label"
							><span v-if="displayMode === 'numbered'" class="mr-1">{{ idx + 1 }}.</span>
							{{ opt.label }}</span
						>
						<button
							v-if="!read_only"
							class="btn btn-xs btn-link text-danger p-0"
							@click="removeValue(opt.value)"
						>
							<i class="fa fa-trash-o"></i>
						</button>
					</component>
				</component>
				<div v-if="!selectedValues.length" class="text-muted small italic p-2">
					{{ __("No selections made") }}
				</div>
			</div>
		</div>

		<!-- Dropdown Popover -->
		<Teleport to="body">
			<transition name="dropdown-fade">
				<div
					v-if="isDropdownOpen"
					class="fr-dropdown multi-select-dropdown"
					:style="dropdownStyle"
					ref="dropdownRef"
				>
					<div class="dropdown-search">
						<i class="fa fa-search text-muted mr-2"></i>
						<input
							ref="searchInputRef"
							v-model="query"
							class="search-input"
							:placeholder="__('Search options...')"
							@keydown="onKeydown"
						/>
					</div>

					<div class="dropdown-actions border-bottom p-2 d-flex gap-3">
						<button class="btn btn-xs btn-link p-0" @click="selectAll">
							{{ __("Select Visible") }}
						</button>
						<button class="btn btn-xs btn-link p-0 text-muted" @click="unselectAll">
							{{ __("Unselect Visible") }}
						</button>
					</div>

					<div class="dropdown-options-container" :style="`grid-template-columns: repeat(${columns}, 1fr)`">
						<div v-if="loading" class="p-3 text-center text-muted">
							<i class="fa fa-spinner fa-spin mr-2"></i> {{ __("Loading...") }}
						</div>
						<div v-else-if="!filteredOptions.length" class="p-3 text-center text-muted">
							{{ __("No options found") }}
						</div>
						<div
							v-for="(opt, idx) in filteredOptions"
							:key="opt.value"
							class="option-item"
							:class="{
								'is-active': idx === activeIndex,
								'is-selected': selectedValues.includes(opt.value)
							}"
							@click="selectOption(opt.value)"
						>
							<input
								type="checkbox"
								:checked="selectedValues.includes(opt.value)"
								class="mr-2"
								@click.stop="selectOption(opt.value)"
							/>
							<div class="option-info">
								<div class="option-label">{{ opt.label }}</div>
								<div v-if="opt.description" class="option-desc">{{ opt.description }}</div>
							</div>
						</div>
					</div>
				</div>
			</transition>
		</Teleport>

		<div v-if="df.description && !hideLabel" class="fr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
.multi-select-list {
	position: relative;
	width: 100%;
}

/* --- Trigger Styles --- */
.multi-select-trigger {
	min-height: var(--fr-input-height);
	background: var(--fr-bg-input);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	padding: 4px 8px;
	display: flex;
	align-items: center;
	cursor: pointer;
	transition: all var(--fr-transition-fast);
}

.multi-select-trigger:hover {
	border-color: var(--fr-border-strong);
}

.multi-select-trigger.is-active {
	border-color: var(--fr-accent);
	box-shadow: 0 0 0 3px var(--fr-accent-light);
}

.selected-badges {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
	flex: 1;
}

.selected-badge {
	background: var(--fr-accent-light);
	color: var(--fr-accent);
	padding: 2px 8px;
	border-radius: var(--fr-radius-sm);
	font-size: var(--fr-text-xs);
	font-weight: var(--fr-weight-semibold);
	display: flex;
	align-items: center;
	gap: 6px;
}

.remove-icon {
	cursor: pointer;
	opacity: 0.7;
}

.remove-icon:hover {
	opacity: 1;
}

.placeholder-text {
	color: var(--fr-text-muted);
	font-size: var(--fr-input-font-size);
}

.trigger-icon {
	color: var(--fr-text-muted);
	font-size: 10px;
	margin-left: 8px;
}

/* --- Display Modes --- */
.selected-list {
	background: var(--fr-bg-card);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	max-height: 300px;
	overflow-y: auto;
}

.list-inner {
	margin: 0;
	padding: var(--fr-space-2);
}

.list-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--fr-space-2) var(--fr-space-4);
	border-radius: var(--fr-radius-md);
}

.list-item:hover {
	background: var(--fr-bg-muted);
}

.columns-layout .list-inner {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
	gap: 8px;
}

/* --- Dropdown Styles --- */
.multi-select-dropdown {
	display: flex;
	flex-direction: column;
	max-height: 400px;
	background: var(--fr-bg-card) !important;
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	box-shadow: var(--fr-shadow-lg);
	overflow: hidden;
}

.dropdown-search {
	padding: 12px;
	display: flex;
	align-items: center;
	border-bottom: 1px solid var(--fr-border);
}

.search-input {
	flex: 1;
	border: none !important;
	background: transparent !important;
	font-size: var(--fr-text-sm);
	outline: none !important;
	box-shadow: none !important;
}

.dropdown-options-container {
	flex: 1;
	overflow-y: auto;
	display: grid;
	padding: 4px;
}

.option-item {
	display: flex;
	align-items: flex-start;
	padding: 8px 12px;
	cursor: pointer;
	border-radius: var(--fr-radius-md);
	transition: background 0.1s;
}

.option-item:hover,
.option-item.is-active {
	background: var(--fr-bg-muted);
}

.option-item.is-selected {
	background: var(--fr-accent-light);
}

.option-label {
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-medium);
	color: var(--fr-text);
}

.option-desc {
	font-size: var(--fr-text-xs);
	color: var(--fr-text-muted);
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
	transition: opacity 0.2s, transform 0.2s;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
	opacity: 0;
	transform: translateY(-8px);
}
</style>
