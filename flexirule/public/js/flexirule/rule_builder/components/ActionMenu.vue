<template>
	<Menu
		as="div"
		class="fxr-action-menu"
		v-slot="{ open }"
		@pointerdown.stop
		@click.stop
		@dblclick.stop
	>
		<MenuButton
			ref="buttonRef"
			type="button"
			class="fxr-action-menu__trigger"
			:class="buttonClass"
			:disabled="disabled"
			:title="buttonTitle || __('Actions')"
			:aria-label="buttonAriaLabel || __('Actions')"
			@pointerdown.stop
			@keydown.stop
		>
			<slot name="button-icon">
				<i class="fa fa-ellipsis-v" aria-hidden="true"></i>
			</slot>
		</MenuButton>

		<Teleport to="body" :disabled="!teleport">
			<MenuItems
				v-if="open && visibleItems.length"
				:ref="setMenuRef"
				class="fxr-action-menu__items"
				:class="[`fxr-action-menu__items--${align}`, menuClass]"
				:style="menuStyle"
				@pointerdown.stop
				@click.stop
				@keydown.stop
			>
				<MenuItem
					v-for="item in visibleItems"
					:key="item.id"
					:disabled="Boolean(item.disabled)"
					v-slot="{ active }"
				>
					<button
						type="button"
						class="fxr-action-menu__item"
						:class="{
							'is-active': active,
							'is-danger': item.danger,
							'is-disabled': item.disabled,
						}"
						:disabled="Boolean(item.disabled)"
						:title="item.title || item.label"
						@click="handleItemClick(item)"
					>
						<i
							v-if="item.icon"
							:class="item.icon"
							class="fxr-action-menu__item-icon"
							aria-hidden="true"
						></i>
						<span class="fxr-action-menu__item-label">{{ item.label }}</span>
						<kbd v-if="item.shortcut" class="fxr-action-menu__item-shortcut">{{
							item.shortcut
						}}</kbd>
					</button>
				</MenuItem>
			</MenuItems>
		</Teleport>
	</Menu>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";
import { autoUpdate, computePosition, flip, offset, shift, size } from "@floating-ui/dom";

const props = defineProps({
	items: { type: Array, default: () => [] },
	align: {
		type: String,
		default: "right",
		validator: (value) => ["left", "right"].includes(value),
	},
	disabled: Boolean,
	buttonClass: { type: String, default: "" },
	menuClass: { type: String, default: "" },
	buttonTitle: { type: String, default: "" },
	buttonAriaLabel: { type: String, default: "" },
	teleport: { type: Boolean, default: true },
});

const emit = defineEmits(["select"]);
const buttonRef = ref(null);
const menuElement = ref(null);
const menuStyle = ref({ position: "fixed", top: "0px", left: "0px", visibility: "hidden" });
let stopAutoUpdate = null;

const visibleItems = computed(() =>
	(Array.isArray(props.items) ? props.items : []).filter((item) => item && item.visible !== false)
);

function resolveElement(value) {
	return value?.$el || value || null;
}

async function updateMenuPosition() {
	const reference = resolveElement(buttonRef.value);
	const floating = resolveElement(menuElement.value);
	if (!reference?.getBoundingClientRect || !floating?.getBoundingClientRect) return;

	try {
		const { x, y } = await computePosition(reference, floating, {
			strategy: "fixed",
			placement: props.align === "left" ? "bottom-start" : "bottom-end",
			middleware: [
				offset(4),
				flip({ padding: 8 }),
				shift({ padding: 8 }),
				size({
					padding: 8,
					apply({ availableWidth, availableHeight, elements }) {
						elements.floating.style.maxWidth = `${Math.max(0, availableWidth)}px`;
						elements.floating.style.maxHeight = `${Math.max(
							0,
						Math.min(280, availableHeight)
						)}px`;
					},
				}),
			],
		});
		if (resolveElement(menuElement.value) !== floating) return;
		menuStyle.value = {
			position: "fixed",
			top: `${y}px`,
			left: `${x}px`,
			zIndex: 10000,
			visibility: "visible",
		};
	} catch {
		// Headless UI still owns menu visibility and focus if the anchor is removed mid-update.
	}
}

function setMenuRef(value) {
	stopAutoUpdate?.();
	stopAutoUpdate = null;
	menuElement.value = value;
	const floating = resolveElement(value);
	const reference = resolveElement(buttonRef.value);
	if (!floating || !reference) return;
	stopAutoUpdate = autoUpdate(reference, floating, () => {
		void updateMenuPosition();
	});
}

function handleItemClick(item) {
	if (!item || item.disabled) return;
	if (typeof item.handler === "function") item.handler(item);
	emit("select", item.id, item);
}

onBeforeUnmount(() => {
	stopAutoUpdate?.();
	stopAutoUpdate = null;
});
</script>

<style scoped>
.fxr-action-menu {
	position: relative;
	display: inline-flex;
	align-items: center;
}

.fxr-action-menu__trigger {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 26px;
	height: 26px;
	min-width: 26px;
	min-height: 26px;
	margin: 0;
	padding: 0;
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #fff);
	color: var(--fxr-text-secondary, #4b5563);
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast, 120ms ease),
		border-color var(--fxr-transition-fast, 120ms ease),
		color var(--fxr-transition-fast, 120ms ease);
}

.fxr-action-menu__trigger:hover:not(:disabled),
.fxr-action-menu__trigger:focus-visible {
	border-color: var(--fxr-border-strong, #9ca3af);
	background: var(--fxr-surface-2, #f3f4f6);
	color: var(--fxr-text-strong, #111827);
}

.fxr-action-menu__trigger:disabled {
	opacity: 0.4;
	cursor: not-allowed;
}

.fxr-action-menu__items {
	position: fixed;
	z-index: 10000;
	min-width: min(140px, calc(100vw - 16px));
	max-width: min(260px, calc(100vw - 16px));
	max-height: min(280px, calc(100vh - 16px));
	overflow: auto;
	padding: 4px;
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #fff);
	box-shadow: var(--fxr-shadow-md, 0 4px 12px rgba(0, 0, 0, 0.12));
	outline: none;
}

.fxr-action-menu__item {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2, 8px);
	width: 100%;
	padding: 5px 8px;
	border: 0;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text, #111827);
	font-family: inherit;
	font-size: var(--fxr-text-xs, 12px);
	text-align: left;
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast, 120ms ease),
		color var(--fxr-transition-fast, 120ms ease);
}

.fxr-action-menu__item.is-active {
	background: var(--fxr-bg-hover, #f3f4f6);
	color: var(--fxr-text-strong, #111827);
}

.fxr-action-menu__item.is-danger {
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-action-menu__item.is-danger.is-active {
	background: var(--fxr-bg-danger, #fef2f2);
	color: var(--fxr-text-danger, #dc2626);
}

.fxr-action-menu__item.is-disabled,
.fxr-action-menu__item:disabled {
	opacity: 0.45;
	cursor: not-allowed;
}

.fxr-action-menu__item-icon {
	width: 14px;
	text-align: center;
	flex: 0 0 14px;
}

.fxr-action-menu__item-label {
	flex: 1 1 auto;
	min-width: 0;
}

.fxr-action-menu__item-shortcut {
	font-size: var(--fxr-text-xs, 10px);
	color: var(--fxr-text-muted, #6b7280);
	background: var(--fxr-bg-muted, #f3f4f6);
	padding: 1px 4px;
	border-radius: var(--fxr-radius-sm, 3px);
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
}
</style>
