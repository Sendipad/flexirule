import assert from "node:assert/strict";
import fs from "node:fs";

const gridSource = fs.readFileSync("flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue", "utf8");
assert.equal(gridSource.includes("<slot name=\"header\" />"), true, "GenericGrid must contain a header slot");
assert.equal(gridSource.includes("class=\"fxr-generic-grid-header\""), true, "GenericGrid must contain fxr-generic-grid-header class");

console.log("generic grid header unit tests passed");
