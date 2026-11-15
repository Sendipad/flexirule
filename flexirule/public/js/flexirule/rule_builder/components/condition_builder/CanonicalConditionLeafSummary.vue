<template>
	<div class="canonical-leaf-summary">
		<span class="leaf-operand font-weight-medium">{{ leftSummary }}</span>
		<span class="leaf-operator font-weight-semibold mx-1 text-primary">{{
			operatorLabel
		}}</span>
		<span v-if="!isUnary" class="leaf-operand font-weight-medium text-dark">{{
			rightSummary
		}}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { isOperatorUnary } from "./canonical_condition_validation.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
	docFields: { type: Array, default: () => [] },
});

const isUnary = computed(() => {
	return isOperatorUnary(props.node?.operator, props.contract);
});

const FRIENDLY_OPERATOR_WORDS = {
	eq: "is",
	ne: "is not",
	gt: "is greater than",
	gte: "is greater than or equal",
	lt: "is less than",
	lte: "is less than or equal",
	in: "is one of",
	not_in: "is not one of",
	contains: "contains",
	not_contains: "does not contain",
	starts_with: "starts with",
	ends_with: "ends with",
	is_set: "is set",
	is_not_set: "is not set",
	is_empty: "is empty",
	is_not_empty: "is not empty",
	is_submittable: "is submittable",
	has_field: "has field",
};

const operatorLabel = computed(() => {
	const op = props.node.operator;
	if (FRIENDLY_OPERATOR_WORDS[op]) {
		return FRIENDLY_OPERATOR_WORDS[op];
	}
	const spec = props.contract?.operators?.[op];
	return spec?.label || op || "is";
});

function resolveFriendlyFieldLabel(pathStr) {
	if (!pathStr) return __("Select field");
	const fields = props.docFields || [];
	const match = fields.find((f) => {
		const val = f.value || f;
		return val === pathStr || val === pathStr.replace(/^(doc|old_doc|vars|row)\./, "");
	});
	if (match) {
		const label = match.label || match.value;
		const parenMatch = label.match(/\(([^)]+)\)/);
		if (parenMatch && parenMatch[1]) {
			return parenMatch[1].trim();
		}
		return label.replace(/^(doc|old_doc|vars|caller|rule)\./, "");
	}

	const parts = pathStr.split(".").filter(Boolean);
	if (parts.length > 1) {
		const scope = parts[0];
		const field = parts.slice(1).join(" ");
		const capitalized = field.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
		if (scope === "old_doc") return `Previous ${capitalized}`;
		if (scope === "row") return capitalized;
		return capitalized;
	}
	return pathStr.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

const FRIENDLY_RESOLVER_NAMES = {
	"math.formula": "Calculation",
	"date.calculate": "Date calculation",
	"date.diff": "Time difference",
	"date.format": "Formatted date",
	"text.combine": "Combined text",
	"text.format": "Formatted text",
	"text.normalize": "Normalized text",
	"lookup.fetch": "Linked record lookup",
	"collection.any": "Matching table item",
	"collection.all": "All table items",
	"collection.none": "No table items",
	"system_context.get": "System setting",
};

function summarizeFlexValue(val, isLeft = false) {
	if (!val || typeof val !== "object") {
		return val != null && val !== "" ? String(val) : __("(empty)");
	}

	if (val.mode === "variable") {
		const path = val.path || {};
		const scope = path.scope || "doc";
		const segments = Array.isArray(path.segments) ? path.segments : [];
		const rawPath = segments.length ? `${scope}.${segments.join(".")}` : scope;
		return resolveFriendlyFieldLabel(rawPath);
	}

	if (val.mode === "static") {
		if (val.value === null) return "None";
		if (typeof val.value === "boolean") return val.value ? "Yes" : "No";
		if (Array.isArray(val.value)) {
			return val.value.length ? val.value.join(", ") : __("(empty list)");
		}
		return val.value !== "" && val.value !== undefined ? String(val.value) : __("(empty)");
	}

	if (val.mode === "resolver") {
		const key = `${val.family || ""}.${val.operation || ""}`;
		const friendlyName = FRIENDLY_RESOLVER_NAMES[key];
		if (friendlyName) return `[${friendlyName}]`;
		const fam = val.family ? val.family.replace(/_/g, " ") : "calculation";
		return `[${fam}]`;
	}

	if (val.mode === "template") {
		if (Array.isArray(val.segments)) {
			const text = val.segments
				.map((s) =>
					s.type === "text" ? s.value : s.value ? summarizeFlexValue(s.value) : ""
				)
				.join("");
			if (text.trim()) return `"${text}"`;
		}
		return "[Template]";
	}

	return __("(unconfigured)");
}

const leftSummary = computed(() => summarizeFlexValue(props.node.left, true));
const rightSummary = computed(() => summarizeFlexValue(props.node.right, false));
</script>

<style scoped>
.canonical-leaf-summary {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-1, 4px);
	font-size: var(--fxr-text-sm, 13px);
	color: var(--fxr-text-strong, #1f2937);
	padding: 2px 4px;
}
.leaf-operator {
	color: var(--fxr-accent, #2563eb);
}
.leaf-operand {
	color: var(--fxr-text-strong, #111827);
}
</style>
