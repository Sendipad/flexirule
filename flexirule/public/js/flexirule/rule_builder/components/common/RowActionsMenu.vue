<template>
	<div class="fxr-row-actions-menu">
		<button
			ref="triggerRef"
			type="button"
			class="fxr-grid-icon-button fxr-row-actions-menu__trigger"
			:class="{ 'is-active': isOpen }"
			:title="buttonTitle || __('More options') + ' (' + shortcutHint + ')'"
			:aria-label="buttonAriaLabel || __('More options')"
			aria-haspopup="menu"
			:aria-expanded="String(isOpen)"
			:disabled="disabled"
			@click.stop="toggleMenu"
			@keydown="handleTriggerKeydown"
		>
			<i class="fa fa-ellipsis-v" aria-hidden="true"></i>
		</button>

		<Teleport to="body">
			<div
				v-if="isOpen"
				ref="dropdownRef"
				class="fxr-row-actions-menu__dropdown fxr-headless-menu"
				:style="dropdownStyle"
				role="menu"
				:aria-label="__('Row options')"
				tabindex="-1"
				@keydown="handleMenuKeydown"
			>
				<div class="fxr-row-actions-menu__items">
					<template v-for="(item, idx) in visibleActions" :key="item.id || idx">
						<div
							v-if="item.type === 'divider' || item.isDivider"
							class="fxr-row-actions-menu__divider"
							role="separator"
						></div>
						<button
							v-else
							type="button"
							role="menuitem"
							class="fxr-row-actions-menu__item"
							:class="{
								'is-danger': item.isDestructive,
								'is-disabled': !item.isEnabled,
							}"
							:disabled="!item.isEnabled"
							:aria-keyshortcuts="item.shortcut || undefined"
							@click.stop="runAction(item)"
						>
							<i
								v-if="item.icon"
								:class="[item.icon, 'fxr-row-actions-menu__icon']"
								aria-hidden="true"
							></i>
							<span class="fxr-row-actions-menu__label">{{ item.label }}</span>
							<kbd v-if="item.shortcut" class="fxr-row-actions-menu__shortcut">
								{{ item.shortcut }}
							</kbd>
						</button>
					</template>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { useFloatingDropdown } from "../../composables/useFloatingDropdown.js";
import { UNIFIED_SHORTCUTS } from "../../composables/command_action_types.mjs";

const props = defineProps({
	actions: { type: Array, default: () => [] },
	context: { type: Object, default: () => ({}) },
	disabled: Boolean,
	buttonTitle: { type: String, default: "" },
	buttonAriaLabel: { type: String, default: "" },
});

const emit = defineEmits(["action", "open", "close"]);

const shortcutHint = UNIFIED_SHORTCUTS.OPEN_MENU;

const {
	triggerRef,
	dropdownRef,
	isOpen,
	dropdownStyle,
	openDropdown,
	closeDropdown,
	toggleDropdown,
} = useFloatingDropdown({
	matchTriggerWidth: false,
	minWidth: 190,
	maxWidth: 280,
	offset: 4,
	zIndex: 25000,
});

const visibleActions = computed(() => {
	const result = [];
	for (const action of props.actions) {
		if (action.type === "divider" || action.isDivider) {
			result.push(action);
			continue;
		}
		const isVisible =
			typeof action.isVisible === "function" ? action.isVisible(props.context) : true;
		if (isVisible) {
			const isEnabled =
				typeof action.isEnabled === "function" ? action.isEnabled(props.context) : true;
			const label = typeof action.label === "function" ? action.label() : action.label;
			result.push({
				...action,
				label,
				isEnabled,
			});
		}
	}
	// Filter out leading, trailing, or double dividers
	return result.filter((item, index, arr) => {
		if (item.type === "divider" || item.isDivider) {
			if (index === 0 || index === arr.length - 1) return false;
			const prev = arr[index - 1];
			if (prev?.type === "divider" || prev?.isDivider) return false;
		}
		return true;
	});
});

function toggleMenu() {
	if (props.disabled) return;
	if (isOpen.value) {
		close();
	} else {
		open();
	}
}

function open() {
	if (props.disabled) return;
	openDropdown();
	emit("open");
	nextTick(() => {
		const first = dropdownRef.value?.querySelector('[role="menuitem"]:not(:disabled)');
		first?.focus();
	});
	document.addEventListener("pointerdown", handleOutsidePointerDown, true);
}

function close() {
	closeDropdown();
	emit("close");
	document.removeEventListener("pointerdown", handleOutsidePointerDown, true);
}

function handleOutsidePointerDown(event) {
	if (dropdownRef.value?.contains(event.target) || triggerRef.value?.contains(event.target)) {
		return;
	}
	close();
}

function handleTriggerKeydown(event) {
	if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
		event.preventDefault();
		event.stopPropagation();
		open();
	}
}

