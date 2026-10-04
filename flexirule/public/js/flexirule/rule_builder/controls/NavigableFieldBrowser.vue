<template>
	<div
		class="fxr-control navigable-field-browser"
		:class="{
			'no-label': hideLabel,
			'has-error': showValidation && !isValid,
		}"
		v-fxr-fieldname="df?.fieldname || fieldname || null"
	>
		<label v-if="df?.label && !hideLabel" class="fxr-label" :class="{ reqd: df?.reqd }">
			{{ __(df.label) }}
		</label>

		<div class="field-browser-container" ref="triggerRef" @focusout="onFocusOut">
			<!-- Trigger Button or Multi Badge Display -->
			<div
				class="field-browser-trigger"
				:class="{ 'is-focused': isOpen, 'is-readonly': readOnly }"
				@click="toggleDropdown"
				@keydown="onKeydown"
				tabindex="0"
			>
				<div class="selected-display truncate">
					<template v-if="allowMulti">
						<span v-if="!modelValue || !modelValue.length" class="placeholder">
							{{ __(placeholder || df?.placeholder || "Select fields...") }}
						</span>
						<div v-else class="badges-list">
							<span
								v-for="(val, idx) in modelValue"
								:key="val || idx"
								class="field-badge"
							>
								{{ val }}
								<i
									v-if="!readOnly"
									class="fa fa-times remove-badge"
									@click.stop="removeItem(val)"
								></i>
							</span>
						</div>
					</template>
					<template v-else>
						<span v-if="modelValue" class="selected-value">
							{{ displayLabel }}
						</span>
						<span v-else class="placeholder">
							{{ __(placeholder || df?.placeholder || "Select field...") }}
						</span>
					</template>
				</div>

				<div class="trigger-actions">
					<button
						v-if="!allowMulti && modelValue && !readOnly"
						class="clear-btn"
						@click.stop.prevent="clearSelection"
						title="Clear"
						tabindex="-1"
					>
						<i class="fa fa-times"></i>
					</button>
					<i
						class="fa fa-chevron-down chevron-icon transition-transform"
						:class="{ 'rotate-180': isOpen }"
					></i>
				</div>
			</div>

			<!-- Dropdown Popover -->
			<Teleport to="body">
				<transition name="dropdown-fade">
					<div
						v-if="isOpen"
						class="fxr-dropdown navigable-browser-popover"
						:style="dropdownStyle"
						ref="dropdownRef"
						tabindex="-1"
						@mousedown.prevent
						@keydown="onKeydown"
					>
						<!-- Breadcrumb Navigation Bar -->
						<div class="browser-header">
							<div class="breadcrumbs-bar">
								<span
									v-for="(item, idx) in navStack"
									:key="idx"
									class="breadcrumb-item"
									:class="{ active: idx === navStack.length - 1 }"
									@click="popToLevel(idx)"
								>
									<span class="breadcrumb-label">{{ item.label }}</span>
									<i
										v-if="idx < navStack.length - 1"
										class="fa fa-angle-right breadcrumb-sep"
									></i>
								</span>
							</div>

							<!-- Scoped Search Input -->
							<div class="search-box">
								<i class="fa fa-search search-icon"></i>
								<input
									ref="searchInputRef"
									type="text"
									class="search-input"
									v-model="searchQuery"
									:placeholder="__('Search in {0}...', [activeLevel?.label])"
									autocomplete="off"
								/>
								<button
									v-if="searchQuery"
									class="search-clear-btn"
									@click="searchQuery = ''"
								>
									<i class="fa fa-times"></i>
								</button>
							</div>
						</div>

						<!-- Field List Body -->
						<div class="browser-body">
							<div v-if="loading" class="text-center p-3 text-muted">
								<i class="fa fa-spinner fa-spin mr-2"></i>
								{{ __("Loading fields...") }}
							</div>

							<div
								v-else-if="!filteredFields.length"
								class="text-center p-3 text-muted"
							>
								{{ __("No matching fields found in {0}", [activeLevel?.label]) }}
							</div>

							<div v-else class="fields-list">
								<div
									v-for="(field, idx) in filteredFields"
									:key="field.value || idx"
									class="field-row-item"
									:class="{
										selected: isFieldSelected(field.value),
										'is-navigable': field.is_navigable,
										active: idx === activeIndex,
									}"
									@click="selectField(field)"
									@mouseover="activeIndex = idx"
								>
									<!-- Field Icon & Badges -->
									<div class="field-icon">
										<i :class="getFieldIcon(field)"></i>
									</div>

									<div class="field-meta">
										<div class="field-label-line">
											<span class="field-label">{{ field.label }}</span>
											<span class="field-name-code"
												>({{ field.fieldname }})</span
											>
										</div>
										<div class="field-desc">
											<span
												class="fieldtype-tag"
												:class="
													'type-' +
													String(field.fieldtype)
														.toLowerCase()
														.replace(' ', '-')
												"
											>
												{{ field.fieldtype }}
											</span>
											<span v-if="field.options" class="options-tag">
												→ {{ field.options }}
											</span>
										</div>
									</div>

									<!-- Right Navigation Arrow for Link & Table fields -->
									<div v-if="field.is_navigable" class="field-nav-action">
										<button
											class="btn-nav-into"
											@click.stop.prevent="navigateIntoField(field)"
											:title="__('Navigate into {0}', [field.options])"
										>
											<i class="fa fa-chevron-right"></i>
										</button>
									</div>

									<!-- Selected Checkmark -->
									<div
										v-else-if="isFieldSelected(field.value)"
										class="selected-check"
									>
										<i class="fa fa-check"></i>
									</div>
								</div>
							</div>
						</div>
					</div>
				</transition>
			</Teleport>
		</div>

		<!-- Validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";

