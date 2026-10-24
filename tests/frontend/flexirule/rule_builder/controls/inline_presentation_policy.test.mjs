import assert from "node:assert/strict";
import { resolvePresentationMode, getInlinePresentation } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/inline_presentation_policy.mjs";

// Mode normalization
assert.equal(resolvePresentationMode("hybrid"), "hybrid");
assert.equal(resolvePresentationMode("HYBRID"), "hybrid");
assert.equal(resolvePresentationMode("summary"), "summary");
assert.equal(resolvePresentationMode("Summary"), "summary");
assert.equal(resolvePresentationMode("form"), "form");
assert.equal(resolvePresentationMode("Form"), "form");
assert.equal(resolvePresentationMode("unknown"), "hybrid");
assert.equal(resolvePresentationMode(null), "hybrid");
assert.equal(resolvePresentationMode(""), "hybrid");

// Form mode always presents editor and cannot toggle
assert.deepEqual(
	getInlinePresentation({
		mode: "form",
		isNew: false,
		isValid: true,
		isEditing: false,
		readOnly: false,
	}),
	{ mode: "form", presentation: "editor", canToggle: false, canEdit: true }
);
assert.deepEqual(getInlinePresentation({ mode: "form", readOnly: true }), {
	mode: "form",
	presentation: "editor",
	canToggle: false,
	canEdit: false,
});

// Without summary, presentation is always editor
assert.deepEqual(getInlinePresentation({ mode: "summary", hasSummary: false }), {
	mode: "summary",
	presentation: "editor",
	canToggle: false,
	canEdit: true,
});

// Summary mode:
// Existing valid item -> summary
assert.deepEqual(
	getInlinePresentation({
		mode: "summary",
		isNew: false,
		isValid: true,
		isEditing: false,
		readOnly: false,
	}),
	{ mode: "summary", presentation: "summary", canToggle: true, canEdit: true }
);
// Explicitly editing -> editor
assert.deepEqual(
	getInlinePresentation({
		mode: "summary",
		isNew: false,
		isValid: true,
		isEditing: true,
		readOnly: false,
	}),
	{ mode: "summary", presentation: "editor", canToggle: true, canEdit: true }
);
// Invalid item in summary mode (not editing) still renders summary unless explicitly editing
assert.deepEqual(
	getInlinePresentation({
		mode: "summary",
		isNew: false,
		isValid: false,
		isEditing: false,
		readOnly: false,
	}),
	{ mode: "summary", presentation: "summary", canToggle: true, canEdit: true }
);

// Hybrid mode:
// Existing valid item -> summary
assert.deepEqual(
	getInlinePresentation({
		mode: "hybrid",
		isNew: false,
		isValid: true,
		isEditing: false,
		readOnly: false,
	}),
	{ mode: "hybrid", presentation: "summary", canToggle: true, canEdit: true }
);
// New item -> editor
assert.deepEqual(
	getInlinePresentation({
		mode: "hybrid",
		isNew: true,
		isValid: true,
		isEditing: false,
		readOnly: false,
	}),
	{ mode: "hybrid", presentation: "editor", canToggle: true, canEdit: true }
);
// Existing invalid item -> editor
assert.deepEqual(
	getInlinePresentation({
		mode: "hybrid",
		isNew: false,
		isValid: false,
		isEditing: false,
		readOnly: false,
	}),
	{ mode: "hybrid", presentation: "editor", canToggle: true, canEdit: true }
);
// Explicitly editing valid item -> editor
assert.deepEqual(
	getInlinePresentation({
		mode: "hybrid",
		isNew: false,
		isValid: true,
		isEditing: true,
		readOnly: false,
	}),
	{ mode: "hybrid", presentation: "editor", canToggle: true, canEdit: true }
);

// Read-only behavior:
// Read-only existing valid item in Hybrid -> summary, canToggle false, canEdit false
assert.deepEqual(
	getInlinePresentation({
		mode: "hybrid",
		isNew: false,
		isValid: true,
		isEditing: false,
		readOnly: true,
	}),
	{ mode: "hybrid", presentation: "summary", canToggle: false, canEdit: false }
);
// Read-only invalid item in Hybrid -> editor (disabled form for inspection), canToggle false, canEdit false
assert.deepEqual(
	getInlinePresentation({
		mode: "hybrid",
		isNew: false,
		isValid: false,
		isEditing: false,
		readOnly: true,
	}),
	{ mode: "hybrid", presentation: "editor", canToggle: false, canEdit: false }
);

console.log("inline presentation policy unit tests passed");
