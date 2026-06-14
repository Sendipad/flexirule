<script setup>
import { computed } from "vue";
import { useUIStore } from "../../stores/useUIStore";

const props = defineProps({
	nodeId: {
		type: String,
		required: true,
	},
	selected: {
		type: Boolean,
		default: false,
	},
	isReadOnly: {
		type: Boolean,
		default: false,
	},
	showDelete: {
		type: Boolean,
		default: true,
	},
});

const emit = defineEmits(["configure", "delete", "select"]);

const uiStore = useUIStore();

const isSelected = computed({
	get: () => props.selected,
	set: (val) => emit("select", val),
});

function onConfigure() {
	emit("configure");
}

function onDelete() {
	emit("delete");
}
</script>

<template>
	<div class="node-toolbar" :class="{ 'is-active': selected }">
		<div class="toolbar-content">
			<div class="toolbar-item checkbox-item">
				<input type="checkbox" v-model="isSelected" @click.stop />
			</div>
			<div class="divider"></div>
			<button
				class="toolbar-item action-btn configure"
				@click.stop="onConfigure"
				:title="isReadOnly ? __('View') : __('Configure')"
			>
				<i :class="['fa', isReadOnly ? 'fa-eye' : 'fa-cog']"></i>
			</button>
			<template v-if="!isReadOnly && showDelete">
				<div class="divider"></div>
				<button
					class="toolbar-item action-btn delete"
					@click.stop="onDelete"
					:title="__('Delete')"
				>
					<i class="fa fa-trash"></i>
				</button>
			</template>
		</div>
	</div>
</template>

<style scoped>
.node-toolbar {
	position: absolute;
	top: -40px;
	right: 0;
	z-index: 50;
	opacity: 0;
	pointer-events: none;
	transition: all 0.2s ease;
	transform: translateY(10px);
}

:hover > .node-toolbar,
.node-toolbar.is-active {
	opacity: 1;
	pointer-events: auto;
	transform: translateY(0);
}

.toolbar-content {
	display: flex;
	align-items: center;
	background-color: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-lg);
	padding: 4px;
	gap: 2px;
}

.toolbar-item {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	border-radius: 6px;
	border: none;
	background: transparent;
	color: var(--fxr-text-soft);
	cursor: pointer;
	transition: all 0.15s ease;
}

.checkbox-item {
	width: 24px;
}

.checkbox-item input {
	cursor: pointer;
	width: 14px;
	height: 14px;
}

.action-btn:hover {
	background-color: var(--fxr-bg-hover);
	color: var(--fxr-text-strong);
}

.action-btn.configure:hover {
	color: var(--fxr-accent);
}

.action-btn.delete:hover {
	color: var(--fxr-text-danger);
	background-color: var(--fxr-bg-danger);
}

.divider {
	width: 1px;
	height: 16px;
	background-color: var(--fxr-border-subtle);
	margin: 0 2px;
}

@media (max-width: 768px) {
	.node-toolbar {
		top: -45px;
	}
	.toolbar-item {
		width: 32px;
		height: 32px;
	}
}
</style>
