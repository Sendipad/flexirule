/** UI validation driven only by the backend's canonical condition contract. */

const SCOPES = new Set(["doc", "old_doc", "vars", "item", "loop", "row", "caller", "rule"]);

export function validateFlexValue(value, label = "Operand") {
	const errors = [];
	if (!value || typeof value !== "object" || Array.isArray(value)) return [`${label} is missing or invalid.`];
	if (!["static", "variable", "resolver"].includes(value.mode)) return [`${label} has an unsupported value mode.`];
	if (value.mode === "variable") {
		const path = value.value ?? value.path;
		if (typeof path !== "string" || !path.trim()) errors.push(`${label} requires a variable path.`);
		else {
			const parts = path.trim().split(".");
			if (parts.length > 1 && SCOPES.has(parts[0])) parts.shift();
			if (!parts.length || parts.some((part) => !/^[A-Za-z0-9_]+$/.test(part) || part.includes("__"))) {
				errors.push(`${label} contains an invalid variable path.`);
			}
		}
	}
	if (value.mode === "resolver" && (
		typeof value.family !== "string" || !value.family ||
		typeof value.operation !== "string" || !value.operation ||
		!value.config || typeof value.config !== "object" || Array.isArray(value.config)
	)) errors.push(`${label} requires an explicitly configured canonical resolver.`);
	if (value.mode === "static" && Object.hasOwn(value, "value_type")) {
		const type = value.value_type;
		const val = value.value;
		if (type === "string" && typeof val !== "string") errors.push(`${label} must be a string.`);
		else if (type === "integer" && !(Number.isInteger(val) && typeof val === "number")) errors.push(`${label} must be an integer.`);
		else if (type === "decimal" && !(typeof val === "string" && val.trim() !== "" && Number.isFinite(Number(val)))) errors.push(`${label} must be a finite decimal string.`);
		else if (type === "boolean" && typeof val !== "boolean") errors.push(`${label} must be a boolean.`);
		else if (type === "null" && val !== null) errors.push(`${label} must be null.`);
		else if (type === "date" && !(typeof val === "string" && /^\\d{4}-\\d{2}-\\d{2}$/.test(val))) errors.push(`${label} must be an ISO date.`);
		else if (type === "datetime" && !(typeof val === "string" && !Number.isNaN(Date.parse(val)))) errors.push(`${label} must be an ISO datetime.`);
		else if (type === "time" && !(typeof val === "string" && /^\\d{2}:\\d{2}(:\\d{2}(\\.\\d+)?)?$/.test(val))) errors.push(`${label} must be an ISO time.`);
		else if (type === "list" && !Array.isArray(val)) errors.push(`${label} must be a list.`);
		else if (type === "object" && (!val || typeof val !== "object" || Array.isArray(val))) errors.push(`${label} must be an object.`);
	}
	if (value.mode === "static" && typeof value.value === "number" && !Number.isFinite(value.value)) {
		errors.push(`${label} must be a finite number.`);
	}
	return errors;
}

export function validateComparisonDomain(domain, operators = []) {
	const errors = [];
	if (!domain || domain.type !== "comparison") return ["Invalid comparison data."];
	const opMeta = operators.find((operator) => operator?.id === domain.op);
	if (!opMeta) return [domain.op ? `Unsupported condition operator: ${domain.op}.` : "Comparison operator is required."];
	errors.push(...validateFlexValue(domain.left, "Left operand"));
	if (opMeta.arity === 2) errors.push(...validateFlexValue(domain.right, "Right operand"));
	else if (Object.hasOwn(domain, "right") && domain.right != null) errors.push("Unary operators must not have a right operand.");
	return errors;
}

/** Validate the editable TreeBuilder model before it is serialized or saved. */
export function validateConditionTree(root, options = {}) {
	const { operators = [], isMandatory = false } = options;
	const errors = [];
	if (!Array.isArray(operators) || operators.length === 0) {
		return { isValid: false, errors: ["The canonical condition contract is unavailable."] };
	}
	if (!root) return { isValid: !isMandatory, errors: isMandatory ? ["Condition is required."] : [] };

	function walk(node, path = "$", rootNode = false) {
		if (!node || typeof node !== "object") {
			errors.push(`${path}: condition node is invalid.`);
			return;
		}
		if (node.type === "group") {
			if (!["and", "or"].includes(node.operator)) errors.push(`${path}: group operator must be AND or OR.`);
			const children = Array.isArray(node.children) ? node.children : [];
			if (children.length < 2 && !(rootNode && children.length === 0 && !isMandatory)) {
				errors.push(`${path}: a persisted group requires at least two children.`);
			}
			children.forEach((child, index) => walk(child, `${path}.children[${index}]`));
			return;
		}
		if (node.type === "leaf") {
			for (const error of validateComparisonDomain(node.domain, operators)) errors.push(`${path}: ${error}`);
			return;
		}
		if (node.type === "collection") {
			if (!["any", "all", "none"].includes(node.quantifier)) errors.push(`${path}: collection quantifier is invalid.`);
			if (typeof node.alias !== "string" || !/^[A-Za-z][A-Za-z0-9_]*$/.test(node.alias) || node.alias.includes("__") || SCOPES.has(node.alias)) {
				errors.push(`${path}: collection alias is invalid or reserved.`);
			}
			if (!node.collection || node.collection.mode !== "variable" || !(node.collection.value ?? node.collection.path)) {
				errors.push(`${path}: collection source must be a variable path.`);
			} else {
				errors.push(...validateFlexValue(node.collection, "Collection source").map((error) => `${path}: ${error}`));
			}
			const children = Array.isArray(node.children) ? node.children : [];
			if (!children.length) errors.push(`${path}: collection predicate requires a nested condition.`);
			children.forEach((child, index) => walk(child, `${path}.collection[${index}]`));
			return;
		}
		errors.push(`${path}: unsupported tree node type.`);
	}

	walk(root, "$", true);
	return { isValid: errors.length === 0, errors };
}
