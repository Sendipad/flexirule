<template>
	<Teleport to="body">
		<div
			v-if="modelValue"
			ref="dropdownRef"
			class="shortcuts-popover fxr-popover"
			:style="popoverStyle"
			@keydown.esc="$emit('update:modelValue', false)"
		>
			<header class="popover-header">
				<h5><i class="fa fa-keyboard-o"></i> {{ __("Keyboard Shortcuts") }}</h5>
			</header>
			<div class="popover-body v2-scrollbar">
				<div class="shortcut-section">
					<h6>{{ __("General") }}</h6>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Save Rule") }}</span>
						<span class="shortcut-keys"><kbd>Ctrl</kbd> <kbd>S</kbd></span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Undo") }}</span>
						<span class="shortcut-keys"><kbd>Ctrl</kbd> <kbd>Z</kbd></span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Redo") }}</span>
						<span class="shortcut-keys"
							><kbd>Ctrl</kbd> <kbd>Shift</kbd> <kbd>Z</kbd></span
						>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Copy / Paste Nodes") }}</span>
						<span class="shortcut-keys"
							><kbd>Ctrl</kbd> <kbd>C</kbd> / <kbd>V</kbd></span
						>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Toggle Shortcuts") }}</span>
						<span class="shortcut-keys"><kbd>Shift</kbd> <kbd>?</kbd></span>
					</div>
				</div>

				<div class="shortcut-section">
					<h6>{{ __("Canvas") }}</h6>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Pan canvas") }}</span>
						<span class="shortcut-keys"><kbd>Space</kbd> (hold)</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Toggle pan mode") }}</span>
						<span class="shortcut-keys"><kbd>P</kbd></span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Inspect Field") }}</span>
						<span class="shortcut-keys"><kbd>Alt</kbd> (hold)</span>
					</div>
				</div>

				<div class="shortcut-section">
					<h6>{{ __("Navigation") }}</h6>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Focus Variables") }}</span>
						<span class="shortcut-keys"><kbd>Alt</kbd> <kbd>1</kbd></span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Focus Config") }}</span>
						<span class="shortcut-keys"><kbd>Alt</kbd> <kbd>2</kbd></span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-keys"><kbd>Ctrl</kbd> <kbd>Arrows</kbd></span>
						<span class="shortcut-desc">{{ __("Prev / Next Action") }}</span>
					</div>
					<div class="shortcut-item">
						<span class="shortcut-desc">{{ __("Close Dialog") }}</span>
						<span class="shortcut-keys"><kbd>Esc</kbd></span>
					</div>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";

const props = defineProps({
	modelValue: Boolean,
	triggerEl: Object, // The element to anchor the popover to
});

const emit = defineEmits(["update:modelValue"]);

const dropdownRef = ref(null);
const popoverStyle = ref({});

function updatePosition() {
	if (!props.triggerEl || !props.modelValue) return;

	const rect = props.triggerEl.getBoundingClientRect();
	const width = 320;
	const offset = 8;
	const viewportPadding = 12;

	let left = rect.right - width;
	if (left < viewportPadding) left = viewportPadding;

	let top = rect.bottom + offset;
	if (top + 400 > window.innerHeight) {
		top = rect.top - 400 - offset;
	}

	popoverStyle.value = {
		position: "fixed",
		top: `${top}px`,
		left: `${left}px`,
		width: `${width}px`,
		zIndex: 20000,
	};
}

function handleOutsideClick(event) {
	if (
		props.modelValue &&
		dropdownRef.value &&
		!dropdownRef.value.contains(event.target) &&
		!props.triggerEl.contains(event.target)
	) {
		emit("update:modelValue", false);
	}
}

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			nextTick(updatePosition);
			window.addEventListener("mousedown", handleOutsideClick, true);
			window.addEventListener("scroll", updatePosition, true);
			window.addEventListener("resize", updatePosition);
		} else {
			window.removeEventListener("mousedown", handleOutsideClick, true);
			window.removeEventListener("scroll", updatePosition, true);
			window.removeEventListener("resize", updatePosition);
		}
	}
);

onUnmounted(() => {
	window.removeEventListener("mousedown", handleOutsideClick, true);
	window.removeEventListener("scroll", updatePosition, true);
	window.removeEventListener("resize", updatePosition);
});
</script>

<style scoped>
.shortcuts-popover {
	background: var(--fr-bg-surface, #fff);
	border: 1px solid var(--fr-border, #e2e8f0);
	border-radius: var(--fr-radius-xl, 12px);
	box-shadow: var(--fr-shadow-lg, 0 10px 25px rgba(0, 0, 0, 0.1));
	display: flex;
	flex-direction: column;
	overflow: hidden;
	max-height: 500px;
}

.popover-header {
	padding: 12px 16px;
	border-bottom: 1px solid var(--fr-border, #e2e8f0);
	background: var(--fr-bg-muted, #f8fafc);
}

.popover-header h5 {
	margin: 0;
	font-size: 13px;
	font-weight: 600;
	color: var(--fr-text, #1e293b);
	display: flex;
	align-items: center;
	gap: 8px;
}

.popover-body {
	padding: 16px;
	overflow-y: auto;
}

.shortcut-section {
	margin-bottom: 16px;
}

.shortcut-section:last-child {
	margin-bottom: 0;
}

.shortcut-section h6 {
	font-size: 10px;
	text-transform: uppercase;
	color: var(--fr-text-muted, #94a3b8);
	margin-bottom: 8px;
	letter-spacing: 0.05em;
	font-weight: 700;
}

.shortcut-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 6px;
	font-size: 12px;
}

.shortcut-desc {
	color: var(--fr-text-secondary, #475569);
}

.shortcut-keys {
	display: flex;
	gap: 4px;
	align-items: center;
}

kbd {
	background: var(--fr-gray-100, #f1f5f9);
	border: 1px solid var(--fr-gray-300, #cbd5e1);
	border-radius: 4px;
	padding: 1px 5px;
	font-size: 10px;
	font-family: var(--fxr-font-mono, monospace);
	color: var(--fr-gray-700, #374151);
	box-shadow: 0 1px 0 rgba(0, 0, 0, 0.1);
	min-width: 20px;
	text-align: center;
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background: var(--fr-gray-300, #cbd5e1);
	border-radius: 10px;
}
</style>
