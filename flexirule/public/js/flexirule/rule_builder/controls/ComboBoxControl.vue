<template>
	<div class="fr-control" :class="{ 'no-label': hideLabel }">
		<div v-if="df?.label && !hideLabel" class="fr-label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>

		<div class="combobox-container" ref="wrapperRef">
			<div
				class="combobox-wrapper"
				:class="{ 'is-focused': isDropdownOpen, 'is-button-mode': trigger === 'button' }"
			>
				<div class="combobox-input-group">
					<!-- Prefix Slot / Selected Icon -->
					<div v-if="selectedOption?.icon || $slots.prefix" class="selection-icon">
						<slot name="prefix" v-bind="{ selectedOption }">
							<i v-if="selectedOption?.icon" :class="selectedOption.icon"></i>
						</slot>
					</div>

					<!-- Trigger: Button Mode -->
					<button
						v-if="trigger === 'button'"
						class="combobox-button-trigger"
						@click.prevent="toggleDropdown"
						:disabled="read_only"
					>
						<span class="selected-label truncate">
							{{ displayValue || placeholder || __("Select option") }}
						</span>
						<i
							class="fa fa-chevron-down ml-2 text-xs opacity-50 transition-transform"
							:class="{ 'rotate-180': isDropdownOpen }"
						></i>
					</button>

					<!-- Trigger: Input Mode -->
					<input
						v-else
						ref="mainInputRef"
						type="text"
						class="combobox-input"
						:value="isDropdownOpen ? query : displayValue"
						@input="onInput"
						@focus="onFocus"
						@keydown="onKeydown"
						:placeholder="__(placeholder || df?.placeholder || '')"
						autocomplete="off"
						:disabled="read_only"
					/>

					<!-- Clear Button -->
					<button
						v-if="trigger === 'input' && modelValue && !read_only"
						class="combobox-trigger clear-btn"
						@click.prevent="onSelect('')"
						title="Clear"
						tabindex="-1"
					>
						<i class="fa fa-times"></i>
					</button>

					<!-- Open Link Button — excluded from keyboard tab flow -->
					<button
						v-if="
							(df?.fieldtype === 'Link' || df?.fieldtype === 'Dynamic Link') &&
							modelValue
						"
						class="combobox-trigger open-link-btn"
						title="Open in new tab"
						tabindex="-1"
						@click.stop.prevent="openLink"
					>
						<i class="fa fa-external-link"></i>
					</button>

					<!-- Dropdown Chevron -->
					<button
						v-if="trigger === 'input'"
						class="combobox-trigger"
						@click.prevent="toggleDropdown"
						:disabled="read_only"
						tabindex="-1"
					>
						<i
							class="fa fa-chevron-down transition-transform"
							:class="{ 'rotate-180': isDropdownOpen }"
						></i>
					</button>
				</div>
			</div>

			<Teleport to="body">
				<transition name="dropdown-fade">
					<div
						v-if="isDropdownOpen"
						class="fr-dropdown"
						:style="dropdownStyle"
						ref="optionsRef"
						@mousedown.prevent
					>
						<!-- Search box inside popover for button mode -->
						<div v-if="trigger === 'button'" class="popover-search">
							<i class="fa fa-search text-muted mr-2"></i>
							<input
								ref="popoverSearchInput"
								class="popover-search-input"
								:value="query"
								@input="onInput"
								@keydown="onKeydown"
								:placeholder="__('Search...')"
								autocomplete="off"
							/>
						</div>

						<div v-if="loading" class="fr-dropdown-item text-center text-muted">
							<i class="fa fa-spinner fa-spin mr-2"></i>
							{{ __("Loading...") }}
						</div>

						<div
							v-else-if="
								(filteredOptions || []).length === 0 &&
								query !== '' &&
								!allowCustomValue
							"
							class="fr-dropdown-item text-center text-muted"
						>
							{{ __("No results found") }}
						</div>

						<!-- Create New Option -->
						<div
							v-if="allowCustomValue && query !== '' && !exactMatch"
							class="fr-dropdown-item is-create"
							:class="{ active: activeIndex === -2 }"
							@click="onSelect(query)"
							@mouseover="activeIndex = -2"
						>
							<div class="option-content">
								<div class="option-icon"><i class="fa fa-plus"></i></div>
								<div class="option-text">
									<div class="option-label text-primary font-medium">
										{{ __("Create '{0}'", [query]) }}
									</div>
								</div>
							</div>
						</div>

						<div
							v-for="(option, idx) in filteredOptions"
							:key="option.value || idx"
							class="fr-dropdown-item"
							:class="{
								active: idx === activeIndex,
								selected: option.value === modelValue,
								'is-compact': hideLabel,
							}"
							@click="onSelect(option.value)"
							@mouseover="activeIndex = idx"
						>
							<div class="option-content">
								<div v-if="option.icon" class="option-icon">
									<i :class="option.icon"></i>
								</div>
								<div class="option-text">
									<div class="option-label-row">
										<span class="option-label">
											{{ option.label || option.value }}
										</span>
										<span
											v-if="option.raw?.fieldtype || option.raw?.type"
											class="option-badge"
											:class="
												'type-' +
												String(
													option.raw?.fieldtype || option.raw?.type || ''
												)
													.toLowerCase()
													.replace(' ', '-')
											"
										>
											{{ option.raw?.fieldtype || option.raw?.type }}
										</span>
									</div>
									<div
										v-if="option.description"
										class="option-description text-muted"
									>
										{{ option.description }}
									</div>
								</div>
								<div v-if="option.value === modelValue" class="selected-check">
									<i class="fa fa-check"></i>
								</div>
							</div>
						</div>

						<!-- Custom Slot for Footer (like 'Add New') -->
						<slot name="footer"></slot>
					</div>
				</transition>
			</Teleport>
		</div>

		<div v-if="df?.description && !hideDescription" class="fr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from "vue";
