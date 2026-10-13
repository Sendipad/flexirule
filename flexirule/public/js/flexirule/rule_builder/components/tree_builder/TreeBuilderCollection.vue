<template>
	<div class="tree-collection">
		<div class="tree-collection__header">
			<div class="tree-collection__label">
				<i class="fa fa-sitemap"></i>
				<span
					><slot name="label" :node="node"
						><strong>{{ label }}</strong></slot
					></span
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
	padding: var(--fxr-space-2);
	border: 1px solid var(--fxr-border-subtle);
	border-left: 3px solid var(--fxr-node-accent, var(--fxr-accent));
	border-radius: var(--fxr-radius-lg);
	background: var(--fxr-surface);
}
.tree-collection__header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--fxr-space-2);
	margin-bottom: var(--fxr-space-2);
}
.tree-collection__label,
.tree-collection__actions {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--fxr-space-1);
}
.tree-collection__actions .fxr-btn--icon {
	border: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface);
	color: var(--fxr-text-secondary);
	transition: all var(--fxr-transition-fast);
}
.tree-collection__actions .fxr-btn--icon:hover,
.tree-collection__actions .fxr-btn--icon:focus-visible {
	border-color: var(--fxr-border-strong);
	background: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
}
.tree-collection__actions .fxr-btn--icon.fxr-btn--danger:hover,
.tree-collection__actions .fxr-btn--icon.fxr-btn--danger:focus-visible {
	border-color: var(--fxr-border-danger);
	background: var(--fxr-bg-danger);
	color: var(--fxr-text-danger);
}
.tree-collection__children {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1);
	width: 100%;
	min-width: 0;
}
</style>
