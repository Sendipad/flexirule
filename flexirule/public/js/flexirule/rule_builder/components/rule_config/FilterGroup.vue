<template>
	<div class="filter-group-wrapper fxr-accent-scope" :style="panelStyleVars">
		<div
			v-if="!doctype && !allowAnyDoctype"
			class="text-muted small p-2 text-center border-dashed rounded"
		>
			{{ __("Select a DocType to configure filters.") }}
		</div>
		<div v-else class="filter-list">
			<div
				v-for="(row, idx) in filters"
				:key="idx"
				class="filter-row"
				:class="{ 'single-row': singleRow }"
			>
				<FilterLeaf
					ref="filterLeafRefs"
					:modelValue="[row]"
					:doctype="row.doctype || doctype"
					:nodeId="nodeId"
					:readOnly="readOnly"
					:allowAnyDoctype="allowAnyDoctype"
					:variableOptions="effectiveVariableOptions"
					:showValidation="showValidation"
					:hideActions="hideActions"
					@update:modelValue="(val) => updateRowFromLeaf(idx, val)"
					@remove="removeFilter(idx)"
				/>
			</div>

			<div v-if="!readOnly && !hideActions && !singleRow" class="filter-actions mt-2">
				<button class="btn btn-xs btn-link p-0 text-primary" @click="addFilter">
					<i class="fa fa-plus mr-1"></i> {{ __("Add Filter") }}
				</button>
				<button
					v-if="filters.length > 0"
					class="btn btn-xs btn-link p-0 text-muted ml-3"
					@click="clearFilters"
				>
					{{ __("Clear All") }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject, nextTick } from "vue";