import { useMetaStore } from "../stores/useMetaStore";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import { useAsyncOptionsSource } from "../composables/useAsyncOptionsSource";

const props = defineProps({
	modelValue: [String, Number, Object],
	df: Object,
	options: { type: Array, default: () => [] },
	get_query: Function,
	doctype: String,
	filters: Object,
	read_only: Boolean,
	hideLabel: Boolean,
	hideDescription: Boolean,
	placeholder: String,
	trigger: { type: String, default: "input" },
	allowCustomValue: Boolean,
	sortBy: [String, Function],
	map: {
		type: Object,
		default: () => ({
			value: "value",
			label: "label",
			description: "description",
			icon: "icon",
		}),
	},
	context: Object,
	rule: Object,
});

const emit = defineEmits(["update:modelValue", "change"]);
const metaStore = useMetaStore();

const query = ref("");
const mainInputRef = ref(null);
const popoverSearchInput = ref(null);
const activeIndex = ref(-1);
const typeaheadBuffer = ref("");
let typeaheadTimeout = null;

const {
	triggerRef: wrapperRef,
	dropdownRef: optionsRef,
	isOpen: isDropdownOpen,
	dropdownStyle,
	openDropdown: openFloatingDropdown,
	closeDropdown: closeFloatingDropdown,
	toggleDropdown: toggleFloatingDropdown,
	updatePosition: updateDropdownPosition,
	cleanup: cleanupFloatingDropdown,
} = useFloatingDropdown({
	minWidth: 220,
	maxWidth: 680,
	maxHeight: 360,
	matchTriggerWidth: true,
});

const effectiveDoctype = computed(() => {
	if (
		props.df?.fieldtype === "DocField" ||
		props.df?.fieldtype === "FieldPicker" ||
		props.df?.options === "DocField"
	) {
		return props.doctype || null;
	}
	return props.doctype || props.rule?.document_type || props.context?.document_type;
});

const isRemote = computed(() => Boolean(props.get_query || effectiveDoctype.value));

const {
	options: fetchedOptions,
	loading,
	run: runOptionFetch,
	reset: resetOptionSource,
} = useAsyncOptionsSource(async ({ query: search, start, pageSize }) => {
	if (props.get_query) {
		const rows = await props.get_query(search, props.filters || {});
		return metaStore.uniqueOptions(metaStore.normalizeLinkRows(rows || []));
	}
	if (effectiveDoctype.value) {
		return await metaStore.search_link_options({
			doctype: effectiveDoctype.value,
			txt: search || "",
			filters: props.filters || {},
			start,
			page_length: pageSize,
		});
	}
	return [];
});

const normalizedOptions = computed(() => {
	let source = props.options;
	if (typeof source === "string") {
		source = source
			.split("\n")
			.filter(Boolean)
			.map((opt) => opt.trim());
	}
	if (!source || (Array.isArray(source) && source.length === 0)) {
		source = fetchedOptions.value || [];
	}
	if (!Array.isArray(source)) return [];

	return source.map((opt, idx) => {
		if (typeof opt === "string") return { value: opt, label: opt, raw: opt };
		if (Array.isArray(opt)) {
			return {
				value: opt[0],
				label: opt[1] || opt[0],
				description: opt[2] || null,
				raw: opt,
			};
		}
		if (typeof opt === "object" && opt !== null) {
			const value = String(
				opt[props.map.value] ??
					opt.value ??
					opt.fieldname ??
					opt.name ??
					opt.id ??
					`opt_${idx}`
			);
			const label = String(opt[props.map.label] ?? opt.label ?? value);

			return {
				value,
				label,
				description: String((opt[props.map.description] ?? opt.description) || ""),
				icon: opt[props.map.icon] ?? opt.icon,
				raw: opt,
			};
		}
		return opt;
	});
});

