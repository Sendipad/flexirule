import assert from "node:assert/strict";
import fs from "node:fs";

const compSource = fs.readFileSync("flexirule/public/js/flexirule/rule_builder/components/rule_config/types/AssignmentConfig.vue", "utf8");

assert.equal(compSource.includes("<GenericGrid"), true, "AssignmentConfig must use GenericGrid");
assert.equal(compSource.includes("template #header"), true, "AssignmentConfig must use GenericGrid header slot");
assert.equal(compSource.includes("Batch Assignments"), true, "AssignmentConfig must preserve Batch Assignments header card");
assert.equal(compSource.includes("validate()"), true, "AssignmentConfig must expose validate method");

console.log("AssignmentConfig refactor contract unit tests passed");
