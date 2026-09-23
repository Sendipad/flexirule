import { ref, computed, watch } from "vue";
import { getStrategy, getAllStrategies } from "./strategies";

export function normalizeResolverPayload(val) {
	if (!val || typeof val !== "object") return val;
	const kind = val.kind;
	if (!kind) return val;

	// Normalize legacy kinds to canonical taxonomy
	if (kind === "date_formula") {
		return {
			...val,
			kind: "date",
			operation: val.offset_sign === "-" ? "subtract" : "add",
		};
	}
	if (kind === "date_diff") {
		return {
			...val,
			kind: "date",
			operation: "diff",
		};
	}
	if (kind === "math_formula") {
		return {
			...val,
			kind: "math",
			operation: val.math_op || "+",
		};
	}
	if (kind === "string_formula") {
		const opMap = { uppercase: "upper", lowercase: "lower" };
		return {
			...val,
			kind: "text",
			operation: opMap[val.str_op] || val.str_op || "concat",
			field_a: val.str_a,
			field_b: val.str_b,
		};
	}
	if (kind === "normalization") {
		return {
			...val,
			kind: "text",
			operation: val.norm_op || "trim",
			field_a: val.norm_field,
		};
	}
	if (kind === "format") {
		return {
			...val,
			kind: "text",
			operation: val.fmt_op || "format_date",
			field_a: val.fmt_field,
		};
	}
	if (kind === "child_aggregation") {
		return {
			...val,
			kind: "aggregate",
			agg_table: val.agg_table,
			agg_field: val.agg_field,
			agg_op: val.agg_op || "sum",
		};
	}
	if (kind === "fetch") {
		return {
			...val,
			kind: "lookup",
			operation: "get",
		};
	}
	if (kind === "system_context") {
		return {
			...val,
			kind: "value_source",
			operation: "system_context",
		};
	}

	return val;
}

export function useValueResolver(props, emit) {
	const localState = ref({});
	const activeKind = ref(null);
	const isValid = ref(true);
	const errors = ref([]);
	const isInitializing = ref(false);

	const availableStrategies = computed(() => {
		const all = getAllStrategies();
		if (props.allowedKinds && props.allowedKinds.length > 0) {
			return all.filter((s) => props.allowedKinds.includes(s.kind));
		}
		return all;
	});

	const activeStrategy = computed(() => getStrategy(activeKind.value));

	// Initialize state from props.modelValue
	const syncFromProps = () => {
		isInitializing.value = true;
		try {
			let val = props.modelValue || {};
			if (val.mode && val.config) {
				val = val.config;
			}

			// Normalize legacy resolver payload
			val = normalizeResolverPayload(val);

			const kind = val.kind || availableStrategies.value[0]?.kind || "value_source";
			activeKind.value = kind;

			const strategy = getStrategy(kind);
			if (strategy) {
				localState.value = {
					...strategy.defaultState(props),
					...val,
				};
			}
		} finally {
			setTimeout(() => {
				isInitializing.value = false;
			}, 0);
		}
	};

	// Watch for kind changes to reset state to defaults
	watch(activeKind, (newKind, oldKind) => {
		if (isInitializing.value) return;
		if (newKind === oldKind) return;
		const strategy = getStrategy(newKind);
		if (strategy) {
			localState.value = strategy.defaultState(props);
		}
	});

	// Emit updates to parent
	watch(
		[localState, activeKind],
		([newState, newKind]) => {
			if (isInitializing.value) return;

			const strategy = getStrategy(newKind);
			if (!strategy) return;

			const config = { ...newState, kind: newKind };
			const label = strategy.compileToLabel(config);
			const expression = strategy.compileToCode(config);

			// Run validation
			if (strategy.validate) {
				const validation = strategy.validate(config, props);
				isValid.value = validation.isValid;
				errors.value = validation.errors || [];
			} else {
				isValid.value = true;
				errors.value = [];
			}

			emit("update:modelValue", config, {
				label,
				expression,
				isValid: isValid.value,
				errors: errors.value,
			});
		},
		{ deep: true }
	);

	return {
		localState,
		activeKind,
		activeStrategy,
		availableStrategies,
		isValid,
		errors,
		syncFromProps,
	};
}
