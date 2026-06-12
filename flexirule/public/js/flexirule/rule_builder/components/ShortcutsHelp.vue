<template>
	<Teleport to="body">
		<transition name="shortcuts-popover">
			<div
				v-if="modelValue"
				ref="popoverRef"
				class="shortcuts-help-popover fxr-headless-popover"
				:style="popoverStyle"
				role="dialog"
				aria-labelledby="shortcuts-help-title"
				@keydown.esc.prevent="close"
			>
				<header class="shortcuts-help-header">
					<div class="shortcuts-help-title">
						<i class="fa fa-keyboard-o"></i>
						<div>
							<h5 id="shortcuts-help-title">{{ __("Keyboard Shortcuts") }}</h5>
							<p>{{ __("Quick actions for the builder canvas and panels") }}</p>
						</div>
					</div>
					<button class="popover-close" @click="close" :title="__('Close')">
						<i class="fa fa-times"></i>
					</button>
				</header>

				<div class="shortcuts-help-body v2-scrollbar">
					<section
						v-for="group in shortcutGroups"
						:key="group.label"
						class="shortcut-group"
					>
						<div class="shortcut-group-heading">{{ group.label }}</div>
						<div class="shortcut-item" v-for="item in group.items" :key="item.label">
							<span class="shortcut-keys">
								<kbd v-for="key in item.keys" :key="key">{{ key }}</kbd>
							</span>
							<span class="shortcut-desc">{{ item.label }}</span>
						</div>
					</section>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, watch, ref } from "vue";

const props = defineProps({
	modelValue: Boolean,
});

const emit = defineEmits(["update:modelValue"]);
const popoverRef = ref(null);

const shortcutGroups = [
	{
		label: __("General"),
		items: [
			{ keys: ["Ctrl", "S"], label: __("Save Rule") },
			{ keys: ["Ctrl", "Z"], label: __("Undo") },
			{ keys: ["Ctrl", "Y"], label: __("Redo") },
			{ keys: ["Ctrl", "Shift", "Z"], label: __("Redo") },
			{ keys: ["Shift", "?"], label: __("Toggle this help") },
		],
	},
	{
		label: __("Canvas"),
		items: [
			{ keys: ["Space"], label: __("Pan canvas") },
			{ keys: ["P"], label: __("Toggle pan mode") },
			{ keys: ["Alt"], label: __("Show field names") },
			{ keys: ["Alt", "Click"], label: __("Copy field name") },
		],
	},
	{
		label: __("Navigation"),
		items: [
			{ keys: ["Alt", "1"], label: __("Focus Variables / Sidebar") },
			{ keys: ["Alt", "2"], label: __("Focus Configuration") },
			{ keys: ["Alt", "3"], label: __("Toggle Settings Bar") },
			{ keys: ["Ctrl", "Arrows"], label: __("Previous / Next Action") },
			{ keys: ["Esc"], label: __("Close dialogs") },
		],
	},
];

const popoverStyle = computed(() => ({
	top: `calc(var(--navbar-height, 44px) + var(--page-head-height, 44px) + 12px)`,
	right: "16px",
}));

function close() {
	emit("update:modelValue", false);
}

function onWindowMouseDown(event) {
	if (!props.modelValue) return;
	if (popoverRef.value && !popoverRef.value.contains(event.target)) {
		close();
	}
}

function onWindowKeydown(event) {
	if (event.key === "Escape" && props.modelValue) {
		close();
	}
}

watch(
	() => props.modelValue,
	(visible) => {
		if (visible) {
			window.addEventListener("mousedown", onWindowMouseDown, true);
			window.addEventListener("keydown", onWindowKeydown, true);
		} else {
			window.removeEventListener("mousedown", onWindowMouseDown, true);
			window.removeEventListener("keydown", onWindowKeydown, true);
		}
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	window.removeEventListener("mousedown", onWindowMouseDown, true);
	window.removeEventListener("keydown", onWindowKeydown, true);
});
</script>

<style scoped>
.shortcuts-help-popover {
	position: fixed;
	z-index: 13000;
	width: min(420px, calc(100vw - 24px));
	max-height: min(70vh, 620px);
	border-radius: var(--fxr-radius-lg);
	border: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface-elevated);
	box-shadow: var(--fxr-shadow-lg);
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.shortcuts-help-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 12px;
	padding: 14px 16px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface-2);
}

.shortcuts-help-title {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	min-width: 0;
}

.shortcuts-help-title i {
	width: 28px;
	height: 28px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 8px;
	background: var(--fxr-accent-soft);
	color: var(--fxr-accent);
	flex: 0 0 auto;
}

.shortcuts-help-title h5 {
	margin: 0;
	font-size: 14px;
	font-weight: 700;
	color: var(--fxr-text-strong);
}

.shortcuts-help-title p {
	margin: 2px 0 0;
	font-size: 11px;
	color: var(--fxr-text-soft);
}

.popover-close {
	width: 30px;
	height: 30px;
	border: none;
	border-radius: 8px;
	background: transparent;
	color: var(--fxr-text-soft);
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
}

.popover-close:hover {
	background-color: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
}

.shortcuts-help-body {
	padding: 10px 12px 12px;
	overflow: auto;
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.shortcut-group {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 10px 10px 8px;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
	background: var(--fxr-surface-soft);
}

.shortcut-group-heading {
	font-size: 10px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--fxr-text-soft);
}

.shortcut-item {
	display: grid;
	grid-template-columns: minmax(126px, auto) minmax(0, 1fr);
	align-items: center;
	gap: 10px;
	padding: 7px 8px;
	border-radius: 10px;
	background-color: var(--fxr-surface-soft);
}

.shortcut-keys {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
}

kbd {
	border: 1px solid var(--fxr-border-subtle);
	border-bottom-color: var(--fxr-border-strong);
	border-radius: 6px;
	padding: 2px 6px;
	font-size: 10px;
	line-height: 1.3;
	font-family: inherit;
	background: var(--fxr-surface-elevated);
	color: var(--fxr-text-strong);
	box-shadow: var(--fxr-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.04));
}

.shortcut-desc {
	font-size: 12px;
	color: var(--fxr-text-strong);
}

.shortcuts-popover-enter-active,
.shortcuts-popover-leave-active {
	transition:
		opacity 0.14s ease,
		transform 0.14s ease;
}

.shortcuts-popover-enter-from,
.shortcuts-popover-leave-to {
	opacity: 0;
	transform: translateY(-6px) scale(0.98);
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}

.v2-scrollbar::-webkit-scrollbar-thumb {
	background: color-mix(in srgb, var(--fxr-text-soft, #64748b) 28%, var(--fxr-surface));
	border-radius: 999px;
}

@media (max-width: 640px) {
	.shortcuts-help-popover {
		left: 12px;
		right: 12px;
		width: auto;
	}

	.shortcut-item {
		grid-template-columns: 1fr;
	}
}
</style>
