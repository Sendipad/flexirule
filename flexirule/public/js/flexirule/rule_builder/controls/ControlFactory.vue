<template>
	<component
		:is="resolved.component"
		v-bind="resolved.props"
		:df="df"
		:modelValue="modelValue"
		:read_only="df?.read_only"
		:hideLabel="hideLabel"
		:hideDescription="hideDescription"
		@update:modelValue="$emit('update:modelValue', $event)"
	/>
</template>

<script setup>
import { computed, onMounted, watch, inject } from "vue";
import { ControlRegistry } from "../../core/control_registry.js";

const injectedVariableOptions = inject("variableOptions", null);
const injectedDocFields = inject("docFields", null);

const props = defineProps({
	df: Object,
	modelValue: [String, Number, Boolean, Array, Object],
	doc: { type: Object, default: null },
	options: { type: Array, default: null },
	engine: { type: Object, default: null },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
	get_options: { type: Function, default: null },
	get_data: { type: Function, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const resolved = computed(() => {
	const registryContext = {
		...props,
		injectedVariableOptions,
		injectedDocFields,
	};
	return ControlRegistry.resolve(props.df, registryContext);
});

onMounted(() => {
	check_default();
});

watch(
	() => props.df?.default,
	() => {
		check_default();
	}
);

function check_default() {
	if (props.modelValue === undefined || props.modelValue === null || props.modelValue === "") {
		if (props.df?.default !== undefined && props.df?.default !== null) {
			emit("update:modelValue", props.df.default);
		}
	}
}
</script>
