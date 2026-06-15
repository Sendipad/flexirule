import { ref, computed, watch, nextTick } from "vue";
import { useStore } from "../stores";
import { compileToCode, compileToLabel } from "../../core/builder_utils.js";

const __ = window.__ || ((s) => s);

/**
 * Strategy-based configuration for different resolver types.
 * Allows easy extensibility by adding new entries to RESOLVER_STRATEGIES.
 */
export const RESOLVER_STRATEGIES = {
	date_formula: {
		label: "Date Formula",
		icon: "fa fa-calendar",
		defaults: (context) => ({
			base_type: "today",
			base_field: context?.fieldname || "",
			offset_sign: "+",
			offset_value: 0,
			offset_unit: "days",
		}),
		validate: (state, meta) => {
			if (state.base_type === "doc_field" && !meta.some((f) => f.value === state.base_field)) {
				return { valid: false, message: "Base field reference is invalid." };
			}
			return { valid: true };
		},
	},
	math_formula: {
		label: "Math Formula",
		icon: "fa fa-calculator",
		defaults: () => ({
			field_a: "",
			math_op: "+",
			field_b_type: "field",
			field_b: "",
			constant_b: 0,
			precision: 2,
		}),
		validate: (state, meta) => {
			if (state.field_a && !meta.some((f) => f.value === state.field_a)) return { valid: false, message: "Field A reference is invalid." };
			if (state.field_b_type === "field" && state.field_b && !meta.some((f) => f.value === state.field_b)) {
				return { valid: false, message: "Field B reference is invalid." };
			}
			return { valid: true };
		},
	},
	date_diff: {
		label: "Date Difference",
		icon: "fa fa-calendar-minus-o",
		defaults: (context) => ({
			diff_start_type: "today",
			diff_start_field: "",
			diff_end_type: "doc_field",
			diff_end_field: context?.fieldname || "",
			diff_unit: "days",
		}),
		validate: (state, meta) => {
			if (state.diff_start_type === "doc_field" && state.diff_start_field && !meta.some((f) => f.value === state.diff_start_field)) return { valid: false, message: "Start field reference is invalid." };
			if (state.diff_end_type === "doc_field" && state.diff_end_field && !meta.some((f) => f.value === state.diff_end_field)) return { valid: false, message: "End field reference is invalid." };
			return { valid: true };
		},
	},
	child_aggregation: {
		label: "Child Table Aggregation",
		icon: "fa fa-table",
		defaults: () => ({
			agg_table: "",
			agg_field: "",
			agg_op: "sum",
		}),
		validate: (state, meta) => {
			if (state.agg_table && !meta.some((f) => f.value === state.agg_table)) return { valid: false, message: "Child table reference is invalid." };
			return { valid: true };
		},
	},
	string_formula: {
		label: "String Manipulation",
		icon: "fa fa-font",
		defaults: () => ({
			str_op: "concat",
			str_a_type: "field",
			str_a: "",
			str_b_type: "constant",
			str_b: "",
		}),
	},
	normalization: {
		label: "Normalization",
		icon: "fa fa-refresh",
		defaults: (context) => ({
			norm_op: "trim",
			norm_field: context?.fieldname || "",
		}),
	},
	format: {
		label: "Format",
		icon: "fa fa-paint-brush",
		defaults: (context) => ({
			fmt_op: "format_date",
			fmt_field: context?.fieldname || "",
			fmt_config: "",
		}),
	},
	fetch: {
		label: "Fetch From Link",
		icon: "fa fa-link",
		defaults: () => ({
			link_source_type: "doc_field",
			link_field: "",
			fetch_field: "",
			linked_doctype: "",
		}),
	},
	system_context: {
		label: "System Context",
		icon: "fa fa-globe",
		defaults: () => ({
			sys_token: "user",
			sys_role: "",
		}),
	},
};

export function useValueResolver(props, emit) {
	const store = useStore();
	const localState = ref({});
	const validationResult = ref({ valid: true, message: "" });
	let _syncing = false;

	const availableCategories = computed(() => {
		const all = Object.entries(RESOLVER_STRATEGIES).map(([value, config]) => ({
			value,
			label: __(config.label),
			icon: config.icon,
		}));
		if (props.allowedKinds && props.allowedKinds.length > 0) {
			return all.filter((c) => props.allowedKinds.includes(c.value));
		}
		return all;
	});

	const activeStrategy = computed(() => RESOLVER_STRATEGIES[localState.value.kind] || null);

	const categoryIcon = computed(() => activeStrategy.value?.icon || "fa fa-calculator");
	const popoverTitle = computed(() => (activeStrategy.value ? __(activeStrategy.value.label) : __("Configure Formula")));

	const currentMeta = computed(() => {
		const dt = store.rule_doc?.document_type || props.doctype;
		if (!dt) return [];
		return store.doc_meta[dt] || [];
	});

	/**
	 * Perform reference validation against dynamic metadata.
	 */
	const performValidation = () => {
		if (!activeStrategy.value?.validate) {
			validationResult.value = { valid: true, message: "" };
			return;
		}
		const metaOptions = currentMeta.value.map((f) => ({ value: f.value || f.fieldname }));
		validationResult.value = activeStrategy.value.validate(localState.value, metaOptions);
	};

	const syncFromProps = () => {
		let val = props.modelValue || {};
		if (val.mode && val.config) {
			val = val.config;
		}
		const kind = val.kind || (availableCategories.value.length > 0 ? availableCategories.value[0].value : "date_formula");
		const strategy = RESOLVER_STRATEGIES[kind];

		const baseDefaults = strategy?.defaults ? strategy.defaults(props.context) : {};
		const next = { kind, ...baseDefaults, ...val };

		// Handle legacy date_formula fields
		if (kind === "date_formula" && val.function_name) {
			if (val.function_name.includes("doc")) next.base_type = "doc_field";
			if (val.offset_days) {
				next.offset_sign = val.offset_days < 0 ? "-" : "+";
				next.offset_value = Math.abs(val.offset_days);
			}
		}

		_syncing = true;
		localState.value = next;
		performValidation();
		nextTick(() => (_syncing = false));
	};

	watch(() => props.modelValue, syncFromProps, { deep: true, immediate: true });
	watch(() => props.doctype, syncFromProps);

	// Re-validate when metadata changes
	watch(() => currentMeta.value, performValidation, { deep: true });

	watch(
		() => localState.value,
		(newVal) => {
			if (_syncing) return;
			performValidation();

			const config = { ...newVal };

			// Custom serialization for specific types
			if (newVal.kind === "date_formula") {
				config.offset_value = newVal.offset_sign === "-" ? -Math.abs(newVal.offset_value) : Math.abs(newVal.offset_value);
			}

			emit("update:modelValue", config, {
				label: compileToLabel(config),
				expression: compileToCode(config),
				valid: validationResult.value.valid,
			});
		},
		{ deep: true }
	);

	const updateKind = (newKind) => {
		const strategy = RESOLVER_STRATEGIES[newKind];
		const defaults = strategy?.defaults ? strategy.defaults(props.context) : {};
		localState.value = { kind: newKind, ...defaults };
	};

	return {
		localState,
		validationResult,
		availableCategories,
		categoryIcon,
		popoverTitle,
		updateKind,
		previewText: computed(() => compileToLabel(localState.value)),
		expressionSnippet: computed(() => {
			const s = { ...localState.value };
			if (s.kind === "date_formula") {
				s.offset_value = s.offset_sign === "-" ? -Math.abs(s.offset_value) : Math.abs(s.offset_value);
			}
			return compileToCode(s);
		}),
	};
}
