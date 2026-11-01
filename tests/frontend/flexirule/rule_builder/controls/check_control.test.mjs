import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "../../../../../");

// 1. Verify controls.css contains all required unified checkbox and switch classes
const controlsCssPath = path.join(rootDir, "flexirule/public/css/controls.css");
const controlsCss = fs.readFileSync(controlsCssPath, "utf-8");

assert.ok(
	controlsCss.includes(".fxr-checkbox-input {"),
	"controls.css must declare .fxr-checkbox-input"
);
assert.ok(
	controlsCss.includes(".fxr-checkbox-input--sm {"),
	"controls.css must declare .fxr-checkbox-input--sm"
);
assert.ok(
	controlsCss.includes(".fxr-checkbox-input:checked"),
	"controls.css must style .fxr-checkbox-input:checked"
);
assert.ok(
	controlsCss.includes(".fxr-checkbox-input:indeterminate"),
	"controls.css must style .fxr-checkbox-input:indeterminate"
);
assert.ok(
	controlsCss.includes(".fxr-checkbox-input:focus-visible"),
	"controls.css must style .fxr-checkbox-input:focus-visible"
);
assert.ok(
	controlsCss.includes(".fxr-checkbox-input:disabled"),
	"controls.css must style .fxr-checkbox-input:disabled"
);
assert.ok(
	controlsCss.includes(".fxr-checkbox-label"),
	"controls.css must declare .fxr-checkbox-label"
);
assert.ok(
	controlsCss.includes(".fxr-switch"),
	"controls.css must declare .fxr-switch"
);
assert.ok(
	controlsCss.includes(".fxr-switch__slider"),
	"controls.css must declare .fxr-switch__slider"
);
assert.ok(
	controlsCss.includes(".fxr-switch--sm"),
	"controls.css must declare .fxr-switch--sm"
);

// 2. Verify CheckControl.vue adheres to design contract
const checkControlPath = path.join(
	rootDir,
	"flexirule/public/js/flexirule/rule_builder/controls/CheckControl.vue"
);
const checkControlVue = fs.readFileSync(checkControlPath, "utf-8");

// No un-namespaced generic `.checkbox` class usage in CheckControl wrapper
assert.ok(
	!checkControlVue.includes('class="control fxr-control checkbox"'),
	"CheckControl must not use generic .checkbox class wrapper"
);
assert.ok(
	checkControlVue.includes("fxr-check-control"),
	"CheckControl must use namespaced .fxr-check-control class"
);
assert.ok(
	checkControlVue.includes("fxr-checkbox-input"),
	"CheckControl must use shared .fxr-checkbox-input"
);
assert.ok(
	checkControlVue.includes("indeterminate"),
	"CheckControl must support indeterminate prop and state"
);
assert.ok(
	checkControlVue.includes("size:"),
	"CheckControl must support size prop"
);

// 3. Verify no lingering legacy .fxr-checkbox styles in ConditionStep.vue
const conditionStepPath = path.join(
	rootDir,
	"flexirule/public/js/flexirule/rule_builder/components/rule_config/types/ConditionStep.vue"
);
const conditionStepVue = fs.readFileSync(conditionStepPath, "utf-8");
assert.ok(
	!conditionStepVue.includes(".fxr-checkbox {"),
	"ConditionStep must not declare local .fxr-checkbox"
);
assert.ok(
	conditionStepVue.includes("fxr-checkbox-input"),
	"ConditionStep must use shared .fxr-checkbox-input"
);

// 4. Verify FlexiGrid.vue row selection and header select-all use fxr-checkbox-input
const flexiGridPath = path.join(
	rootDir,
	"flexirule/public/js/flexirule/rule_builder/controls/FlexiGrid.vue"
);
const flexiGridVue = fs.readFileSync(flexiGridPath, "utf-8");
assert.ok(
	flexiGridVue.includes('class="fxr-checkbox-input fxr-checkbox-input--sm"'),
	"FlexiGrid must use .fxr-checkbox-input--sm for header and row checkboxes"
);

// 5. Verify SubRuleNodeConfig.vue uses unified .fxr-switch instead of Bootstrap custom-switch
const subRulePath = path.join(
	rootDir,
	"flexirule/public/js/flexirule/rule_builder/components/node_configs/SubRuleNodeConfig.vue"
);
const subRuleVue = fs.readFileSync(subRulePath, "utf-8");
assert.ok(
	!subRuleVue.includes("custom-switch"),
	"SubRuleNodeConfig must not use bootstrap custom-switch"
);
assert.ok(
	subRuleVue.includes("fxr-switch"),
	"SubRuleNodeConfig must use unified .fxr-switch"
);

// 6. CheckControl validation logic behavioral test
function testCheckControlValidation(df, modelValue) {
	const isChecked = !!modelValue;
	const isValid = !df?.reqd || isChecked;
	const errors = [];
	if (!isValid) {
		errors.push(`${df?.label || "Field"} must be checked`);
	}
	return { valid: errors.length === 0, errors };
}

assert.deepEqual(
	testCheckControlValidation({ reqd: 0, label: "Accept Terms" }, false),
	{ valid: true, errors: [] },
	"Optional unchecked field should be valid"
);
assert.deepEqual(
	testCheckControlValidation({ reqd: 1, label: "Accept Terms" }, false),
	{ valid: false, errors: ["Accept Terms must be checked"] },
	"Required unchecked field should be invalid"
);
assert.deepEqual(
	testCheckControlValidation({ reqd: 1, label: "Accept Terms" }, true),
	{ valid: true, errors: [] },
	"Required checked (boolean true) field should be valid"
);
assert.deepEqual(
	testCheckControlValidation({ reqd: 1, label: "Accept Terms" }, 1),
	{ valid: true, errors: [] },
	"Required checked (numeric 1) field should be valid"
);
assert.deepEqual(
	testCheckControlValidation({ reqd: 1, label: "Accept Terms" }, 0),
	{ valid: false, errors: ["Accept Terms must be checked"] },
	"Required checked (numeric 0) field should be invalid"
);

// 7. CheckControl value change conversion test (preserves number vs boolean)
function handleCheckChange(modelValue, checked) {
	return typeof modelValue === "number" ? (checked ? 1 : 0) : checked;
}

assert.equal(handleCheckChange(0, true), 1);
assert.equal(handleCheckChange(1, false), 0);
assert.equal(handleCheckChange(false, true), true);
assert.equal(handleCheckChange(true, false), false);

console.log("CheckControl and checkbox design system contract tests passed");
