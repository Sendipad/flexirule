<template>
	<div class="tree-leaf">
		<div class="tree-leaf__content">
			<slot :node="node" :context="context" :index="index" :parent="parent" />
		</div>
		<button
			v-if="!readOnly"
			type="button"
			class="tree-leaf__remove"
			:title="__('Remove')"
			@click="$emit('remove')"
		>
			<i class="fa fa-trash"></i>
		</button>
	</div>
</template>
<script setup>
defineProps({
	node: { type: Object, required: true },
	context: { type: Object, default: () => ({ scopes: [], path: [] }) },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: Boolean,
});
defineEmits(["remove"]);
</script>
<style scoped>
.tree-leaf {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: var(--fxr-space-2);
	align-items: start;
}
.tree-leaf__remove {
	width: 30px;
	height: 30px;
	margin-top: 4px;
	border: 0;
	background: transparent;
	color: var(--fxr-text-danger, #ef4444);
	border-radius: var(--fxr-radius-sm);
	cursor: pointer;
}
</style>
