<template>
	<div class="context-picker">
		<input
			type="text"
			class="form-control form-control-sm"
			:value="modelValue"
			@input="$emit('update:modelValue', $event.target.value)"
			@dragover.prevent
			@drop="onDrop"
			list="context-vars-list"
			:placeholder="`${context.alias}.field`"
		/>
		<datalist id="context-vars-list">
			<option v-for="opt in suggestions" :key="opt.value" :value="opt.value">
				{{ opt.label || opt.value }}
			</option>
		</datalist>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from "vue";
import { useStore } from "../stores";

const props = defineProps({
	modelValue: String,
	docFields: Array,
});
const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const context = inject("conditionContext", { alias: "doc" });

const metaFields = ref([]);

function onDrop(event) {
	const variable = event.dataTransfer.getData("application/x-flexirule-variable");
	if (variable) {
		event.preventDefault();
		emit("update:modelValue", variable);
	}
}

// Common variables that are always available
const commonVars = [
	{ value: "vars.previous_result", label: "Previous Result" },
	{ value: "vars.parent_doc", label: "Parent Document" },
];

const suggestions = computed(() => {
	// 1. If docFields provided, use them (this will include row.* fields)
	if (props.docFields && props.docFields.length > 0) {
		return [...props.docFields, ...commonVars];
	}

	// 2. Fallback to current doc meta
	const docOptions = metaFields.value.map((f) => ({
		value: `doc.${f.fieldname}`,
		label: `doc.${f.fieldname} (${f.label})`,
	}));

	return [...docOptions, ...commonVars];
});

onMounted(() => {
	if (!props.docFields || props.docFields.length === 0) {
		fetchMeta();
	}
});

function fetchMeta() {
	const doctype = store.rule_doc?.document_type;
	if (!doctype) return;

	frappe.model.with_doctype(doctype, () => {
		const meta = frappe.get_meta(doctype);
		metaFields.value = meta.fields || [];
	});
}
</script>

<style scoped>
.context-picker input {
	font-family: monospace;
	color: var(--primary);
	background-color: var(--bg-light-gray);
}
</style>
