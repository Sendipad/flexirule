/**
 * Pure FlexValue serialization helpers shared by controls and regression tests.
 */

/**
 * Normalize the selected values for membership operators to the JSON type
 * expected by the backend condition contract.
 */
export function parseListElements(value, targetFieldType) {
	let rawList = [];
	if (Array.isArray(value)) {
		rawList = value;
	} else if (typeof value === "string") {
		rawList = value
			.split(",")
			.map((item) => item.trim())
			.filter(Boolean);
	} else if (value !== null && value !== undefined && value !== "") {
		rawList = [value];
	}

	const isInt = targetFieldType === "Int" || targetFieldType === "integer";
	const isFloat = ["Float", "Currency", "Percent", "decimal"].includes(targetFieldType);

	return rawList.map((item) => {
		if (typeof item !== "string") return item;

		const trimmed = item.trim();
		if (targetFieldType === "Check" || targetFieldType === "boolean") {
			const normalized = trimmed.toLowerCase();
			if (["1", "yes", "true", "on"].includes(normalized)) return 1;
			if (["0", "no", "false", "off"].includes(normalized)) return 0;
			return trimmed;
		}
		if (isInt) {
			const parsed = Number.parseInt(trimmed, 10);
			return Number.isNaN(parsed) ? trimmed : parsed;
		}
		if (isFloat) {
			const parsed = Number.parseFloat(trimmed);
			return Number.isNaN(parsed) ? trimmed : parsed;
		}
		return trimmed;
	});
}
