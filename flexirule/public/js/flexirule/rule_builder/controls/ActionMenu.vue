<template>
	<Menu as="div" class="fxr-action-menu" :class="{ 'is-open': isOpen }">
		<MenuButton
			ref="buttonRef"
			type="button"
			class="fxr-action-menu-trigger"
			:class="[sizeClass]"
			:title="label || __('Actions')"
			:aria-label="label || __('Actions')"
			@pointerdown.stop
			@click.stop="toggleMenu"
			@keydown.stop
		>
			<slot name="trigger">
				<i class="fa fa-ellipsis-v" aria-hidden="true"></i>
			</slot>
		</MenuButton>

		<Teleport to="body" :disabled="!teleport">
			<div
				v-if="isOpen"
				ref="menuWrapperRef"
				class="fxr-action-menu-portal"
				@pointerdown.stop
				@click.stop
				@keydown.stop
			>
				<MenuItems
					static
					class="fxr-action-menu-items"
					:style="menuStyle"
					@keydown="handleMenuItemsKeydown"
				>
					<MenuItem
						v-for="action in actions"
						:key="action.id"
						v-slot="{ active }"
						:disabled="Boolean(action.disabled)"
					>
						<button
							type="button"
							class="fxr-action-menu-item"
							:class="{
								'is-active': active,
								'is-danger': action.danger,
								'is-disabled': action.disabled,
							}"
							:disabled="Boolean(action.disabled)"
							:title="action.title || action.label"
							@click="executeAction(action, $event)"
						>
							<i v-if="action.icon" :class="action.icon" aria-hidden="true"></i>
							<span class="fxr-action-menu-item-label">{{ action.label }}</span>
						</button>
					</MenuItem>
				</MenuItems>
			</div>
		</Teleport>
	</Menu>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";

const props = defineProps({
	actions: {
		type: Array,
		default: () => [],
	},
	label: {
		type: String,
		default: "",
	},
	size: {
		type: String,
		default: "sm",
	},
	teleport: {
		type: Boolean,
		default: true,
	},
	align: {
		type: String,
		default: "right",
	},
});

const emit = defineEmits(["select", "open", "close"]);

const buttonRef = ref(null);
const menuWrapperRef = ref(null);
const isOpen = ref(false);
const menuStyle = ref({});

const sizeClass = computed(() => {
	if (props.size === "xs") return "is-xs";
	if (props.size === "lg") return "is-lg";
	return "is-sm";
});

function resolveButtonElement() {
	if (!buttonRef.value) return null;
	return buttonRef.value.$el || buttonRef.value;
}

function updatePosition() {
	if (!isOpen.value) return;
	const buttonEl = resolveButtonElement();
	if (!buttonEl || !buttonEl.getBoundingClientRect) return;

	const rect = buttonEl.getBoundingClientRect();
	const viewportWidth = window.innerWidth;
	const viewportHeight = window.innerHeight;

	const minWidth = 160;
	const maxWidth = Math.min(260, viewportWidth - 16);
	const offset = 4;
	const padding = 8;

	let left = props.align === "left" ? rect.left : rect.right - minWidth;
	left = Math.max(padding, Math.min(left, viewportWidth - minWidth - padding));

	const spaceBelow = viewportHeight - rect.bottom - offset - padding;
	const spaceAbove = rect.top - offset - padding;
	const openUp = spaceBelow < 180 && spaceAbove > spaceBelow;

	const maxHeight = Math.max(120, Math.min(280, openUp ? spaceAbove : spaceBelow));
	let top = openUp ? rect.top - offset : rect.bottom + offset;

	menuStyle.value = {
		position: "fixed",
		top: openUp ? "auto" : `${top}px`,
		bottom: openUp ? `${viewportHeight - rect.top + offset}px` : "auto",
		left: `${left}px`,
		minWidth: `${minWidth}px`,
		maxWidth: `${maxWidth}px`,
		maxHeight: `${maxHeight}px`,
		zIndex: 99999,
	};
}

function openMenu() {
	if (isOpen.value) return;
	isOpen.value = true;
	emit("open");
	nextTick(() => {
		updatePosition();
		if (typeof window !== "undefined") {
			window.addEventListener("scroll", handleScroll, true);
			window.addEventListener("resize", updatePosition);
			document.addEventListener("pointerdown", handleOutsidePointerDown, true);
		}
	});
}

