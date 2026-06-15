import { ref, computed, watch } from "vue";
import { getStrategy, getAllStrategies } from "./strategies";

export function useValueResolver(props, emit) {
	const localState = ref({});
	const activeKind = ref(null);
	const isValid = ref(true);
	const errors = ref([]);

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
		let val = props.modelValue || {};
		if (val.mode && val.config) {
			val = val.config;
		}

		const kind = val.kind || availableStrategies.value[0]?.kind || "date_formula";
		activeKind.value = kind;

		const strategy = getStrategy(kind);
		if (strategy) {
			// Merge default state with provided config
			localState.value = {
				...strategy.defaultState(props),
				...val,
			};
		}
	};

	// Watch for kind changes to reset state to defaults
	watch(activeKind, (newKind, oldKind) => {
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
