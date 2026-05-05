<!--
  SelectControl - Simple native select for reliability
-->
<script setup>
import { computed } from "vue";
const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	no_label: Boolean,
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const options = computed(() => {
	let opts = props.df?.options;

	if (!opts) return [];

	// String options (newline separated)
	if (typeof opts === "string") {
		return opts
			.split("\n")
			.filter(Boolean)
			.map((opt) => ({
				label: __(opt.trim()),
				value: opt.trim(),
			}));
	}

	// Array of strings
	if (Array.isArray(opts) && opts.length && typeof opts[0] === "string") {
		return opts.map((opt) => ({
			label: __(opt),
			value: opt,
		}));
	}

	// Array of objects with label/value
	if (Array.isArray(opts)) {
		return opts.map((opt) => ({
			label: __(opt.label || opt.value),
			value: opt.value,
		}));
	}

	return [];
});

function on_change(event) {
	emit("update:modelValue", event.target.value);
}
</script>

<template>
	<div class="fr-control">
		<div
			v-if="df?.label && !no_label && !hideLabel"
			class="fr-label"
			:class="{ reqd: df.reqd }"
		>
			{{ __(df.label) }}
		</div>
		<div class="select-wrapper">
			<select
				class="fr-select"
				:value="modelValue"
				:disabled="read_only || df?.read_only"
				@change="on_change"
			>
				<option v-if="!df?.reqd" value="">{{ __("Select...") }}</option>
				<option v-for="opt in options" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
		</div>
		<div v-if="df?.description && !hideDescription" class="fr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
.select-wrapper {
	position: relative;
	width: 100%;
}

.select-wrapper select {
	width: 100%;
}
</style>
