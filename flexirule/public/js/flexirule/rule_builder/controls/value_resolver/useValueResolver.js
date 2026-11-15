import { ref, computed, watch } from "vue";
import { getStrategy, getAllStrategies } from "./strategies";

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

			// Normalize canonical family / legacy structure
			let family = val.family;
			let kind = val.kind;
			let innerConfig = val.config && typeof val.config === "object" ? val.config : {};

			if (kind === "child_aggregation" || family === "child_aggregation") {
				family = "collection";
				kind = "collection";
				val = {
					source:
						val.source ||
						val.agg_table ||
						innerConfig.source ||
						innerConfig.agg_table ||
						"",
					target_field:
						val.target_field ||
						val.agg_field ||
						innerConfig.target_field ||
						innerConfig.agg_field ||
						"",
					operation:
						val.operation ||
						val.agg_op ||
						innerConfig.operation ||
						innerConfig.agg_op ||
						"sum",
					condition:
						val.condition !== undefined ? val.condition : innerConfig.condition || null,
				};
			} else if (family === "collection" || kind === "collection") {
				kind = "collection";
				val = {
					source: val.source || innerConfig.source || "",
					target_field: val.target_field || innerConfig.target_field || "",
					operation: val.operation || innerConfig.operation || "any",
					condition:
						val.condition !== undefined ? val.condition : innerConfig.condition || null,
				};
			} else if (family === "text" || kind === "text") {
				kind = "text";
				val = {
					operation: val.operation || innerConfig.operation || "combine",
					config: {
						...(val.config || innerConfig || {}),
					},
				};
			} else if (family === "date_time" || kind === "date_time") {
				kind = "date_time";
				val = {
					operation: val.operation || innerConfig.operation || "calculate",
					config: {
						...(val.config || innerConfig || {}),
					},
				};
			} else if (family === "lookup" || kind === "lookup" || kind === "fetch") {
				family = "lookup";
				kind = "lookup";
				const rawCfg = val.config && typeof val.config === "object" ? val.config : val;
				val = {
					doctype_mode:
						rawCfg.doctype_mode || (rawCfg.doctype_source ? "dynamic" : "static"),
					target_doctype: rawCfg.target_doctype || rawCfg.linked_doctype || "",
					doctype_source: rawCfg.doctype_source || "",
					record_source_type:
						rawCfg.record_source_type || rawCfg.link_source_type || "doc_field",
					record_field: rawCfg.record_field || rawCfg.link_field || "",
					fetch_field: rawCfg.fetch_field || "",
				};
			} else if (family === "math" || kind === "math_formula") {
				family = "math";
				kind = "math_formula";
				const rawCfg = val.config && typeof val.config === "object" ? val.config : val;
				val = {
					field_a: rawCfg.field_a || "",
					math_op: rawCfg.math_op || "+",
					field_b_type: rawCfg.field_b_type || "field",
					field_b: rawCfg.field_b || "",
					constant_b: rawCfg.constant_b !== undefined ? rawCfg.constant_b : 0,
					precision: rawCfg.precision !== undefined ? rawCfg.precision : 2,
				};
			} else if (family === "system_context" || kind === "system_context") {
				family = "system_context";
				kind = "system_context";
				const rawCfg = val.config && typeof val.config === "object" ? val.config : val;
				val = {
					sys_token: rawCfg.sys_token || "user",
					sys_role: rawCfg.sys_role || "",
				};
			}

			kind = kind || availableStrategies.value[0]?.kind || "date_time";
			activeKind.value = kind;

			const strategy = getStrategy(kind);
			if (strategy) {
				// Merge default state with provided config
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

			let config;
			if (newKind === "collection") {
				const { source, operation, target_field, condition } = newState;
				config = {
					family: "collection",
					operation: operation || "any",
					config: {
						source: source || "",
						target_field: target_field || "",
						condition: condition || null,
					},
					kind: "collection",
				};
			} else if (newKind === "text") {
				const { operation, config: innerConfig } = newState;
				config = {
					family: "text",
					operation: operation || "combine",
					config: innerConfig || {},
					kind: "text",
				};
			} else if (newKind === "date_time") {
				const { operation, config: innerConfig } = newState;
				config = {
					family: "date_time",
					operation: operation || "calculate",
					config: innerConfig || {},
					kind: "date_time",
				};
			} else if (newKind === "lookup") {
				const {
					doctype_mode,
					target_doctype,
					doctype_source,
					record_source_type,
					record_field,
					fetch_field,
				} = newState;
				config = {
					family: "lookup",
					operation: "fetch",
					kind: "lookup",
					config: {
						doctype_mode: doctype_mode || "static",
						target_doctype: target_doctype || "",
						doctype_source: doctype_source || "",
						record_source_type: record_source_type || "doc_field",
						record_field: record_field || "",
						fetch_field: fetch_field || "",
					},
				};
			} else if (newKind === "math_formula") {
				const { field_a, math_op, field_b_type, field_b, constant_b, precision } = newState;
				config = {
					family: "math",
					operation: "formula",
					kind: "math_formula",
					config: {
						field_a: field_a || "",
						math_op: math_op || "+",
						field_b_type: field_b_type || "field",
						field_b: field_b || "",
						constant_b: constant_b !== undefined ? constant_b : 0,
						precision: precision !== undefined ? precision : 2,
					},
				};
			} else if (newKind === "system_context") {
				const { sys_token, sys_role } = newState;
				config = {
					family: "system_context",
					operation: "get",
					kind: "system_context",
					config: {
						sys_token: sys_token || "user",
						sys_role: sys_role || "",
					},
				};
			} else {
				config = { ...newState, kind: newKind };
			}

			const flatStateForCompile =
				newKind === "collection" ||
				newKind === "text" ||
				newKind === "date_time" ||
				newKind === "lookup" ||
				newKind === "math_formula" ||
				newKind === "system_context"
					? { ...newState, kind: newKind }
					: config;

			const label = strategy.compileToLabel(flatStateForCompile);
			const expression = strategy.compileToCode(flatStateForCompile);

			// Run validation
			if (strategy.validate) {
				const validation = strategy.validate(flatStateForCompile, props);
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
