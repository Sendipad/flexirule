import assert from "node:assert/strict";
import {
	createGroup,
	createLeaf,
	findNode,
	findParent,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_utils.mjs";
import {
	addLeaf,
	duplicateNode,
	moveNode,
	removeNode,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_commands.mjs";
import {
	GRID_CLIPBOARD_FORMAT,
	parseClipboardRows,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs";

// --- TreeBuilder duplicate and move tests ---
const tree = createGroup("and", []);
const leaf1 = addLeaf(tree, tree.id, { field: "name", operator: "=", value: "John" });
const leaf2 = addLeaf(tree, tree.id, { field: "age", operator: ">", value: 30 });

assert.equal(tree.children.length, 2);
assert.equal(tree.children[0].id, leaf1.id);
assert.equal(tree.children[1].id, leaf2.id);

// Duplicate leaf1
const dupLeaf = duplicateNode(tree, leaf1.id);
assert.ok(dupLeaf);
assert.notEqual(dupLeaf.id, leaf1.id);
assert.equal(dupLeaf.field, "name");
assert.equal(dupLeaf.value, "John");
assert.equal(tree.children.length, 3);
assert.equal(tree.children[1].id, dupLeaf.id); // inserted right after leaf1

// Move duplicated leaf to the end
assert.equal(moveNode(tree, dupLeaf.id, tree.id, tree.children.length), true);
assert.equal(tree.children[2].id, dupLeaf.id);

// Move up: from index 2 to index 1
assert.equal(moveNode(tree, dupLeaf.id, tree.id, 1), true);
assert.equal(tree.children[1].id, dupLeaf.id);

// Remove duplicated leaf
assert.ok(removeNode(tree, dupLeaf.id));
assert.equal(tree.children.length, 2);
assert.equal(findNode(tree, dupLeaf.id), null);

// --- GenericGrid row actions model & clipboard test ---
const row = { id: "row-1", label: "Test Row", value: 42 };
const serialized = JSON.stringify({
	format: GRID_CLIPBOARD_FORMAT,
	version: 1,
	rows: [row],
});

const parsed = parseClipboardRows(serialized);
assert.equal(parsed.length, 1);
assert.equal(parsed[0].id, "row-1");
assert.equal(parsed[0].label, "Test Row");
assert.equal(parsed[0].value, 42);

// Single row JSON copy format
const singleRowJson = JSON.stringify(row);
const parsedSingle = JSON.parse(singleRowJson);
assert.equal(parsedSingle.id, "row-1");

console.log("kebab action menu and row/leaf actions unit tests passed");
