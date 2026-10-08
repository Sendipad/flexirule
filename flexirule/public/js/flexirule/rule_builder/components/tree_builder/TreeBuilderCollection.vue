<template>
	<div class="tree-collection">
		<div class="tree-collection__header">
			<div class="tree-collection__label">
				<i class="fa fa-sitemap"></i>
				><slot name="label" :node="node"><strong>{{ label }}</strong></slot
				>
			</div>
			<div v-if="!readOnly" class="tree-collection__actions">
				<button type="button" class="fxr-btn fxr-btn--icon" @click="$emit('add-leaf')">
					<i class="fa fa-plus"></i>
				</button>
				<button
					v-if="allowGroups"
					type="button"
					class="fxr-btn fxr-btn--icon"
					@click="$emit('add-group')"
				>
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					v-if="allowCollections"
					type="button"
					class="fxr-btn fxr-btn--icon"
					@click="$emit('add-collection')"
				>
					<i class="fa fa-sitemap"></i>
				</button>
				<button
					type="button"
					class="fxr-btn fxr-btn--icon fxr-btn--danger"
					@click="$emit('remove')"
				>
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>
		<div class="tree-collection__children"><slot name="children" /></div>
	</div>
</template>
<script setup>
defineProps({
	node: { type: Object, required: true },
	label: { type: String, default: "Collection" },
	readOnly: Boolean,
	allowGroups: Boolean,
	allowCollections: Boolean,
});
defineEmits(["add-leaf", "add-group", "add-collection", "remove"]);
</script>
<style scoped>
.tree-collection {
	padding: var(--fxr-space-3);
	border: 1px solid var(--fxr-border-subtle);
	border-left: 3px solid var(--fxr-node-accent, var(--fxr-accent));
	border-radius: var(--fxr-radius-lg);
	background: var(--fxr-surface);
}
.tree-collection__header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: var(--fxr-space-2);
	margin-bottom: var(--fxr-space-2);
}
.tree-collection__label,
.tree-collection__actions {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-1);
}
.tree-collection__children {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
}
</style>