const sortedOptions = computed(() => {
	const options = [...normalizedOptions.value];
	if (!props.sortBy) return options;
	if (typeof props.sortBy === "function") {
		options.sort(props.sortBy);
		return options;
	}
	const key = props.sortBy;
	options.sort((a, b) => {
		const valA = (a[key] || "").toString().toLowerCase();
		const valB = (b[key] || "").toString().toLowerCase();
		return valA.localeCompare(valB);
	});
	return options;
});

const filteredOptions = computed(() => {
	const options = sortedOptions.value || [];
	if (!query.value || typeof query.value !== "string") return options;
	const q = query.value.toLowerCase();
	return options.filter((option) =>
		String(`${option.label} ${option.description || ""} ${option.value}`)
			.toLowerCase()
			.includes(q)
	);
});

const exactMatch = computed(() => {
	const options = normalizedOptions.value || [];
	const q = String(query.value || "").toLowerCase();
	if (!q) return false;
	return options.some((opt) => String(opt.label || "").toLowerCase() === q);
});

const selectedOption = computed(
	() =>
		normalizedOptions.value.find((opt) => String(opt.value) === String(props.modelValue)) ||
		null
);

const displayValue = computed(() => selectedOption.value?.label || props.modelValue || "");

function openLink() {
	if (!effectiveDoctype.value || !props.modelValue) return;
	const url = `/app/${frappe.router.slug(effectiveDoctype.value)}/${encodeURIComponent(
		props.modelValue
	)}`;
	window.open(url, "_blank");
}

const debouncedRemoteSearch = flexirule.utils.debounce(async (value) => {
	if (!isRemote.value) return;
	await runOptionFetch(value || "");
	nextTick(() => updateDropdownPosition());
}, 220);

function toggleDropdown() {
	if (props.read_only) return;
	toggleFloatingDropdown();
	if (isDropdownOpen.value) openDropdown();
}

function openDropdown() {
	query.value = props.trigger === "input" ? displayValue.value : "";
	activeIndex.value = -1;
	openFloatingDropdown();
	nextTick(() => {
		updateDropdownPosition();
		if (props.trigger === "button" && popoverSearchInput.value) {
			popoverSearchInput.value.focus();
		} else if (mainInputRef.value) {
			mainInputRef.value.focus();
			mainInputRef.value.select();
		}
	});
	if (isRemote.value) runOptionFetch(query.value || "");
}

function closeDropdown() {
	closeFloatingDropdown();
}

function onFocus() {
	if (props.read_only) return;
	if (!isDropdownOpen.value) openDropdown();
}

function onInput(e) {
	query.value = e.target.value;
	if (!isDropdownOpen.value) openDropdown();
	if (isRemote.value) debouncedRemoteSearch(query.value || "");
}

function onSelect(val) {
	emit("update:modelValue", val);
	const option = normalizedOptions.value.find((o) => String(o.value) === String(val));
	emit("change", option?.raw || val);
	query.value = "";
	closeDropdown();
}

function scrollToActive() {
	nextTick(() => {
		const activeItem = optionsRef.value?.querySelector(".active");
		if (activeItem) activeItem.scrollIntoView({ block: "nearest" });
	});
}

function runTypeahead(key) {
	typeaheadBuffer.value += String(key || "").toLowerCase();
	if (typeaheadTimeout) clearTimeout(typeaheadTimeout);
	typeaheadTimeout = setTimeout(() => {
		typeaheadBuffer.value = "";
	}, 450);
	const idx = filteredOptions.value.findIndex((opt) =>
		String(opt.label || "")
			.toLowerCase()
			.startsWith(typeaheadBuffer.value)
	);
	if (idx > -1) {
		activeIndex.value = idx;
		scrollToActive();
	}
}