const props = defineProps({
	modelValue: [String, Array],
	df: Object,
	fieldname: String,
	doctype: { type: String, required: true },
	readOnly: { type: Boolean, default: false },
	hideLabel: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
	placeholder: String,
	allowMulti: { type: Boolean, default: false },
	options: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "change"]);

const searchInputRef = ref(null);
const searchQuery = ref("");
const activeIndex = ref(-1);
const loading = ref(false);
const rawDocMeta = ref({});

const {
	triggerRef,
	dropdownRef,
	isOpen,
	dropdownStyle,
	openDropdown: openFloatingDropdown,
	closeDropdown: closeFloatingDropdown,
	updatePosition,
	cleanup: cleanupFloatingDropdown,
} = useFloatingDropdown({
	minWidth: 320,
	maxWidth: 600,
	maxHeight: 400,
	matchTriggerWidth: true,
});

// Navigation Stack State
const navStack = ref([]);

function initNavStack() {
	navStack.value = [
		{
			doctype: props.doctype,
			pathPrefix: "",
			label: props.doctype,
		},
	];
}

const activeLevel = computed(() => navStack.value[navStack.value.length - 1] || null);

// Load fields for active level DocType
const levelFields = ref([]);

async function loadFieldsForActiveLevel() {
	const current = activeLevel.value;
	if (!current || !current.doctype) {
		levelFields.value = [];
		return;
	}

	loading.value = true;
	try {
		const dt = current.doctype;
		const meta = await flexirule.utils.get_doctype_meta(dt);
		rawDocMeta.value[dt] = meta;

		const list = [];
		const seen = new Set();

		// System / Standard fields for root or child
		const stdFields = [
			{ fieldname: "name", label: __("ID (name)"), fieldtype: "Data" },
			{
				fieldname: "owner",
				label: __("Created By (owner)"),
				fieldtype: "Link",
				options: "User",
			},
			{ fieldname: "creation", label: __("Created On (creation)"), fieldtype: "Datetime" },
			{ fieldname: "modified", label: __("Modified On (modified)"), fieldtype: "Datetime" },
			{
				fieldname: "modified_by",
				label: __("Modified By (modified_by)"),
				fieldtype: "Link",
				options: "User",
			},
			{ fieldname: "docstatus", label: __("Document Status (docstatus)"), fieldtype: "Int" },
		];

		const prefix = current.pathPrefix ? `${current.pathPrefix}.` : "";

		stdFields.forEach((sf) => {
			const fullVal = `${prefix}${sf.fieldname}`;
			seen.add(fullVal);
			list.push({
				...sf,
				value: fullVal,
				parentDoctype: dt,
				is_navigable: sf.fieldtype === "Link" && sf.options && sf.options !== "User",
			});
		});

		if (meta && meta.fields) {
			const fieldsSorted = [...meta.fields].sort((a, b) =>
				(a.label || a.fieldname || "").localeCompare(b.label || b.fieldname || "")
			);
			for (const df of fieldsSorted) {
				if (
					frappe.model.no_value_type.includes(df.fieldtype) &&
					!["Table", "Table MultiSelect"].includes(df.fieldtype)
				) {
					continue;
				}
				if (df.is_virtual) continue;

				const fullVal = `${prefix}${df.fieldname}`;
				if (seen.has(fullVal)) continue;
				seen.add(fullVal);

				const isNav = Boolean(
					(df.fieldtype === "Link" ||
						df.fieldtype === "Table" ||
						df.fieldtype === "Table MultiSelect") &&
						df.options &&
						df.options !== dt
				);

				list.push({
					fieldname: df.fieldname,
					label: __(df.label || df.fieldname),
					fieldtype: df.fieldtype,
					options: df.options,
					value: fullVal,
					parentDoctype: dt,
					is_navigable: isNav,
				});
			}
		}

		levelFields.value = list;
	} catch (e) {
		console.warn("NavigableFieldBrowser: Failed to load fields for", current.doctype, e);
		levelFields.value = [];
	} finally {
		loading.value = false;
	}
}

