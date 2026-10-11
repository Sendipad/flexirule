<template>
	<div class="embedded-child-editor">
		<div class="editor-header">
			<div>
				<h6 class="mb-0">{{ __("Embedded Child Tables") }}</h6>
				<p class="section-description">
					{{ __("Select child table fields to embed as nested arrays under each document.") }}
				</p>
			</div>
			<button
				v-if="!readOnly"
				type="button"
				class="btn btn-xs btn-outline-primary"
				@click="addChildSection"
			>
				<i class="fa fa-plus mr-1"></i>{{ __("Add Embedded Child Table") }}
			</button>
		</div>

		<div v-if="localSections.length === 0" class="empty-state text-muted py-2 text-center">
			<small>{{ __("No child tables selected.") }}</small>
		</div>

		<div v-else class="child-sections">
			<div v-for="(section, index) in localSections" :key="section.id" class="child-section-card">
				<div class="section-top-row">
					<div class="child-field-select flex-1">
						<label class="ctrl-label">{{ __("Child Table") }} <span class="text-danger">*</span></label>
						<select
							v-model="section.child_field"
							class="form-control form-control-sm"
							:disabled="readOnly"
							@change="onChildFieldChange(section)"
						>
							<option value="">{{ __("-- Select Child Table --") }}</option>
							<option v-for="ct in childTableOptions" :key="ct.value" :value="ct.value">
								{{ ct.label }} ({{ ct.value }})
							</option>
						</select>
					</div>

					<button
						v-if="!readOnly"
						type="button"
						class="btn btn-xs btn-link text-danger remove-section-btn"
						:title="__('Remove child table section')"
						@click="removeSection(index)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>

				<div v-if="section.child_field" class="section-fields-row">
					<label class="ctrl-label">{{ __("Selected Child Fields") }}</label>
					<MultiSelectList
						:df="{
							label: '',
							fieldname: 'fields',
							placeholder: __('Select fields from child table...'),
						}"
						:options="getChildFieldOptions(section.child_field)"
						:modelValue="section.fields || []"
						:read_only="readOnly"
						:hideLabel="true"
						@update:modelValue="updateSectionFields(section, $event)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import MultiSelectList from "../../../../controls/MultiSelectList.vue";
import { useMetaStore } from "../../../../stores/useMetaStore";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	childTableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);
const metaStore = useMetaStore();

const localSections = ref(normalizeSections(props.modelValue));

function normalizeSections(list) {
	if (!Array.isArray(list)) return [];
	return list.map((item) => ({
		id: item.id || "child-" + Math.random().toString(36).substring(2, 8),
		child_field: item.child_field || "",
		fields: Array.isArray(item.fields) ? [...item.fields] : [],
	}));
}

function getChildFieldOptions(childFieldName) {
	const match = props.childTableOptions.find((ct) => ct.value === childFieldName);
	if (!match || !match.child_doctype) return [];
	return metaStore.get_fields_for_doctype(match.child_doctype, {
		alias: "",
		valueMode: "fieldname",
	});
}

function onChildFieldChange(section) {
	section.fields = ["name"];
	emitUpdate();
}

function updateSectionFields(section, newFields) {
	section.fields = Array.isArray(newFields) ? [...newFields] : [];
	emitUpdate();
}

function addChildSection() {
	if (props.readOnly) return;
	const firstUnselected = props.childTableOptions.find(
		(ct) => !localSections.value.some((s) => s.child_field === ct.value)
	);
	const childField = firstUnselected ? firstUnselected.value : "";
	localSections.value.push({
		id: "child-" + Date.now() + "-" + Math.random().toString(36).substring(2, 6),
		child_field: childField,
		fields: childField ? ["name"] : [],
	});
	emitUpdate();
}

function removeSection(index) {
	if (props.readOnly) return;
	localSections.value.splice(index, 1);
	emitUpdate();
}

function emitUpdate() {
	emit("update:modelValue", localSections.value);
}

watch(
	() => props.modelValue,
	(val) => {
		if (JSON.stringify(val) === JSON.stringify(localSections.value)) return;
		localSections.value = normalizeSections(val);
	},
	{ deep: true }
);
</script>

<style scoped>
.embedded-child-editor {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.editor-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--spacing-md);
}

.section-description {
	margin: 2px 0 0;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
}

.child-sections {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.child-section-card {
	background: var(--fxr-bg-subtle, #f8fafc);
	border: 1px solid var(--fxr-border-color, #e2e8f0);
	border-radius: 6px;
	padding: var(--spacing-sm) var(--spacing-md);
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.section-top-row {
	display: flex;
	align-items: flex-end;
	gap: var(--spacing-md);
}

.ctrl-label {
	display: block;
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text-muted);
	margin-bottom: 2px;
}

.remove-section-btn {
	padding: 0;
	height: 30px;
	line-height: 30px;
}

.flex-1 {
	flex: 1;
}
</style>
