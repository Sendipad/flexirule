<script setup>
import { computed, inject, onMounted, provide, reactive, ref, watch } from "vue";
/**
 * CollectionUI - Child table iterator editor
 */
import ConditionNode from "./ConditionNode.vue";
import { useStore } from "../../stores";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);

const { addCondition, addGroup } = inject("conditionActions");
const store = useStore();

const aliasValue = computed(() => {
	const rawAlias = String(props.node.alias || "").trim();
	if (!rawAlias) return "row";
	return rawAlias.replace(/[^\w]/g, "_");
});

// Provide overridden alias to children
provide(
	"conditionContext",
	reactive({
		alias: computed(() => aliasValue.value),
	})
);

const tableFields = computed(() => {
	const fields = props.docFields || [];
	return fields.filter((f) => {
		// 1. Static Table fields
		if (f.fieldtype === "Table") return true;

		// 2. Variables marked as Table
		if (f.is_variable && f.fieldtype === "Table") return true;

		// 3. Variables that have sub-fields (schema-driven)
		if (f.is_variable) {
			const prefix = f.value + ".";
			return fields.some((sub) => sub.value.startsWith(prefix));
		}

		return false;
	});
});

// Child fields for the selected table
const childDocFields = ref([]);

function addConditionForCollection() {
	const alias = aliasValue.value;
	const firstAliasField = childDocFields.value.find((f) =>
		String(f?.value || "").startsWith(`${alias}.`)
	);
	addCondition(props.node.where, alias);
	const last = props.node.where?.conditions?.[props.node.where.conditions.length - 1];
	if (last?.left && firstAliasField?.value) {
		last.left.ref = firstAliasField.value;
	}
}
// Resolve child table metadata
function fetchChildMeta() {
	const collectionPath = props.node.collection;
	const alias = aliasValue.value;

	if (!collectionPath) {
		childDocFields.value = props.docFields.filter((f) => f.fieldtype !== "Table");
		return;
	}

	// Auto-set alias from table name if not set
	if (!props.node.alias) {
		const parts = collectionPath.split(".");
		props.node.alias = parts[parts.length - 1].replace(/[^a-zA-Z0-9_]/g, "_");
	}

	// Resolve table field metadata
	const fieldMeta = props.docFields.find((f) => f.value === collectionPath);
	const isVariable = collectionPath.startsWith("vars.") || fieldMeta?.is_variable;

	if (isVariable) {
		// Try multiple possible roots for the variable (with and without vars. prefix)
		const cleanPath = collectionPath.replace(/^vars\./, "");
		const possibleRoots = [collectionPath, `vars.${cleanPath}`, cleanPath];

		let subFields = [];
		let matchedRoot = "";

		for (const root of possibleRoots) {
			const prefix = root + ".";
			const found = props.docFields.filter((f) => f.value.startsWith(prefix));
			if (found.length > 0) {
				subFields = found;
				matchedRoot = root;
				break;
			}
		}

		if (matchedRoot) {
			const prefix = matchedRoot + ".";
			const aliasFields = subFields.map((f) => {
				const subPath = f.value.slice(prefix.length);
				// Clean label: remove the variable prefix and (Variable) suffix if present
				let cleanLabel = f.label
					.replace(prefix, "")
					.replace(/\s*\([\w\u0600-\u06FF\s]+\)$/, "");

				// If cleanLabel contains a parenthesized human label, extract it
				const humanLabelMatch = cleanLabel.match(/\((.*)\)/);
				if (humanLabelMatch) {
					cleanLabel = humanLabelMatch[1];
				}

				return {
					...f,
					label: `${alias}.${subPath} (${cleanLabel})`,
					value: `${alias}.${subPath}`,
				};
			});

			// Include non-table parent fields (global context) - KEEP other variables!
			const parentFields = props.docFields.filter(
				(f) =>
					f.fieldtype !== "Table" &&
					!possibleRoots.includes(f.value) &&
					!f.value.startsWith(prefix)
			);

			const merged = [];
			const seen = new Set();
			[...aliasFields, ...parentFields].forEach((field) => {
				const key = String(field?.value || "");
				if (!key || seen.has(key)) return;
				seen.add(key);
				merged.push(field);
			});
			childDocFields.value = merged;
			return;
		}
	}

	// Find table field metadata
	// (fieldMeta is already declared above)

	if (fieldMeta && fieldMeta.options) {
		const childDoctype = fieldMeta.options;
		const getAliasFields = () =>
			typeof store.get_fields_for_doctype === "function"
				? store.get_fields_for_doctype(childDoctype, alias)
				: [];
		const parentFields = props.docFields.filter((f) => f.fieldtype !== "Table");
		const mergeFields = (aliasFields) => {
			const merged = [];
			const seen = new Set();
			[...(aliasFields || []), ...parentFields].forEach((field) => {
				const key = String(field?.value || "");
				if (!key || seen.has(key)) return;
				seen.add(key);
				merged.push(field);
			});
			childDocFields.value = merged;
		};

		const childFields = getAliasFields();
		if (childFields.length > 0) {
			mergeFields(childFields);
			return;
		}

		// Fetch if not cached
		if (typeof store.fetch_metadata === "function") {
			store.fetch_metadata(childDoctype).then(() => {
				mergeFields(getAliasFields());
			});
			return;
		}

		mergeFields([]);
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
					@click="addConditionForCollection"
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