watch(activeLevel, () => {
	loadFieldsForActiveLevel();
});

const filteredFields = computed(() => {
	const q = searchQuery.value.trim().toLowerCase();
	if (!q) return levelFields.value;
	return levelFields.value.filter((f) => {
		return (
			String(f.label || "")
				.toLowerCase()
				.includes(q) ||
			String(f.fieldname || "")
				.toLowerCase()
				.includes(q) ||
			String(f.fieldtype || "")
				.toLowerCase()
				.includes(q) ||
			String(f.options || "")
				.toLowerCase()
				.includes(q)
		);
	});
});

function isFieldSelected(val) {
	if (props.allowMulti) {
		return Array.isArray(props.modelValue) && props.modelValue.includes(val);
	}
	return String(props.modelValue || "") === String(val);
}

const displayLabel = computed(() => {
	if (!props.modelValue) return "";
	return String(props.modelValue);
});

function navigateIntoField(field) {
	if (!field.options) return;
	navStack.value.push({
		doctype: field.options,
		pathPrefix: field.value,
		label: `${field.label || field.fieldname}`,
	});
	searchQuery.value = "";
	activeIndex.value = -1;
	nextTick(() => {
		updatePosition();
		if (searchInputRef.value) searchInputRef.value.focus();
	});
}

function popToLevel(index) {
	if (index >= 0 && index < navStack.value.length) {
		navStack.value = navStack.value.slice(0, index + 1);
		searchQuery.value = "";
		activeIndex.value = -1;
		nextTick(() => {
			updatePosition();
			if (searchInputRef.value) searchInputRef.value.focus();
		});
	}
}

function selectField(field) {
	const val = field.value;
	if (props.allowMulti) {
		const current = Array.isArray(props.modelValue) ? [...props.modelValue] : [];
		const idx = current.indexOf(val);
		if (idx > -1) {
			current.splice(idx, 1);
		} else {
			current.push(val);
		}
		emit("update:modelValue", current);
		emit("change", current);
	} else {
		emit("update:modelValue", val);
		emit("change", val);
		closeDropdown();
	}
}

function removeItem(val) {
	if (!props.allowMulti || !Array.isArray(props.modelValue)) return;
	const updated = props.modelValue.filter((item) => item !== val);
	emit("update:modelValue", updated);
	emit("change", updated);
}

function clearSelection() {
	if (props.allowMulti) {
		emit("update:modelValue", []);
		emit("change", []);
	} else {
		emit("update:modelValue", "");
		emit("change", "");
	}
}

function toggleDropdown() {
	if (props.readOnly) return;
	if (isOpen.value) {
		closeDropdown();
	} else {
		openDropdown();
	}
}

