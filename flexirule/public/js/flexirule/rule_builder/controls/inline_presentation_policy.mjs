/**
 * Pure inline-presentation decision policy shared across GenericGrid, TreeBuilder, and consumers.
 */

export function resolvePresentationMode(rawMode) {
	const mode = String(rawMode || "")
		.trim()
		.toLowerCase();
	if (mode === "summary" || mode === "form" || mode === "hybrid") {
		return mode;
	}
	return "hybrid";
}

export function getInlinePresentation({
	mode = "hybrid",
	isNew = false,
	isValid = true,
	isEditing = false,
	readOnly = false,
	hasSummary = true,
} = {}) {
	const resolvedMode = resolvePresentationMode(mode);
	const canEdit = !readOnly;

	if (!hasSummary) {
		return {
			mode: resolvedMode,
			presentation: "editor",
			canToggle: false,
			canEdit,
		};
	}

	if (resolvedMode === "form") {
		return {
			mode: resolvedMode,
			presentation: "editor",
			canToggle: false,
			canEdit,
		};
	}

	const canToggle = !readOnly;

	if (resolvedMode === "summary") {
		const presentation = isEditing ? "editor" : "summary";
		return {
			mode: resolvedMode,
			presentation,
			canToggle,
			canEdit,
		};
	}

	// Hybrid mode:
	// - Explicitly editing -> editor
	// - New or invalid -> editor
	// - Existing and valid -> summary
	const presentation = isEditing || isNew || !isValid ? "editor" : "summary";

	return {
		mode: resolvedMode,
		presentation,
		canToggle,
		canEdit,
	};
}