import FilterLeaf from "./FilterLeaf.vue";
import { useStore } from "../../stores";
import { getContract } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: {
		type: Array,
		default: () => [],
	},
	doctype: {
		type: String,
		required: true,
	},
	nodeId: {
		type: String,
		default: null,
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	allowAnyDoctype: {
		type: Boolean,
		default: false,
	},
	variableOptions: {
		type: Array,
		default: null,
	},
	showValidation: {
		type: Boolean,
		default: false,
	},
	singleRow: {
		type: Boolean,
		default: false,
	},
	hideActions: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const filterLeafRefs = ref([]);

const injectedVariableOptions = inject("variableOptions", ref([]));
const effectiveVariableOptions = computed(
	() => props.variableOptions ?? injectedVariableOptions.value
);

const panelStyleVars = computed(() => {
	const node = (store.nodes || []).find((n) => n.id === props.nodeId);
	const actionType = node?.data?.action_type || node?.type;
	const accent = getContract(actionType)?.css?.color || "var(--fxr-accent)";
	return {
		"--fxr-node-accent": accent,
		"--fxr-node-accent-light": `color-mix(in srgb, ${accent} 12%, var(--fxr-surface))`,
	};
});

const filters = ref([]);

function coerceStructuredFilterValue(rawValue) {
	if (Array.isArray(rawValue)) {
		return rawValue.map((item) => coerceStructuredFilterValue(item));
	}

	if (rawValue && typeof rawValue === "object" && rawValue.mode) {
		if (["formula", "format", "normalize", "normalization"].includes(rawValue.mode)) {
			const config = { ...(rawValue.config || {}) };
			if (!config.kind) {
				if (rawValue.mode === "formula") config.kind = "math_formula";
				if (["format", "normalize", "normalization"].includes(rawValue.mode)) {
					config.kind = "text";
				}
			}
			return {
				mode: "resolver",
				value: rawValue.value || rawValue.expression || "",
				config,
			};
		}
		if (rawValue.mode === "variable") {
			return { mode: "variable", value: rawValue.value || rawValue.path || "" };
		}
		return rawValue;
	}

	if (
		rawValue &&
		typeof rawValue === "object" &&
		!Array.isArray(rawValue) &&
		"value" in rawValue
	) {
		const rawType = String(rawValue.value_type || "Value").toLowerCase();
		if (rawValue.builder && typeof rawValue.builder === "object") {
			return {
				mode: "resolver",
				value: rawValue.value || "",
				config: rawValue.builder,
			};
		}
		if (rawType === "variable") {
			const path = String(rawValue.value || "")
				.trim()
				.replace(/^\{/, "")
				.replace(/\}$/, "");
			return { mode: "variable", value: path };
		}
		if (rawType === "expression") {
			return { mode: "resolver", value: rawValue.value || "" };
		}
		return { mode: "static", value: rawValue.value };
	}

	return { mode: "static", value: rawValue ?? "" };
}

const syncFromProps = () => {
	if (!props.modelValue || !Array.isArray(props.modelValue)) {
		filters.value = [];
		return;
	}

	const format = (list) =>
		(list || []).map((f) => {
			if (Array.isArray(f)) {
				return {
					doctype: f[0] || props.doctype,
					field: f[1] || "",
					operator: f[2] || "=",
					value: coerceStructuredFilterValue(f[3]),
				};
			}
			return {
				doctype: f.doctype || props.doctype,
				field: f.field || f.fieldname || "",
				operator: f.operator || f.op || "=",
				value: coerceStructuredFilterValue(f.value),
			};
		});

	const current_formatted = format(filters.value);
	const incoming_formatted = format(props.modelValue || []);

	if (JSON.stringify(current_formatted) === JSON.stringify(incoming_formatted)) {
		return;
	}

	filters.value = props.modelValue.map((f) => {
		if (Array.isArray(f)) {
			return {
				doctype: f[0] || props.doctype,
				field: f[1] || "",
				operator: f[2] || "=",
				value: coerceStructuredFilterValue(f[3]),
			};
		}
		return {
			doctype: f.doctype || props.doctype,
			field: f.field || f.fieldname || "",
			operator: f.operator || f.op || "=",
			value: coerceStructuredFilterValue(f.value),
		};
	});
};

const emitUpdate = () => {
	const serialized = filters.value.map((r) => [
		r.doctype || props.doctype,
		r.field || "",
		r.operator || "=",
		r.value,
	]);
	emit("update:modelValue", serialized);
};

function updateRowFromLeaf(idx, value) {
	const row = Array.isArray(value) ? value[0] : value;
	if (!row) return;

	let normalizedValue = row[3] !== undefined ? row[3] : row.value;
	let normalizedField = row[1] !== undefined ? row[1] : (row.field || row.fieldname || "");
	let normalizedDoctype = row[0] !== undefined ? row[0] : (row.doctype || props.doctype);
	let normalizedOperator = row[2] !== undefined ? row[2] : (row.operator || "=");

	filters.value[idx] = {
		doctype: normalizedDoctype,
		field: normalizedField,
		operator: normalizedOperator,
		value: normalizedValue,
	};
	emitUpdate();
}

const addFilter = () => {
	filters.value.push({
		doctype: props.doctype,
		field: "",
		operator: "=",
		value: { mode: "static", value: "" },
	});
	emitUpdate();
};

const removeFilter = (idx) => {
	filters.value.splice(idx, 1);
	emitUpdate();
};

const clearFilters = () => {
	filters.value = [];
	emitUpdate();
};

async function validate() {
	const results = await Promise.all(
		(filterLeafRefs.value || []).map((leaf) =>
			leaf && typeof leaf.validate === "function"
				? leaf.validate()
				: { valid: true, errors: [] }
		)
	);
	const errors = [];
	results.forEach((res, idx) => {
		if (!res.valid && res.errors) {
			res.errors.forEach((e) => errors.push(__("Filter #{0}: {1}", [idx + 1, e])));
		}
	});
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

watch(() => props.modelValue, syncFromProps, { deep: true });

onMounted(() => {
	syncFromProps();
});
</script>

<style scoped>
.filter-group-wrapper {
	width: 100%;
	font-family: var(--fxr-font-family);
}

.filter-list {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
}

.filter-row {
	display: flex;
	flex-direction: column;
	width: 100%;
}

.filter-actions {
	display: flex;
	align-items: center;
	padding-top: var(--fxr-space-2);
}

.filter-actions .btn {
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	border-radius: var(--fxr-radius-md);
	transition: all var(--fxr-transition-fast);
}

.filter-actions .btn:hover {
	text-decoration: none;
}

.border-dashed {
	border: 1px dashed var(--fxr-border);
	border-radius: var(--fxr-radius-lg);
}
</style>
