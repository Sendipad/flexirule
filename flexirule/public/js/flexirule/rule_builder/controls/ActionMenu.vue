<template>
	<Menu as="div" class="fxr-action-menu" v-slot="{ open }">
		<MenuButton
			ref="buttonRef"
			type="button"
			class="fxr-action-menu__trigger"
			:class="[triggerClass, { 'is-open': open }]"
			:title="title || __('More actions')"
			:aria-label="ariaLabel || title || __('More actions')"
			:disabled="disabled"
			@click.stop
			@pointerdown.stop
		>
			<slot name="trigger" :open="open">
				<i class="fa fa-ellipsis-v" aria-hidden="true"></i>
			</slot>
		</MenuButton>

		<Teleport to="body">
			<MenuItems
				v-if="open"
				ref="itemsRef"
				class="fxr-action-menu__items"
				:class="menuClass"
				:style="floatingStyles"
				static
				@click.stop
				@pointerdown.stop
			>
				<template
					v-for="(item, idx) in items"
					:key="item.id || item.action || `item-${idx}`"
				>
					<div v-if="item.divider" class="fxr-action-menu__divider" role="separator" />
					<MenuItem
						v-else
						:disabled="Boolean(item.disabled)"
						v-slot="{ active, disabled: itemDisabled }"
					>
						<button
							type="button"
							class="fxr-action-menu__item"
							:class="[
								item.class,
								{
									'is-active': active,
									'is-disabled': itemDisabled,
									'is-danger': item.danger,
								},
							]"
							:disabled="itemDisabled"
							:title="item.title || item.label"
							:aria-label="item.ariaLabel || item.title || item.label"
							@click="handleItemClick(item, $event)"
						>
							<i
								v-if="item.icon"
								class="fxr-action-menu__item-icon"
								:class="item.icon"
								aria-hidden="true"
							></i>
							<span class="fxr-action-menu__item-label">{{ item.label }}</span>
							<kbd v-if="item.shortcut" class="fxr-action-menu__item-shortcut">
								{{ item.shortcut }}
							</kbd>
						</button>
					</MenuItem>
				</template>
			</MenuItems>
		</Teleport>
	</Menu>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";
import { autoUpdate, computePosition, flip, offset, shift } from "@floating-ui/dom";