function openDropdown() {
	if (props.readOnly) return;
	initNavStack();
	searchQuery.value = "";
	activeIndex.value = -1;
	openFloatingDropdown();
	loadFieldsForActiveLevel();

	nextTick(() => {
		updatePosition();
		if (searchInputRef.value) searchInputRef.value.focus();
	});
}

function closeDropdown() {
	closeFloatingDropdown();
}

function onFocusOut(e) {
	if (!isOpen.value) return;
	const related = e.relatedTarget;
	if (triggerRef.value && triggerRef.value.contains(related)) return;
	if (dropdownRef.value && dropdownRef.value.contains(related)) return;
	closeDropdown();
}

function onKeydown(e) {
	if (!isOpen.value) {
		if (e.key === "ArrowDown" || e.key === "Enter") {
			openDropdown();
			e.preventDefault();
		}
		return;
	}

	if (e.key === "ArrowDown") {
		e.preventDefault();
		if (activeIndex.value < filteredFields.value.length - 1) {
			activeIndex.value++;
		}
		return;
	}

	if (e.key === "ArrowUp") {
		e.preventDefault();
		if (activeIndex.value > 0) {
			activeIndex.value--;
		}
		return;
	}

	if (e.key === "Enter") {
		e.preventDefault();
		if (activeIndex.value >= 0 && activeIndex.value < filteredFields.value.length) {
			selectField(filteredFields.value[activeIndex.value]);
		}
		return;
	}

	if (e.key === "Escape") {
		e.preventDefault();
		closeDropdown();
		return;
	}
}

function getFieldIcon(field) {
	if (field.fieldtype === "Table" || field.fieldtype === "Table MultiSelect") {
		return "fa fa-table text-warning";
	}
	if (field.fieldtype === "Link" || field.fieldtype === "Dynamic Link") {
		return "fa fa-link text-info";
	}
	if (["Date", "Datetime", "Time"].includes(field.fieldtype)) {
		return "fa fa-calendar text-primary";
	}
	if (["Int", "Float", "Currency", "Percent"].includes(field.fieldtype)) {
		return "fa fa-hashtag text-success";
	}
	return "fa fa-font text-muted";
}

watch(
	() => props.doctype,
	() => {
		initNavStack();
	}
);

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	if (props.allowMulti) {
		return Array.isArray(props.modelValue) && props.modelValue.length > 0;
	}
	return props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "";
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({
	validate,
});

onMounted(() => {
	initNavStack();
});

onBeforeUnmount(() => {
	cleanupFloatingDropdown();
});
</script>

<style scoped>
.navigable-field-browser {
	width: 100%;
	position: relative;
}

.field-browser-container {
	position: relative;
	width: 100%;
}

.field-browser-trigger {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x);
	min-height: var(--fxr-input-height);
	background: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	cursor: pointer;
	transition: all var(--fxr-transition-fast);
}

.field-browser-trigger:hover:not(.is-readonly) {
	border-color: var(--fxr-border-strong);
}

.field-browser-trigger.is-focused {
	border-color: var(--fxr-accent);
	box-shadow: 0 0 0 2px var(--fxr-accent-light);
}

.selected-display {
	flex: 1;
	min-width: 0;
}

.placeholder {
	color: var(--fxr-text-muted);
	font-size: var(--fxr-input-font-size);
}

.selected-value {
	font-size: var(--fxr-input-font-size);
	font-weight: 600;
	color: var(--fxr-text-strong);
}

.badges-list {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
}

.field-badge {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 6px;
	background: var(--fxr-surface-soft);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text-strong);
}

.remove-badge {
	cursor: pointer;
	font-size: 10px;
	opacity: 0.6;
}

.remove-badge:hover {
	opacity: 1;
	color: var(--fxr-text-danger);
}

.trigger-actions {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-left: 8px;
}

.clear-btn {
	background: transparent;
	border: none;
	color: var(--fxr-text-muted);
	font-size: 11px;
	cursor: pointer;
	padding: 0;
}

.clear-btn:hover {
	color: var(--fxr-text-danger);
}

.chevron-icon {
	font-size: 11px;
	color: var(--fxr-text-muted);
}

