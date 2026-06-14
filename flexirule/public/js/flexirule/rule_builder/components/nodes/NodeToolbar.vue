<script setup>
import { computed } from "vue";

const props = defineProps({
	show: { type: Boolean, default: false },
	isReadOnly: { type: Boolean, default: false },
	allowConfig: { type: Boolean, default: true },
	allowDelete: { type: Boolean, default: true },
});

const emit = defineEmits(["configure", "delete"]);
</script>

<template>
	<Transition name="fade">
		<div v-if="show" class="node-toolbar" @click.stop>
			<button
				v-if="allowConfig"
				class="toolbar-btn config-btn"
				@click.stop="emit('configure')"
				:title="isReadOnly ? __('View Configuration') : __('Configure')"
			>
				<i :class="['fa', isReadOnly ? 'fa-eye' : 'fa-cog']"></i>
			</button>
			<button
				v-if="!isReadOnly && allowDelete"
				class="toolbar-btn delete-btn"
				@click.stop="emit('delete')"
				:title="__('Delete Node')"
			>
				<i class="fa fa-trash"></i>
			</button>
		</div>
	</Transition>
</template>

<style scoped>
.node-toolbar {
	position: absolute;
	top: -36px;
	right: 0;
	display: flex;
	gap: 4px;
	background: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 6px;
	padding: 4px;
	box-shadow: var(--fxr-shadow-md);
	z-index: 100;
	pointer-events: all;
}

.toolbar-btn {
	width: 26px;
	height: 26px;
	display: flex;
	align-items: center;
	justify-content: center;
	border: none;
	background: transparent;
	border-radius: 4px;
	color: var(--fxr-text-soft);
	cursor: pointer;
	transition: all 0.2s;
	font-size: 13px;
}

.toolbar-btn:hover {
	background: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
}

.config-btn:hover {
	color: var(--fxr-accent);
}

.delete-btn:hover {
	color: var(--fxr-text-danger);
	background: var(--fxr-danger-soft);
}

.fade-enter-active,
.fade-leave-active {
	transition:
		opacity 0.2s,
		transform 0.2s;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
	transform: translateY(4px);
}
</style>