const props = defineProps({
	items: {
		type: Array,
		default: () => [],
	},
	title: {
		type: String,
		default: "",
	},
	ariaLabel: {
		type: String,
		default: "",
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	triggerClass: {
		type: [String, Object, Array],
		default: "",
	},
	menuClass: {
		type: [String, Object, Array],
		default: "",
	},
	placement: {
		type: String,
		default: "bottom-end",
	},
	offsetDistance: {
		type: Number,
		default: 4,
	},
});

const emit = defineEmits(["action", "select"]);

const buttonRef = ref(null);
const itemsRef = ref(null);
const floatingStyles = ref({
	position: "fixed",
	top: "0px",
	left: "0px",
});

let cleanupAutoUpdate = null;

function resolveDOMElement(target) {
	if (!target) return null;
	if (target instanceof Element) return target;
	if (target.$el instanceof Element) return target.$el;
	return null;
}

function updatePosition() {
	const triggerEl = resolveDOMElement(buttonRef.value);
	const menuEl = resolveDOMElement(itemsRef.value);

	if (!triggerEl || !menuEl) return;
	if (!triggerEl.isConnected) return;

	computePosition(triggerEl, menuEl, {
		placement: props.placement,
		strategy: "fixed",
		middleware: [
			offset(props.offsetDistance),
			flip({ fallbackPlacements: ["top-end", "bottom-start", "top-start"] }),
			shift({ padding: 8 }),
		],
	}).then(({ x, y }) => {
		floatingStyles.value = {
			position: "fixed",
			left: `${Math.round(x)}px`,
			top: `${Math.round(y)}px`,
		};
	});
}

function startPositionTracking() {
	stopPositionTracking();
	nextTick(() => {
		const triggerEl = resolveDOMElement(buttonRef.value);
		const menuEl = resolveDOMElement(itemsRef.value);
		if (triggerEl && menuEl) {
			cleanupAutoUpdate = autoUpdate(triggerEl, menuEl, updatePosition, {
				animationFrame: true,
			});
		}
	});
}

function stopPositionTracking() {
	if (typeof cleanupAutoUpdate === "function") {
		cleanupAutoUpdate();
		cleanupAutoUpdate = null;
	}
}

watch(itemsRef, (newVal) => {
	if (newVal) {
		startPositionTracking();
	} else {
		stopPositionTracking();
	}
});

onBeforeUnmount(() => {
	stopPositionTracking();
});

function handleItemClick(item, event) {
	if (item.disabled || props.disabled) {
		event.preventDefault();
		event.stopPropagation();
		return;
	}

	if (typeof item.handler === "function") {
		item.handler(event);
	}
	if (item.action) {
		emit("action", item.action, item);
	}
	emit("select", item);
}
</script>

<style scoped>
.fxr-action-menu {
	position: relative;
	display: inline-flex;
	align-items: center;
	line-height: 1;
}

.fxr-action-menu__trigger {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 25px;
	height: 25px;
	min-height: 25px;
	padding: 0;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text-secondary, #4b5563);
	font: inherit;
	font-size: var(--fxr-text-xs, 12px);
	cursor: pointer;
	user-select: none;
	transition:
		background-color var(--fxr-transition-fast, 120ms ease),
		border-color var(--fxr-transition-fast, 120ms ease),
		color var(--fxr-transition-fast, 120ms ease);
}

.fxr-action-menu__trigger:hover:not(:disabled),
.fxr-action-menu__trigger.is-open {
	border-color: var(--fxr-border, #d1d5db);
	background: var(--fxr-surface-soft, #f3f4f6);
	color: var(--fxr-text, #111827);
}

.fxr-action-menu__trigger:focus-visible {
	outline: 2px solid var(--fxr-border-focus, #3b82f6);
	outline-offset: 1px;
}

.fxr-action-menu__trigger:disabled {
	opacity: 0.4;
	cursor: not-allowed;
}

.fxr-action-menu__items {
	box-sizing: border-box;
	z-index: 99999;
	min-width: 160px;
	max-width: 280px;
	padding: 4px;
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #ffffff);
	box-shadow:
		0 10px 25px -5px rgba(0, 0, 0, 0.1),
		0 8px 10px -6px rgba(0, 0, 0, 0.1);
	outline: none;
	font-family: var(--fxr-font-family, inherit);
}

.fxr-action-menu__divider {
	height: 1px;
	margin: 4px -4px;
	background: var(--fxr-border-subtle, #e5e7eb);
}

.fxr-action-menu__item {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	min-height: 28px;
	padding: 5px 8px;
	border: 0;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text, #1f2937);
	font: inherit;
	font-size: var(--fxr-text-xs, 12px);
	font-weight: var(--fxr-weight-normal, 400);
	line-height: 1.25;
	text-align: left;
	cursor: pointer;
	user-select: none;
	white-space: nowrap;
	transition:
		background-color var(--fxr-transition-fast, 120ms ease),
		color var(--fxr-transition-fast, 120ms ease);
}

.fxr-action-menu__item.is-active:not(.is-disabled) {
	background: var(--fxr-surface-soft, #f3f4f6);
	color: var(--fxr-text-strong, #111827);
}

.fxr-action-menu__item.is-danger {
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-action-menu__item.is-danger.is-active:not(.is-disabled) {
	background: var(--fxr-surface-danger, #fef2f2);
	color: var(--fxr-text-danger, #b91c1c);
}

.fxr-action-menu__item.is-disabled {
	opacity: 0.45;
	cursor: not-allowed;
}

.fxr-action-menu__item:focus-visible {
	outline: 2px solid var(--fxr-border-focus, #3b82f6);
	outline-offset: -1px;
}

.fxr-action-menu__item-icon {
	flex: 0 0 14px;
	width: 14px;
	text-align: center;
	font-size: 11px;
	opacity: 0.85;
}

.fxr-action-menu__item-label {
	flex: 1 1 auto;
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
}

.fxr-action-menu__item-shortcut {
	flex: 0 0 auto;
	margin-left: auto;
	padding: 1px 4px;
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
	border-radius: var(--fxr-radius-sm, 3px);
	background: var(--fxr-surface-soft, #f9fafb);
	color: var(--fxr-text-muted, #6b7280);
	font-family: inherit;
	font-size: 10px;
	line-height: 1;
}
</style>