function onKeydown(e) {
	if (!isDropdownOpen.value) {
		if (e.key === "ArrowDown" || e.key === "Enter") {
			openDropdown();
			e.preventDefault();
		}
		return;
	}

	if (e.key === "ArrowDown") {
		e.preventDefault();
		activeIndex.value = Math.min(activeIndex.value + 1, filteredOptions.value.length - 1);
		scrollToActive();
		return;
	}

	if (e.key === "ArrowUp") {
		e.preventDefault();
		if (activeIndex.value > 0) {
			activeIndex.value -= 1;
		} else if (props.allowCustomValue && query.value !== "" && !exactMatch.value) {
			activeIndex.value = -2;
		}
		scrollToActive();
		return;
	}

	if (e.key === "Enter") {
		e.preventDefault();
		if (activeIndex.value === -2 && props.allowCustomValue) {
			onSelect(query.value);
		} else if (activeIndex.value >= 0 && activeIndex.value < filteredOptions.value.length) {
			onSelect(filteredOptions.value[activeIndex.value].value);
		} else if (filteredOptions.value.length === 1) {
			onSelect(filteredOptions.value[0].value);
		}
		return;
	}

	if (e.key === "Escape") {
		e.preventDefault();
		closeDropdown();
		return;
	}

	if (/^[\\w\\s-]$/.test(e.key) && props.trigger === "button") {
		runTypeahead(e.key);
	}
}

function handleClickOutside(e) {
	if (!isDropdownOpen.value || !wrapperRef.value) return;
	if (wrapperRef.value.contains(e.target)) return;
	if (optionsRef.value && optionsRef.value.contains(e.target)) return;
	if (props.trigger === "input" && query.value === "") {
		onSelect("");
	}
	closeDropdown();
}

let queryWatchTimer = null;
watch(query, (newQuery) => {
	activeIndex.value = -1;
	if (!isRemote.value) return;
	clearTimeout(queryWatchTimer);
	queryWatchTimer = setTimeout(() => {
		runOptionFetch(newQuery || "");
	}, 180);
});

watch(
	() => props.df?.fieldtype,
	(newVal, oldVal) => {
		if (newVal !== oldVal && ["Link", "Dynamic Link", "Autocomplete"].includes(newVal)) {
			resetOptionSource();
		}
	}
);

watch(
	() => effectiveDoctype.value,
	() => {
		resetOptionSource();
		if (isDropdownOpen.value && isRemote.value) {
			runOptionFetch(query.value || "");
		}
	}
);

watch(
	() => props.filters,
	() => {
		resetOptionSource();
		if (isDropdownOpen.value && isRemote.value) {
			runOptionFetch(query.value || "");
		}
	},
	{ deep: true }
);

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
	if (props.modelValue && isRemote.value) {
		runOptionFetch(query.value || "");
	}
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	cleanupFloatingDropdown();
	if (queryWatchTimer) clearTimeout(queryWatchTimer);
	if (typeaheadTimeout) clearTimeout(typeaheadTimeout);
});
</script>

<style scoped>
.combobox-container {
	position: relative;
	width: 100%;
}

.combobox-wrapper {
	position: relative;
	width: 100%;
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	background: var(--fr-bg-input);
	transition: all var(--fr-transition-normal);
	box-shadow: var(--fr-shadow-sm);
}

.combobox-wrapper.is-focused {
	border-color: var(--fr-accent);
	box-shadow: 0 0 0 3px var(--fr-accent-light);
}

.fr-control.no-label .combobox-wrapper {
	border-color: var(--fr-border);
	background: var(--fr-bg-input);
	box-shadow: var(--fr-shadow-sm);
}

.fr-control.no-label .combobox-wrapper:hover {
	border-color: var(--fr-border-strong);
}

.fr-control.no-label .combobox-wrapper.is-focused {
	border-color: var(--fr-accent);
	background: var(--fr-bg-input);
	box-shadow: 0 0 0 3px var(--fr-accent-light);
}

.combobox-input-group {
	display: flex;
	align-items: center;
	padding: 0 var(--fr-input-padding-x);
	height: var(--fr-input-height);
	width: 100%;
}

.combobox-button-trigger {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: space-between;
	height: 100%;
	width: 100%;
	text-align: left;
	font-size: var(--fr-input-font-size);
	font-weight: var(--fr-weight-medium);
	color: var(--fr-text);
	cursor: pointer;
	padding: 0;
	border: none;
	background: transparent;
	min-width: 0;
}

.combobox-input {
	flex: 1;
	border: none;
	background: transparent;
	padding: 0;
	height: 100%;
	font-size: var(--fr-input-font-size);
	color: var(--fr-text);
	outline: none;
	width: 100%;
	min-width: 0;
}

.combobox-trigger {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 20px;
	height: 20px;
	color: var(--fr-text-muted);
	cursor: pointer;
	background: transparent;
	border: none;
	padding: 0;
	margin-left: 4px;
	border-radius: var(--fr-radius-sm);
	transition: all 0.2s;
	flex-shrink: 0;
}

