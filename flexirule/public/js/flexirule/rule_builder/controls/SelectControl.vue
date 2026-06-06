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

const isFloating = computed(() => {
	return isFocused.value || hasValue.value;
});

const labelText = computed(() => {
	const baseLabel = props.df?.label ? __(props.df.label) : "";
	if (isFloating.value || !baseLabel) {
		return baseLabel;
	}
	return __("Select {0}", [baseLabel]);
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
				'has-floating-label': df?.label && !no_label && !hideLabel,
				'has-value': hasValue,
				'is-focused': isFocused,
			}"
		>
			<label
				v-if="df?.label && !no_label && !hideLabel"
				class="fxr-label"
				:class="{ reqd: df.reqd }"
			>
				{{ labelText }}
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
						{{ isFloating ? __("Select...") : "" }}
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

/* Ensure the floating label transitions smoothly when text changes */
.fxr-label {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	max-width: calc(100% - 40px);
	transition: all var(--fxr-transition-slow, 0.3s) ease;
}

/* When floating, we want to ensure the background covers any potential text behind it */
.has-floating-label.has-value .fxr-label,
.has-floating-label.is-focused .fxr-label {
	background: var(--fxr-bg-card, #ffffff);
	padding: 0 4px;
}
</style>
