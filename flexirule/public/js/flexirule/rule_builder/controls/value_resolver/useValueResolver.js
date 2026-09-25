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

			// Normalize canonical family / legacy child_aggregation structure
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
			}

			kind = kind || availableStrategies.value[0]?.kind || "date_formula";
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
			// We delay resetting the flag slightly to allow watchers to skip the first pulse
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
			} else {
				config = { ...newState, kind: newKind };
			}

			const flatStateForCompile =
				newKind === "collection" ? { ...newState, kind: "collection" } : config;

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
