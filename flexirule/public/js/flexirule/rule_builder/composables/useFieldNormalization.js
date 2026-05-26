import { computed } from "vue";

/**
 * useFieldNormalization
 * Shared logic for normalizing field definitions based on dependency states.
 * Used in SchemaRenderer and FlexiGrid.
 */
export function useFieldNormalization(engine) {
	function getFieldState(field, contextId = "root") {
		if (engine && typeof engine.getFieldState === "function") {
			return (
				engine.getFieldState(field, contextId) || {
					reqd: field.reqd,
					read_only: field.read_only,
					hidden: field.hidden,
					options: field.options,
				}
			);
		}

		if (!engine)
			return {
				reqd: field.reqd,
				read_only: field.read_only,
				hidden: field.hidden,
				options: field.options,
			};

		return (
			engine.dependency_states?.[contextId]?.[field.fieldname] || {
				reqd: field.reqd,
				read_only: field.read_only,
				hidden: field.hidden,
				options: field.options,
			}
		);
	}

	function getNormalizedDf(field, contextId = "root", globalReadOnly = false) {
		if (engine && typeof engine.getNormalizedDf === "function") {
			const customDf = engine.getNormalizedDf(field, contextId);
			if (customDf) {
				return {
					...customDf,
					read_only: customDf.read_only || globalReadOnly,
				};
			}
		}

		const state = getFieldState(field, contextId);
		return {
			...field,
			reqd: state.reqd ?? field.reqd,
			read_only: state.read_only || field.read_only || globalReadOnly,
			hidden: state.hidden ?? field.hidden,
			options: state.options ?? field.options,
		};
	}

	return {
		getFieldState,
		getNormalizedDf,
	};
}
