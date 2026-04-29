<script setup>
/**
 * FieldPickerControl - DocField autocomplete picker
 * Shows fields from the target doctype with search
 * Supports pre-fetched fields from store via 'fields' prop
 */
import { ref, computed, watch, nextTick } from "vue";

const props = defineProps({
	df: Object,
	modelValue: String,
	documentType: String, // Optional: fallback for API fetch
	fields: { type: Array, default: null }, // NEW: Pre-fetched fields from store
	read_only: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

const searchQuery = ref("");
const showDropdown = ref(false);
const apiFields = ref([]); // Fields fetched from API (fallback)
const loading = ref(false);
const activeIndex = ref(-1);

const content = computed({
	get: () => props.modelValue || "",
	set: (val) => emit("update:modelValue", val),
});

// Use props.fields if provided, otherwise use apiFields from API
const effectiveFields = computed(() => {
	if (props.fields && props.fields.length > 0) {
		return props.fields;
	}
	return apiFields.value;
});

const filteredFields = computed(() => {
	if (!searchQuery.value) return effectiveFields.value;
	const query = searchQuery.value.toLowerCase();
	return effectiveFields.value.filter(
		(f) =>
			(f.value && f.value.toLowerCase().includes(query)) ||
			(f.label && f.label.toLowerCase().includes(query))
	);
});

const displayValue = computed(() => {
	const field = effectiveFields.value.find((f) => f.value === content.value);
	return field ? `${field.label}` : content.value;
});

function getPrimaryLabel(field) {
	if (!field) return "";
	const rawLabel = String(field.label || "").trim();
	const rawValue = String(field.value || "").trim();
	if (!rawLabel) return rawValue;

	// Convert "row.account (Account)" to a cleaner "Account"
	const match = rawLabel.match(/\(([^)]+)\)\s*$/);
	if (match && match[1]) return match[1].trim();
	return rawLabel;
}

function getSecondaryMeta(field) {
	if (!field) return "";
	const rawValue = String(field.value || "").trim();
	const rawLabel = String(field.label || "").trim();
	if (!rawValue) return rawLabel;
	if (!rawLabel) return rawValue;
	// If label already equals value, avoid duplicate line.
	if (rawLabel === rawValue) return "";
	return rawValue;
}

async function loadFields() {
	// Skip API call if fields prop is provided
	if (props.fields && props.fields.length > 0) return;

	if (!props.documentType) {
		apiFields.value = [];
		return;
	}
	loading.value = true;
	try {
		apiFields.value = await flexirule.utils.get_doctype_fields(props.documentType);
	} catch (e) {
		apiFields.value = [];
	} finally {
		loading.value = false;
	}
}

function selectField(field) {
	content.value = field.value;
	showDropdown.value = false;
	searchQuery.value = "";
	activeIndex.value = -1;
}

function handleInput(e) {
	searchQuery.value = e.target.value;
	showDropdown.value = true;
}

function handleFocus() {
	showDropdown.value = true;
	searchQuery.value = displayValue.value;
	if (!effectiveFields.value.length && props.documentType) loadFields();
}

function clearField() {
	content.value = "";
	searchQuery.value = "";
	showDropdown.value = false;
	emit("update:modelValue", "");
}

function handleBlur() {
	setTimeout(() => {
		showDropdown.value = false;
	}, 200);
}

function handleKeydown(e) {
	if (!showDropdown.value) {
		if (e.key === "ArrowDown" || e.key === "Enter") {
			showDropdown.value = true;
			e.preventDefault();
		}
		return;
	}

	if (e.key === "ArrowDown") {
		e.preventDefault();
		if (activeIndex.value < filteredFields.value.length - 1) {
			activeIndex.value++;
			scrollToActive();
		}
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		if (activeIndex.value > 0) {
			activeIndex.value--;
			scrollToActive();
		}
	} else if (e.key === "Enter") {
		e.preventDefault();
		if (activeIndex.value >= 0 && activeIndex.value < filteredFields.value.length) {
			selectField(filteredFields.value[activeIndex.value]);
		}
	} else if (e.key === "Escape") {
		e.preventDefault();
		showDropdown.value = false;
	}
}

function scrollToActive() {
	nextTick(() => {
		const activeItem = document.querySelector(".field-option.active-item");
		if (activeItem) {
			activeItem.scrollIntoView({ block: "nearest" });
		}
	});
}

watch(searchQuery, () => {
	activeIndex.value = -1;
});

watch(showDropdown, (val) => {
	if (val) activeIndex.value = -1;
});

function onDrop(event) {
	let variable = event.dataTransfer.getData("application/x-flexirule-variable");
	if (variable) {
		event.preventDefault();

		// Sanitize variable name to prevent injection
		if (/[{}"']/.test(variable)) {
			console.warn("FlexiRule: Rejected unsafe variable name drop:", variable);
			return;
		}

		// Field pickers usually expect the literal field name/variable name
		emit("update:modelValue", variable);
	}
}

// Only trigger API load if we don't have pre-fetched fields
watch(
	() => props.documentType,
	() => {
		if (!props.fields || props.fields.length === 0) {
			loadFields();
		}
	},
	{ immediate: true }
);
</script>

<template>
	<div class="field-picker-control">
		<label v-if="df.label" class="control-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</label>

		<div class="field-input-wrapper">
			<input
				type="text"
				class="form-control form-control-sm"
				:value="showDropdown ? searchQuery : displayValue"
				@input="handleInput"
				@focus="handleFocus"
				@blur="handleBlur"
				@keydown="handleKeydown"
				@dragover.prevent
				@drop="onDrop"
				:placeholder="__('Search fields...')"
				:disabled="read_only"
			/>
			<div v-if="content && !read_only" class="field-clear" @click.stop="clearField">
				<i class="fa fa-times"></i>
			</div>
			<div v-if="loading" class="field-loading">
				<span class="spinner-border spinner-border-sm"></span>
			</div>
			<div v-if="showDropdown && filteredFields.length" class="field-dropdown">
				<div
					v-for="(field, idx) in filteredFields"
					:key="field.value"
					class="field-option"
					:class="{
						selected: field.value === content,
						'active-item': idx === activeIndex,
					}"
					@mousedown.prevent="selectField(field)"
				>
					<div class="field-text">
						<div class="field-primary">{{ __(getPrimaryLabel(field)) }}</div>
						<div v-if="getSecondaryMeta(field)" class="field-meta">
							{{ getSecondaryMeta(field) }}
						</div>
					</div>
					<span class="field-type badge badge-secondary">{{
						field.fieldtype || "Data"
					}}</span>
				</div>
			</div>
			<div v-if="showDropdown && !filteredFields.length && !loading" class="field-dropdown">
				<div class="field-option disabled">{{ __("No fields found") }}</div>
			</div>
		</div>

		<small v-if="df.description" class="form-text text-muted">{{ df.description }}</small>
	</div>
</template>

<style scoped>
.field-picker-control {
	margin-bottom: 15px;
}
.control-label {
	font-size: 12px;
	font-weight: 500;
	margin-bottom: 5px;
	display: block;
}
.field-input-wrapper {
	position: relative;
	display: flex;
	align-items: center;
	z-index: 1;
}
.field-input-wrapper:focus-within {
	z-index: 1201; /* Higher than other rows */
}
.field-input-wrapper input {
	padding-right: 24px;
}
.field-clear {
	position: absolute;
	right: 8px;
	top: 50%;
	transform: translateY(-50%);
	cursor: pointer;
	color: #94a3b8;
	font-size: 12px;
	padding: 4px;
	z-index: 2;
}
[dir="rtl"] .field-clear {
	right: auto;
	left: 8px;
}
.field-clear:hover {
	color: #ef4444;
}
.field-loading {
	position: absolute;
	right: 10px;
	top: 50%;
	transform: translateY(-50%);
}
[dir="rtl"] .field-loading {
	right: auto;
	left: 10px;
}
.field-dropdown {
	position: absolute;
	top: 100%;
	inset-inline-start: 0;
	width: max(100%, 360px);
	max-width: min(560px, calc(100vw - 32px));
	background: white;
	border: 1px solid var(--border-color);
	border-radius: 8px;
	max-height: 300px;
	overflow-y: auto;
	z-index: 1200;
	box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12), 0 2px 6px rgba(15, 23, 42, 0.08);
	margin-top: 4px;
}
.field-option {
	padding: 8px 10px;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	border-bottom: 1px solid var(--border-color);
	background: #fff;
}
.field-option:last-child {
	border-bottom: none;
}
.field-option:hover {
	background: #f8fafc;
}
.field-option.selected {
	background: #eff6ff;
}
.field-option.active-item {
	background: #eff6ff;
}
.field-option.disabled {
	color: var(--text-muted);
	cursor: default;
}
.field-text {
	flex: 1;
	min-width: 0;
}
.field-primary {
	font-size: 13px;
	font-weight: 500;
	color: #1f2937;
	line-height: 1.2;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.field-meta {
	font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
		"Courier New", monospace;
	font-size: 11px;
	color: #64748b;
	line-height: 1.2;
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.field-type {
	font-size: 10px;
	padding: 2px 6px;
	flex-shrink: 0;
	background: #f1f5f9;
	color: #475569;
	border-radius: 999px;
}
</style>
