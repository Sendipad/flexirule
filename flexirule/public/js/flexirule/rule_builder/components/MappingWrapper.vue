<template>
	<div class="mapping-wrapper" :class="{ 'is-mapped': isMapped }">
		<div class="mapping-header d-flex justify-content-between align-items-center mb-1">
			<label class="control-label mb-0">
				{{ label }}
				<span v-if="reqd" class="text-danger">*</span>
			</label>
			<div class="mode-switcher-container">
				<div class="mode-switcher">
					<button
						type="button"
						class="mode-btn"
						:class="{ active: !isMapped }"
						@click="setMode(false)"
						:title="__('Static Value')"
					>
						<i class="fa fa-font"></i>
						<span class="mode-text">{{ __("Static") }}</span>
					</button>
					<button
						type="button"
						class="mode-btn"
						:class="{ active: isMapped }"
						@click="setMode(true)"
						:title="__('Field Reference')"
					>
						<i class="fa fa-link"></i>
						<span class="mode-text">{{ __("Field") }}</span>
					</button>
				</div>
			</div>
		</div>

		<div class="mapping-input-container">
			<transition name="fade-slide" mode="out-in">
				<div v-if="isMapped" :key="'mapped'" class="mapped-input">
					<ContextPicker
						:modelValue="mappingValue"
						:docFields="docFields"
						@update:modelValue="$emit('update:mappingValue', $event)"
					/>
					<div class="mapping-hint text-primary mt-1">
						<i class="fa fa-link"></i> {{ __("Linked to field") }}
					</div>
				</div>
				<div v-else :key="'static'" class="static-input">
					<slot></slot>
				</div>
			</transition>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import ContextPicker from "./ContextPicker.vue";

const props = defineProps({
	label: String,
	reqd: [Boolean, Number],
	mappingValue: String,
	docFields: Array,
});

const emit = defineEmits(["update:modelValue", "clearStatic"]);

const isMapped = ref(false);

watch(
	() => props.mappingValue,
	(val) => {
		if (val) isMapped.value = true;
	},
	{ immediate: true }
);

function setMode(mapped) {
	if (isMapped.value === mapped) return;

	isMapped.value = mapped;

	if (isMapped.value) {
		// Switched to Field mode: Clear static value in parent
		emit("clearStatic");
	} else {
		// Switched to Static: Clear mapping value
		emit("update:mappingValue", undefined);
	}
}
</script>

<style scoped>
.mapping-wrapper {
	transition: all 0.2s ease;
}

.control-label {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted);
	text-transform: uppercase;
	letter-spacing: 0.5px;
}

.mode-switcher-container {
	display: flex;
	background: #f1f5f9;
	padding: 2px;
	border-radius: 6px;
}

.mode-switcher {
	display: flex;
	gap: 2px;
}

.mode-btn {
	border: none;
	background: transparent;
	padding: 2px 8px;
	border-radius: 4px;
	font-size: 10px;
	font-weight: 600;
	color: #64748b;
	display: flex;
	align-items: center;
	gap: 4px;
	transition: all 0.2s;
	cursor: pointer;
	outline: none !important;
}

.mode-btn i {
	font-size: 10px;
}

.mode-btn.active {
	background: white;
	color: var(--primary);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.mode-btn:hover:not(.active) {
	background: #e2e8f0;
}

.mode-text {
	display: inline;
}

.mapping-hint {
	font-size: 10px;
	font-weight: 500;
	display: flex;
	align-items: center;
	gap: 4px;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
	transition: all 0.2s ease;
}

.fade-slide-enter-from {
	opacity: 0;
	transform: translateY(4px);
}

.fade-slide-leave-to {
	opacity: 0;
	transform: translateY(-4px);
}

@media (max-width: 1200px) {
	.mode-text {
		display: none;
	}
	.mode-btn {
		padding: 2px 6px;
	}
}
</style>
