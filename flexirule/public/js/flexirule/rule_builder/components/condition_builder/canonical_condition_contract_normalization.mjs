/**
 * Pure JS normalization helper for Canonical Condition Contract DTO.
 * Free of Vue dependencies so it can be imported cleanly in Node test environments.
 */

export function normalizeConditionContract(rawContract) {
	if (!rawContract || typeof rawContract !== "object") {
		return null;
	}

	const rawOperators = rawContract.operators;
	const operatorMap = {};
	const operatorList = [];

	if (Array.isArray(rawOperators)) {
		for (const op of rawOperators) {
			if (op && op.id) {
				const normalizedOp = {
					...op,
					label: op.label || op.id,
					arity: typeof op.arity === "number" ? op.arity : 2,
					accepted_left_types: op.accepted_left_types || [],
					accepted_right_types: op.accepted_right_types || [],
					fieldtypes: op.fieldtypes || null,
					legacy_aliases: op.legacy_aliases || [],
				};
				operatorMap[op.id] = normalizedOp;
				operatorList.push(normalizedOp);
			}
		}
	} else if (rawOperators && typeof rawOperators === "object") {
		for (const [id, op] of Object.entries(rawOperators)) {
			if (op) {
				const normalizedOp = {
					...op,
					id: op.id || id,
					label: op.label || id,
					arity: typeof op.arity === "number" ? op.arity : 2,
					accepted_left_types: op.accepted_left_types || [],
					accepted_right_types: op.accepted_right_types || [],
					fieldtypes: op.fieldtypes || null,
					legacy_aliases: op.legacy_aliases || [],
				};
				operatorMap[id] = normalizedOp;
				operatorList.push(normalizedOp);
			}
		}
	}

	const rawLimits = rawContract.limits || {};
	const nodeTypes = rawContract.node_types || {};
	const flexvalueModes = rawContract.flexvalue_modes || {};
	const fieldtypeValueTypes = rawContract.fieldtype_value_types;
	const rawDepth = rawLimits.condition_depth ?? rawLimits.depth;
	const rawNodes = rawLimits.condition_nodes ?? rawLimits.nodes;
	const hasCompleteContract =
		Boolean(rawContract.api_version) &&
		Boolean(rawContract.semantics_version) &&
		Boolean(nodeTypes.group && nodeTypes.comparison && nodeTypes.collection_predicate) &&
		Array.isArray(flexvalueModes.static) &&
		Array.isArray(flexvalueModes.variable?.scopes) &&
		Boolean(flexvalueModes.resolver && typeof flexvalueModes.resolver === "object") &&
		Boolean(flexvalueModes.template && typeof flexvalueModes.template === "object") &&
		Boolean(fieldtypeValueTypes && typeof fieldtypeValueTypes === "object" && Object.keys(fieldtypeValueTypes).length) &&
		Number.isInteger(rawDepth) && rawDepth > 0 &&
		Number.isInteger(rawNodes) && rawNodes > 0 &&
		operatorList.length > 0;
	if (!hasCompleteContract) return null;

	const normalizedLimits = {
		...rawLimits,
		condition_depth: rawLimits.condition_depth ?? rawLimits.depth ?? 16,
		condition_nodes: rawLimits.condition_nodes ?? rawLimits.nodes ?? 128,
		path_segments: rawLimits.path_segments ?? 8,
		template_segments: rawLimits.template_segments ?? 64,
		template_output_chars: rawLimits.template_output_chars ?? 8192,
		payload_bytes: rawLimits.payload_bytes ?? 65536,
		depth: rawLimits.condition_depth ?? rawLimits.depth ?? 16,
		nodes: rawLimits.condition_nodes ?? rawLimits.nodes ?? 128,
	};

	return {
		...rawContract,
		operators: operatorMap,
		operatorList,
		limits: normalizedLimits,
		flexvalue_modes: flexvalueModes,
		fieldtype_value_types: fieldtypeValueTypes,
	};
}