function closeMenu() {
	if (!isOpen.value) return;
	isOpen.value = false;
	emit("close");
	if (typeof window !== "undefined") {
		window.removeEventListener("scroll", handleScroll, true);
		window.removeEventListener("resize", updatePosition);
		document.removeEventListener("pointerdown", handleOutsidePointerDown, true);
	}
}

function toggleMenu(event) {
	if (event) {
		event.stopPropagation();
		event.preventDefault();
	}
	if (isOpen.value) {
		closeMenu();
	} else {
		openMenu();
	}
}

function handleScroll(e) {
	if (menuWrapperRef.value && menuWrapperRef.value.contains(e.target)) {
		return;
	}
	updatePosition();
}

function handleOutsidePointerDown(e) {
	const buttonEl = resolveButtonElement();
	if (buttonEl && buttonEl.contains(e.target)) return;
	if (menuWrapperRef.value && menuWrapperRef.value.contains(e.target)) return;
	closeMenu();
}

function handleMenuItemsKeydown(e) {
	if (e.key === "Escape") {
		e.stopPropagation();
		e.preventDefault();
		closeMenu();
		const buttonEl = resolveButtonElement();
		buttonEl?.focus?.();
	}
}

function executeAction(action, event) {
	if (event) {
		event.stopPropagation();
		event.preventDefault();
	}
	if (action.disabled) return;
	closeMenu();
	if (typeof action.onClick === "function") {
		action.onClick();
	}
	emit("select", action.id);
	const buttonEl = resolveButtonElement();
	buttonEl?.focus?.();
}

watch(isOpen, (val) => {
	if (!val) {
		if (typeof window !== "undefined") {
			window.removeEventListener("scroll", handleScroll, true);
			window.removeEventListener("resize", updatePosition);
			document.removeEventListener("pointerdown", handleOutsidePointerDown, true);
		}
	}
});

onBeforeUnmount(() => {
	closeMenu();
});

defineExpose({
	openMenu,
	closeMenu,
	toggleMenu,
	isOpen,
});
</script>

<style scoped>
.fxr-action-menu {
	display: inline-flex;
	align-items: center;
	position: relative;
}

.fxr-action-menu-trigger {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	margin: 0;
	padding: 0;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-md, 6px);
	background: transparent;
	color: var(--fxr-text-secondary, #4b5563);
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast, 120ms ease),
		border-color var(--fxr-transition-fast, 120ms ease),
		color var(--fxr-transition-fast, 120ms ease);
}

.fxr-action-menu-trigger.is-xs {
	width: 22px;
	height: 22px;
	font-size: 11px;
}

.fxr-action-menu-trigger.is-sm {
	width: 26px;
	height: 26px;
	font-size: 12px;
}

.fxr-action-menu-trigger.is-lg {
	width: 30px;
	height: 30px;
	font-size: 14px;
}

.fxr-action-menu-trigger:hover,
.fxr-action-menu-trigger:focus-visible,
.fxr-action-menu.is-open .fxr-action-menu-trigger {
	border-color: var(--fxr-border, #d1d5db);
	background: var(--fxr-bg-hover, #f3f4f6);
	color: var(--fxr-text-strong, #111827);
	outline: none;
}

.fxr-action-menu-portal {
	position: fixed;
	inset: 0;
	z-index: 99999;
	pointer-events: none;
}

.fxr-action-menu-items {
	position: fixed;
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding: 4px;
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #ffffff);
	box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06);
	overflow-y: auto;
	pointer-events: auto;
	outline: none;
}

.fxr-action-menu-item {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 6px 10px;
	border: 0;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text, #111827);
	font-size: var(--fxr-text-xs, 12px);
	font-weight: 500;
	text-align: left;
	cursor: pointer;
	transition: background-color 100ms ease, color 100ms ease;
}

.fxr-action-menu-item.is-active {
	background: var(--fxr-bg-hover, #f3f4f6);
	color: var(--fxr-text-strong, #111827);
}

.fxr-action-menu-item.is-danger {
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-action-menu-item.is-danger.is-active {
	background: var(--fxr-bg-danger, #fef2f2);
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-action-menu-item:disabled,
.fxr-action-menu-item.is-disabled {
	opacity: 0.45;
	cursor: not-allowed;
	background: transparent !important;
}

.fxr-action-menu-item-label {
	flex: 1;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
