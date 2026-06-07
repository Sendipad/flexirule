<!--
  SelectControl - Simple native select for reliability
-->
<script setup>
import { computed, ref } from "vue";
const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	no_label: Boolean,
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const isFocused = ref(false);

const hasValue = computed(() => {
	return props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "";
});

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
	<div class="fxr-control">
		<div
			class="fxr-input-group"
			:class="{
				'has-value': hasValue,
				'is-focused': isFocused,
			}"
		>
			<label
				v-if="df?.label && !no_label && !hideLabel"
				class="fxr-label"
				:class="{ reqd: df.reqd }"
			>
				{{ __(df.label) }}
			</label>
			<div class="select-wrapper">
				<select
					class="fxr-select"
					:value="modelValue"
					:disabled="read_only || df?.read_only"
					@change="on_change"
					@focus="isFocused = true"
					@blur="isFocused = false"
				>
					<option v-if="!df?.reqd" value="">
						{{ __("Select...") }}
					</option>
					<option v-for="opt in options" :key="opt.value" :value="opt.value">
						{{ opt.label }}
					</option>
				</select>
			</div>
		</div>
		<div v-if="df?.description && !hideDescription" class="fxr-description">
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

.fxr-label {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	max-width: 100%;
}
</style>