/* Dropdown Popover */
.navigable-browser-popover {
	background-color: var(--fxr-surface-elevated, #ffffff);
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: var(--fxr-radius-lg, 8px);
	box-shadow: var(--fxr-shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
	display: flex;
	flex-direction: column;
	overflow: hidden;
	max-height: 380px;
}

/* Header & Breadcrumbs */
.browser-header {
	display: flex;
	flex-direction: column;
	background-color: var(--fxr-surface-2, #f8fafc);
	border-bottom: 1px solid var(--fxr-border-subtle, #e2e8f0);
	padding: 8px 12px;
	gap: 8px;
}

.breadcrumbs-bar {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 4px;
	font-size: 12px;
}

.breadcrumb-item {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	cursor: pointer;
	color: var(--fxr-text-secondary, #64748b);
	font-weight: 500;
}

.breadcrumb-item:hover {
	color: var(--fxr-accent, #2563eb);
}

.breadcrumb-item.active {
	color: var(--fxr-text-strong, #0f172a);
	font-weight: 700;
	cursor: default;
}

.breadcrumb-sep {
	font-size: 10px;
	color: var(--fxr-text-muted, #94a3b8);
	margin: 0 2px;
}

.search-box {
	display: flex;
	align-items: center;
	background: var(--fxr-bg-input, #ffffff);
	border: 1px solid var(--fxr-border, #cbd5e1);
	border-radius: var(--fxr-radius-md, 6px);
	padding: 4px 8px;
	gap: 6px;
}

.search-icon {
	color: var(--fxr-text-muted, #94a3b8);
	font-size: 12px;
}

.search-input {
	flex: 1;
	border: none !important;
	outline: none !important;
	background: transparent !important;
	font-size: 12px;
	color: var(--fxr-text, #334155);
	padding: 0 !important;
}

.search-clear-btn {
	background: transparent;
	border: none;
	color: var(--fxr-text-muted);
	cursor: pointer;
	font-size: 10px;
}

/* Body & Fields List */
.browser-body {
	flex: 1;
	overflow-y: auto;
	max-height: 280px;
}

.fields-list {
	display: flex;
	flex-direction: column;
}

.field-row-item {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid var(--fxr-border-subtle, #f1f5f9);
	cursor: pointer;
	transition: background-color 0.12s ease;
	gap: 10px;
}

.field-row-item:last-child {
	border-bottom: none;
}

.field-row-item:hover,
.field-row-item.active {
	background-color: var(--fxr-bg-hover, #f1f5f9);
}

.field-row-item.selected {
	background-color: var(--fxr-accent-soft, #eff6ff);
}

.field-icon {
	width: 18px;
	display: flex;
	justify-content: center;
	font-size: 12px;
}

.field-meta {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
}

.field-label-line {
	display: flex;
	align-items: center;
	gap: 6px;
}

.field-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-strong, #0f172a);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.field-name-code {
	font-size: 11px;
	color: var(--fxr-text-muted, #94a3b8);
	font-family: var(--fxr-font-mono, monospace);
}

.field-desc {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 10px;
	margin-top: 2px;
}

.fieldtype-tag {
	font-weight: 700;
	text-transform: uppercase;
	padding: 0 4px;
	border-radius: 3px;
	background: var(--fxr-bg-muted, #e2e8f0);
	color: var(--fxr-text-secondary, #475569);
}

.options-tag {
	color: var(--fxr-text-muted, #64748b);
	font-style: italic;
}

.field-nav-action {
	flex-shrink: 0;
}

.btn-nav-into {
	background: var(--fxr-surface-2, #f1f5f9);
	border: 1px solid var(--fxr-border, #cbd5e1);
	border-radius: 4px;
	width: 26px;
	height: 26px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--fxr-accent, #2563eb);
	cursor: pointer;
	transition: all 0.15s ease;
}

.btn-nav-into:hover {
	background: var(--fxr-accent, #2563eb);
	color: #ffffff;
	border-color: var(--fxr-accent, #2563eb);
}

.selected-check {
	color: var(--fxr-accent, #2563eb);
	font-size: 12px;
}
</style>
