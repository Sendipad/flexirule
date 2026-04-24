<script setup>
import { computed, inject, onMounted, ref, watch } from "vue";
/**
 * CollectionUI - Child table iterator editor
 */
import ConditionNode from "./ConditionNode.vue";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);

const { addCondition, addGroup, addCollection } = inject("conditionActions");
const store = inject("store");

// Filter to show only Table fields
const tableFields = computed(() => {
	return props.docFields.filter((f) => f.fieldtype === "Table" && f.options);
});

// Child fields for the selected table
const childDocFields = ref([]);

// Resolve child table metadata
function fetchChildMeta() {
	const collectionPath = props.node.collection;
	const alias = props.node.alias || "row";

	if (!collectionPath) {
		childDocFields.value = props.docFields.filter((f) => f.fieldtype !== "Table");
		return;
	}

	// Auto-set alias from table name
	if (!props.node.alias) {
		const parts = collectionPath.split(".");
		props.node.alias = parts[parts.length - 1].replace(/[^a-zA-Z0-9_]/g, "_");
	}

	// Find table field metadata
	const fieldMeta = props.docFields.find((f) => f.value === collectionPath);

	if (fieldMeta && fieldMeta.options) {
		const childDoctype = fieldMeta.options;
		const childFields = store.get_fields_for_doctype(childDoctype, alias);
		const parentFields = props.docFields.filter((f) => f.fieldtype !== "Table");

		if (childFields.length > 0) {
			childDocFields.value = [...childFields, ...parentFields];
		} else {
			// Fetch if not cached
			store.fetch_metadata(childDoctype).then(() => {
				const fields = store.get_fields_for_doctype(childDoctype, alias);
				childDocFields.value = [...fields, ...parentFields];
			});
		}
	} else {
		childDocFields.value = props.docFields.filter((f) => f.fieldtype !== "Table");
	}
}

watch(() => props.node.collection, fetchChildMeta);
watch(() => props.node.alias, fetchChildMeta);
watch(() => props.docFields, fetchChildMeta, { deep: true });
onMounted(fetchChildMeta);
</script>

<template>
	<div class="collection-ui p-3 border-2 border-left-primary rounded bg-white">
		<!-- Header -->
		<div class="d-flex gap-3 mb-3 pb-2 border-bottom">
			<!-- Logic -->
			<div style="width: 100px">
				<label class="small text-muted mb-1 d-block">{{ __("Match") }}</label>
				<select v-model="node.op" class="form-control form-control-sm" :disabled="readOnly">
					<option value="any">{{ __("Any") }}</option>
					<option value="all">{{ __("All") }}</option>
					<option value="none">{{ __("None") }}</option>
				</select>
			</div>

			<!-- Table -->
			<div class="flex-grow-1">
				<label class="small text-muted mb-1 d-block">{{ __("Table") }}</label>
				<select
					v-model="node.collection"
					class="form-control form-control-sm"
					@change="fetchChildMeta"
					:disabled="readOnly"
				>
					<option value="">{{ __("Select table...") }}</option>
					<option v-for="f in tableFields" :key="f.value" :value="f.value">
						{{ f.label }}
					</option>
				</select>
			</div>

			<!-- Alias -->
			<div style="width: 120px">
				<label class="small text-muted mb-1 d-block">{{ __("Alias") }}</label>
				<input
					type="text"
					v-model="node.alias"
					class="form-control form-control-sm"
					placeholder="row"
					@input="fetchChildMeta"
					:disabled="readOnly"
				/>
			</div>

			<!-- Actions -->
			<div class="d-flex gap-1 align-items-end" v-if="!readOnly">
				<button
					class="btn btn-xs btn-default"
					@click="addCondition(node.where, node.alias || 'row')"
					:title="__('Add Condition')"
				>
					<i class="fa fa-plus"></i>
				</button>
				<button
					class="btn btn-xs btn-default"
					@click="addGroup(node.where)"
					:title="__('Add Group')"
				>
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					class="btn btn-xs btn-link text-danger"
					@click="emit('remove')"
					:title="__('Remove')"
				>
					<i class="fa fa-trash-o"></i>
				</button>
			</div>
		</div>

		<!-- Nested conditions -->
		<div class="pl-3 border-left">
			<div v-if="!node.where?.conditions?.length" class="text-muted py-2 text-sm text-center">
				{{ __("No conditions in collection. Click + to add.") }}
			</div>
			<div v-for="(child, idx) in node.where?.conditions" :key="child.id || idx" class="mb-2">
				<ConditionNode
					:node="child"
					:index="idx"
					:parentGroup="node.where"
					:docFields="childDocFields"
					:readOnly="readOnly"
				/>
			</div>
		</div>
	</div>
</template>

<style scoped>
.collection-ui {
	border-left: 4px solid var(--blue-500) !important;
}
</style>
