<template>
	<div class="tree-group">
		<div class="tree-group__header">
			<div class="tree-group__logic">
				<button
					v-for="op in operators"
					:key="op"
					type="button"
					class="logic-btn"
					:class="{ active: node.operator === op }"
					:disabled="readOnly"
					@click="$emit('operator', op)"
				>
					{{ operatorLabel(op) }}
				</button>
			</div>
			<div v-if="!readOnly" class="tree-group__actions">
				<button type="button" class="fxr-btn fxr-btn--icon" @click="$emit('add-leaf')">
					<i class="fa fa-plus"></i></button
				><button
					v-if="allowGroups"
					type="button"
					class="fxr-btn fxr-btn--icon"
					@click="$emit('add-group')"
				>
					<i class="fa fa-folder-open-o"></i></button
				><button
					type="button"
					class="fxr-btn fxr-btn--icon fxr-btn--danger"
					@click="$emit('remove')"
				>
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>
		<div class="tree-group__children"><slot name="children" /></div>
	</div>
</template>
<script setup>
defineProps({
	node: { type: Object, required: true },
	operators: { type: Array, default: () => ["and", "or"] },
	operatorLabel: { type: Function, default: (v) => v },
	readOnly: Boolean,
	allowGroups: Boolean,
});
defineEmits(["operator", "add-leaf", "add-group", "remove"]);
</script>
<style scoped>
.tree-group {
	padding: var(--fxr-space-3);
	background: var(--fxr-bg-hover);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
}
.tree-group__header {
	display: flex;
	justify-content: space-between;
	gap: var(--fxr-space-2);
	margin-bottom: var(--fxr-space-2);
}
.tree-group__logic,
.tree-group__actions {
	display: flex;
	gap: var(--fxr-space-1);
	align-items: center;
}
.logic-btn {
	border: 0;
	background: transparent;
	padding: 3px 9px;
	border-radius: var(--fxr-radius-sm);
	font-size: 10px;
	font-weight: 800;
}
.logic-btn.active {
	background: var(--fxr-node-accent, var(--fxr-accent));
	color: #fff;
}
.tree-group__children {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
}
</style>