function handleMenuKeydown(event) {
	if (event.key === "Escape") {
		event.preventDefault();
		event.stopPropagation();
		close();
		nextTick(() => triggerRef.value?.focus());
		return;
	}

	const items = Array.from(
		dropdownRef.value?.querySelectorAll('[role="menuitem"]:not(:disabled)') || []
	);
	if (!items.length) return;
	const currentIndex = items.indexOf(document.activeElement);

	if (event.key === "ArrowDown") {
		event.preventDefault();
		const next = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
		items[next]?.focus();
	} else if (event.key === "ArrowUp") {
		event.preventDefault();
		const prev = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
		items[prev]?.focus();
	} else if (event.key === "Home") {
		event.preventDefault();
		items[0]?.focus();
	} else if (event.key === "End") {
		event.preventDefault();
		items[items.length - 1]?.focus();
	}
}

async function runAction(action) {
	if (!action.isEnabled) return;
	close();
	emit("action", { action: action.id, context: props.context });
	if (typeof action.execute === "function") {
		await action.execute(props.context);
	}
	await nextTick();
	triggerRef.value?.focus({ preventScroll: true });
}

onBeforeUnmount(() => {
	document.removeEventListener("pointerdown", handleOutsidePointerDown, true);
});

defineExpose({
	open,
	close,
	isOpen,
});
</script>

<style scoped>
.fxr-row-actions-menu {
	display: inline-flex;
	align-items: center;
	position: relative;
}

.fxr-row-actions-menu__trigger {
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
	color: var(--fxr-text-muted, #6b7280);
	cursor: pointer;
	transition: background-color 120ms ease, color 120ms ease, border-color 120ms ease;
}

.fxr-row-actions-menu__trigger:hover,
.fxr-row-actions-menu__trigger:focus-visible,
.fxr-row-actions-menu__trigger.is-active {
	background: var(--fxr-surface-soft, #f3f4f6);
	color: var(--fxr-text, #111827);
	border-color: var(--fxr-border-subtle, #d1d5db);
}

.fxr-row-actions-menu__dropdown {
	position: fixed;
	background: var(--fxr-surface, #fff);
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
	outline: none;
	animation: fxr-menu-pop 100ms cubic-bezier(0.16, 1, 0.3, 1);
}

.fxr-row-actions-menu__items {
	display: flex;
	flex-direction: column;
	padding: 4px;
	gap: 1px;
}

.fxr-row-actions-menu__item {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	min-height: 28px;
	padding: 5px 8px;
	border: 0;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text, #111827);
	font: inherit;
	font-size: var(--fxr-text-xs, 11px);
	font-weight: var(--fxr-weight-medium, 500);
	text-align: left;
	cursor: pointer;
	transition: background-color 80ms ease, color 80ms ease;
}

.fxr-row-actions-menu__item:hover:not(:disabled),
.fxr-row-actions-menu__item:focus-visible:not(:disabled) {
	background: var(--fxr-surface-soft, #f3f4f6);
	color: var(--fxr-text, #111827);
	outline: none;
}

.fxr-row-actions-menu__item.is-danger {
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-row-actions-menu__item.is-danger:hover:not(:disabled),
.fxr-row-actions-menu__item.is-danger:focus-visible:not(:disabled) {
	background: var(--fxr-surface-danger, #fef2f2);
	color: var(--fxr-text-danger, #b91c1c);
}

.fxr-row-actions-menu__item:disabled {
	opacity: 0.4;
	cursor: default;
}

.fxr-row-actions-menu__icon {
	width: 14px;
	text-align: center;
	color: var(--fxr-text-muted, #6b7280);
}

.fxr-row-actions-menu__item.is-danger .fxr-row-actions-menu__icon {
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-row-actions-menu__label {
	flex: 1 1 auto;
	min-width: 0;
	white-space: nowrap;
}

.fxr-row-actions-menu__shortcut {
	margin-left: auto;
	padding: 1px 4px;
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
	border-radius: 3px;
	background: var(--fxr-surface-soft, #f9fafb);
	color: var(--fxr-text-muted, #6b7280);
	font-family: inherit;
	font-size: 10px;
	line-height: 1.2;
}

.fxr-row-actions-menu__divider {
	height: 1px;
	margin: 3px 0;
	background: var(--fxr-border-subtle, #e5e7eb);
}

@keyframes fxr-menu-pop {
	from {
		opacity: 0;
		transform: scale(0.96) translateY(-4px);
	}
	to {
		opacity: 1;
		transform: scale(1) translateY(0);
	}
}

@media (max-width: 768px) {
	.fxr-row-actions-menu__trigger {
		width: 32px;
		height: 32px;
		min-height: 32px;
	}

	.fxr-row-actions-menu__item {
		min-height: 34px;
		padding: 7px 10px;
		font-size: var(--fxr-text-sm, 12px);
	}
}
</style>
