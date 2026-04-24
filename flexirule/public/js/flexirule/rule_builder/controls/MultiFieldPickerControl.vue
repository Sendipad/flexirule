<script setup>
import { computed, ref, watch } from "vue";
/**
 * MultiFieldPickerControl - Select multiple DocType fields
 * Returns array of field names
 */

const props = defineProps({
	df: Object,
	modelValue: [Array, String],
	documentType: String,
	read_only: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

const searchQuery = ref("");
const showDropdown = ref(false);
const fields = ref([]);
const loading = ref(false);

const selected = computed({
	get() {
		if (Array.isArray(props.modelValue)) return props.modelValue;
		if (typeof props.modelValue === "string" && props.modelValue) {
			try {
				return JSON.parse(props.modelValue);
			} catch {
				return props.modelValue
					.split("\n")
					.map((s) => s.trim())
					.filter(Boolean);
			}
		}
		return [];
	},
	set(val) {
		emit("update:modelValue", val);
	},
});

const availableFields = computed(() => {
	return fields.value.filter((f) => !selected.value.includes(f.value));
});

const filteredFields = computed(() => {
	if (!searchQuery.value) return availableFields.value;
	const query = searchQuery.value.toLowerCase();
	return availableFields.value.filter(
		(f) =>
			f.value.toLowerCase().includes(query) ||
			(f.label && f.label.toLowerCase().includes(query))
	);
});

async function loadFields() {
	if (!props.documentType) {
		fields.value = [];
		return;
	}
	loading.value = true;
	try {
		const result = await frappe.call({
			method: "flexirule.ruleflow.api.get_doctype_fields",
			args: { doctype: props.documentType },
		});
		fields.value = result.message.parent_fields || [];
	} catch (e) {
		fields.value = [];
	} finally {
		loading.value = false;
	}
}

function addField(field) {
	emit("update:modelValue", [...selected.value, field.value]);
	showDropdown.value = false;
	searchQuery.value = "";
}

function removeField(fieldname) {
	emit(
		"update:modelValue",
		selected.value.filter((f) => f !== fieldname)
	);
}

function handleFocus() {
	showDropdown.value = true;
	if (!fields.value.length && props.documentType) loadFields();
}

function handleBlur() {
	setTimeout(() => {
		showDropdown.value = false;
	}, 200);
}

watch(() => props.documentType, loadFields, { immediate: true });
</script>

<!--
@deprecated
Reason: Superseded by standard MultiSelect/Autocomplete in ConfigurableAction.
Replaced by: flexirule.ui.ConfigurableAction
Removal Target: v2.0
-->
<template>
	<div class="multi-field-picker">
		<label v-if="df.label" class="control-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</label>

		<!-- Selected fields as tags -->
		<div class="selected-fields" v-if="selected.length">
			<span v-for="fieldname in selected" :key="fieldname" class="field-tag">
				{{ fieldname }}
				<button
					v-if="!read_only"
					type="button"
					class="remove-btn"
					@click="removeField(fieldname)"
				>
					×
				</button>
			</span>
		</div>

		<!-- Add field input -->
		<div class="add-field-wrapper" v-if="!read_only">
			<input
				type="text"
				class="form-control form-control-sm"
				v-model="searchQuery"
				@focus="handleFocus"
				@blur="handleBlur"
				:placeholder="__('Add field...')"
			/>
			<div v-if="showDropdown && filteredFields.length" class="field-dropdown">
				<div
					v-for="field in filteredFields"
					:key="field.value"
					class="field-option"
					@mousedown.prevent="addField(field)"
				>
					<span class="field-name">{{ field.value }}</span>
					<span class="field-label">{{ field.label }}</span>
				</div>
			</div>
		</div>

		<small v-if="df.description" class="form-text text-muted">{{ df.description }}</small>
	</div>
</template>

<style scoped>
.multi-field-picker {
	margin-bottom: 15px;
}
.control-label {
	font-size: 12px;
	font-weight: 500;
	margin-bottom: 5px;
	display: block;
}
.selected-fields {
	display: flex;
	flex-wrap: wrap;
	gap: 5px;
	margin-bottom: 8px;
}
.field-tag {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 3px 8px;
	background: var(--bg-light-gray);
	border-radius: 4px;
	font-size: 12px;
	font-family: monospace;
}
.remove-btn {
	background: none;
	border: none;
	padding: 0 2px;
	font-size: 14px;
	cursor: pointer;
	color: var(--text-muted);
}
.remove-btn:hover {
	color: var(--red);
}
.add-field-wrapper {
	position: relative;
}
.field-dropdown {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	background: white;
	border: 1px solid var(--border-color);
	border-radius: 4px;
	max-height: 200px;
	overflow-y: auto;
	z-index: 100;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.field-option {
	padding: 6px 10px;
	cursor: pointer;
	display: flex;
	align-items: center;
	gap: 8px;
}
.field-option:hover {
	background: var(--bg-light-gray);
}
.field-name {
	font-family: monospace;
	font-size: 12px;
	color: var(--primary);
}
.field-label {
	font-size: 11px;
	color: var(--text-muted);
}
</style>
