<template>
	<LookupResolver v-bind="$props" />
</template>

<script setup>
import LookupResolver from "./LookupResolver.vue";

defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
	variableOptions: Array,
	context: Object,
});
</script>
