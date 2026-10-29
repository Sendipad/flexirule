<template>
	<Menu as="div" class="fxr-action-menu" @pointerdown.stop @click.stop @dblclick.stop>
		<MenuButton
			type="button"
			class="fxr-action-menu__trigger"
			:class="buttonClass"
			:disabled="disabled"
			:title="buttonTitle || __('Actions')"
			:aria-label="buttonAriaLabel || __('Actions')"
			@pointerdown.stop
			@click.stop
			@keydown.stop
		>
			<slot name="button-icon">
				<i class="fa fa-ellipsis-v" aria-hidden="true"></i>
			</slot>
		</MenuButton>

		<transition
			enter-active-class="fxr-action-menu__transition-enter-active"
			enter-from-class="fxr-action-menu__transition-enter-from"
			enter-to-class="fxr-action-menu__transition-enter-to"
			leave-active-class="fxr-action-menu__transition-leave-active"
			leave-from-class="fxr-action-menu__transition-leave-to"
			leave-to-class="fxr-action-menu__transition-leave-to"
		>
			<MenuItems
				class="fxr-action-menu__items"
				:class="[
					align === 'left'
						? 'fxr-action-menu__items--left'
						: 'fxr-action-menu__items--right',
					menuClass,
				]"
				@pointerdown.stop
				@click.stop
				@keydown.stop
			>
				<div
					v-for="item in visibleItems"
					:key="item.id"
					class="fxr-action-menu__item-wrapper"
				>
					<MenuItem v-slot="{ active }">
						<button
							type="button"
							class="fxr-action-menu__item"
							:class="{
								'is-active': active,
								'is-danger': item.danger,
								'is-disabled': item.disabled,
							}"
							:disabled="item.disabled"
							:title="item.title || item.label"
							@click.stop="handleItemClick(item)"
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
				</div>
			</MenuItems>
		</transition>
	</Menu>
</template>

<script setup>
import { computed } from "vue";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";

const props = defineProps({
	items: {
		type: Array,
		default: () => [],
	},
	align: {
		type: String,
		default: "right",
	},
	disabled: Boolean,
	buttonClass: {
		type: String,
		default: "",
	},
	menuClass: {
		type: String,
		default: "",
	},
	buttonTitle: {
		type: String,
		default: "",
	},
	buttonAriaLabel: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["select"]);

const visibleItems = computed(() => {
	return (props.items || []).filter((item) => item && item.visible !== false);
});

function handleItemClick(item) {
	if (item.disabled) return;
	if (typeof item.handler === "function") {
		item.handler(item);
	}
	emit("select", item.id, item);
}
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
	transition:
		background-color var(--fxr-transition-fast, 120ms ease),
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
	position: absolute;
	z-index: 1000;
	top: calc(100% + 4px);
	min-width: 140px;
	padding: 4px;
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #fff);
	box-shadow: var(--fxr-shadow-md, 0 4px 12px rgba(0, 0, 0, 0.12));
	outline: none;
}

.fxr-action-menu__items--right {
	right: 0;
}

.fxr-action-menu__items--left {
	left: 0;
}

.fxr-action-menu__item-wrapper {
	width: 100%;
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
	transition:
		background-color var(--fxr-transition-fast, 120ms ease),
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

.fxr-action-menu__transition-enter-active,
.fxr-action-menu__transition-leave-active {
	transition:
		opacity 100ms ease,
		transform 100ms ease;
}

.fxr-action-menu__transition-enter-from,
.fxr-action-menu__transition-leave-to {
	opacity: 0;
	transform: scale(0.95);
}

.fxr-action-menu__transition-enter-to {
	opacity: 1;
	transform: scale(1);
}
</style>
