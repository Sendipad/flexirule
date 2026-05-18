<template>
	<div class="schema-renderer">
		<div v-for="field in visibleFields" :key="field.fieldname" class="schema-field-wrapper">
			<!-- Section Break -->
			<div v-if="field.fieldtype === 'Section Break'" class="section-break">
				<h5 v-if="field.label">{{ field.label }}</h5>
				<hr />
			</div>

			<!-- Column Break (Simplified) -->
			<div v-else-if="field.fieldtype === 'Column Break'" class="column-break"></div>

			<!-- Use ControlFactory for standard fields -->
			<div
				v-else
				class="form-group"
				:class="{
					'has-error':
						getFieldState(field, props.row ? props.row.name : 'root').reqd &&
						!getValue(field),
				}"
			>
				<ControlFactory
					:df="
						getNormalizedDf(field, props.row ? props.row.name : 'root', props.readOnly)
					"
					:modelValue="getValue(field)"
					:doc="engine._get_context(row).doc"
					:engine="engine"
					@update:modelValue="updateValue(field, $event)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import ControlFactory from "../../controls/ControlFactory.vue";
import { useFieldNormalization } from "../../composables/useFieldNormalization";

const props = defineProps({
	fields: { type: Array, default: () => [] },
	engine: { type: Object, required: true },
	readOnly: { type: Boolean, default: false },
	row: { type: Object, default: null }, // If rendering for a child table row
});

const { getNormalizedDf, getFieldState } = useFieldNormalization(props.engine);

const visibleFields = computed(() => {
	return props.fields.filter(
		(f) => !getFieldState(f, props.row ? props.row.name : "root").hidden
	);
});

function getValue(field) {
	const target = props.row || props.engine.config;
	return target[field.fieldname];
}

function updateValue(field, value) {
	props.engine.handleFieldChange(field.fieldname, value, props.row);
}
</script>

<style scoped>
.schema-renderer {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3, 8px);
	padding: 0 4px;
}

.section-break {
	margin-top: 16px;
	margin-bottom: 4px;
}

.section-break h5 {
	margin: 0 0 8px 0;
	font-size: 14px;
	font-weight: 700;
	color: var(--text-color);
}

.has-error :deep(.form-control) {
	border-color: var(--red-500, #ef4444);
}
</style>
