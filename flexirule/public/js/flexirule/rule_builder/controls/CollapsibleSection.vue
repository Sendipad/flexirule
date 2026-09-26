<template>
	<div class="fxr-collapsible" :class="{ 'is-collapsed': collapsed }">
		<div
			class="fxr-collapsible__header"
			role="button"
			:tabindex="readOnly ? -1 : 0"
			:aria-expanded="!collapsed"
			@click="toggle"
			@keydown.enter.prevent="toggle"
			@keydown.space.prevent="toggle"
		>
			<div class="d-flex align-items-center fxr-gap-2 flex-1">
				<i
					class="fa fa-chevron-right fxr-collapsible__arrow"
					:class="{ 'rotate-90': !collapsed }"
				></i>
				<span class="fxr-label-sm mb-0">{{ label }}</span>
			</div>
			<slot name="header-actions"></slot>
		</div>
		<transition name="fxr-collapse">
			<div v-if="!collapsed" class="fxr-collapsible__body">
				<slot></slot>
			</div>
		</transition>
	</div>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
	label: String,
	initialCollapsed: { type: Boolean, default: true },
	readOnly: Boolean,
});

const collapsed = ref(props.initialCollapsed);

const toggle = () => {
	if (props.readOnly) return;
	collapsed.value = !collapsed.value;
};

defineExpose({
	collapsed,
	open: () => (collapsed.value = false),
	close: () => (collapsed.value = true),
});
</script>

<style scoped>
.fxr-collapsible {
	border-bottom: 1px solid var(--fxr-border-subtle);
}
.fxr-collapsible__header {
	display: flex;
	align-items: center;
	padding: 8px 0;
	cursor: pointer;
	user-select: none;
	outline: none;
}
.fxr-collapsible__header:focus-visible {
	box-shadow: inset 0 0 0 2px var(--fxr-accent);
}
.fxr-collapsible__arrow {
	font-size: 10px;
	color: var(--fxr-text-muted);
	transition: transform 0.2s ease;
}
.fxr-collapsible__arrow.rotate-90 {
	transform: rotate(90deg);
}
.fxr-collapsible__body {
	padding: 8px 0 12px 18px;
}

.fxr-collapse-enter-active,
.fxr-collapse-leave-active {
	transition:
		max-height 0.3s ease,
		opacity 0.3s ease;
	overflow: hidden;
}
.fxr-collapse-enter-from,
.fxr-collapse-leave-to {
	max-height: 0;
	opacity: 0;
}
.fxr-collapse-enter-to,
.fxr-collapse-leave-from {
	max-height: 500px;
	opacity: 1;
}
</style>