.combobox-trigger:hover:not(:disabled) {
	color: var(--fr-accent);
	background: var(--fr-accent-light);
}

/* Open-link is purely decorative — smaller, more muted */
.combobox-trigger.open-link-btn {
	width: 16px;
	height: 16px;
	font-size: 9px;
	opacity: 0.45;
	margin-left: 2px;
}
.combobox-trigger.open-link-btn:hover {
	opacity: 1;
	color: var(--fr-accent);
	background: var(--fr-accent-light);
}

/* Clear button same footprint as chevron but slightly warmer */
.combobox-trigger.clear-btn {
	font-size: 9px;
	opacity: 0.55;
}
.combobox-trigger.clear-btn:hover {
	opacity: 1;
	color: #ef4444;
	background: #fee2e2;
}

.option-content {
	display: flex;
	align-items: flex-start;
	gap: var(--fr-space-3);
	width: 100%;
}

.option-icon {
	flex-shrink: 0;
	margin-top: 2px;
	width: 16px;
	height: 16px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--fr-accent);
	font-size: 12px;
}

.option-text {
	flex: 1;
	min-width: 0;
}

.option-label-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fr-space-3);
}

.option-label {
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-semibold);
	color: var(--fr-text);
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
	background: var(--fr-bg-muted);
	color: var(--fr-text-muted);
	flex-shrink: 0;
}

.option-description {
	font-size: 10px;
	line-height: 1.4;
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.selected-check {
	flex-shrink: 0;
	color: var(--fr-accent);
	font-size: 10px;
	margin-top: 4px;
}

/* Dropdown Animation */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
	transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1),
		transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
	opacity: 0;
	transform: translateY(-8px) scale(0.98);
}

.transition-transform {
	transition: transform 0.2s ease;
}

/* ─── Popover Search (Button Mode) ─── */
.popover-search {
	display: flex;
	align-items: center;
	padding: 10px 14px;
	border-bottom: 1px solid var(--fr-border);
	background: rgba(255, 255, 255, 0.5);
	backdrop-filter: blur(4px);
}

.popover-search-icon {
	color: var(--fr-text-muted);
	margin-right: 8px;
	display: flex;
	align-items: center;
}

.popover-search-input {
	flex: 1;
	border: none !important;
	background: transparent !important;
	font-size: 13px;
	outline: none !important;
	box-shadow: none !important;
	color: var(--fr-text);
	width: 100%;
	padding: 0;
}

.popover-search-input::placeholder {
	color: var(--fr-text-muted);
	opacity: 0.7;
}

.fr-dropdown {
	background: var(--fr-bg-card, #fff);
	border: 1px solid var(--fr-border, #dbe2ea);
	border-radius: var(--fr-radius-lg, 12px);
	box-shadow: var(--fr-shadow-lg, 0 18px 36px rgba(15, 23, 42, 0.16));
	overflow: auto;
}

.fr-dropdown-item {
	padding: 8px 12px;
	cursor: pointer;
	border-bottom: 1px solid rgba(148, 163, 184, 0.12);
	background: transparent;
	transition: background 0.12s ease;
}

.fr-dropdown-item:last-child {
	border-bottom: none;
}

.fr-dropdown-item:hover,
.fr-dropdown-item.active {
	background: var(--fr-bg-muted, #f8fafc);
}

.fr-dropdown-item.selected {
	background: var(--fr-accent-light, #e8f0ff);
}
</style>

<style>
/* Global styles for teleported ComboBox dropdown content */
.fr-dropdown .option-content {
	display: flex;
	align-items: flex-start;
	gap: var(--fr-space-3, 12px);
	width: 100%;
}

.fr-dropdown .option-icon {
	flex-shrink: 0;
	margin-top: 2px;
	width: 16px;
	height: 16px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--fr-accent, #2563eb);
	font-size: 12px;
}

.fr-dropdown .option-text {
	flex: 1;
	min-width: 0;
}

.fr-dropdown .option-label-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fr-space-3, 12px);
}

.fr-dropdown .option-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--fr-text, #1e293b);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.fr-dropdown .option-badge {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 4px;
	letter-spacing: 0.05em;
	background: var(--fr-bg-muted, #f1f5f9);
	color: var(--fr-text-muted, #64748b);
	flex-shrink: 0;
}

.fr-dropdown .option-description {
	font-size: 10px;
	line-height: 1.4;
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	color: var(--fr-text-muted, #64748b);
}

.fr-dropdown .selected-check {
	flex-shrink: 0;
	color: var(--fr-accent, #2563eb);
	font-size: 10px;
	margin-top: 4px;
}
</style>
