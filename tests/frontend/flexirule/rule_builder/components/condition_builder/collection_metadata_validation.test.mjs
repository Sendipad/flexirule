import test from "node:test";
import assert from "node:assert/strict";
import {
	getCollectionMetadataIssues,
	getResolvedCollectionDocType,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/collection_metadata_validation.mjs";

const collection = {
	id: "items",
	type: "collection",
	collection: "doc.items",
	source: { scope: "doc", segments: ["items"] },
	children: [{ id: "leaf", type: "leaf" }],
};

test("child DocType resolves only after child metadata is loaded", () => {
	assert.equal(getResolvedCollectionDocType(collection, new Map()), "");
	assert.equal(
		getResolvedCollectionDocType(collection, new Map([["items", { status: "loading", childDocType: "Sales Invoice Item" }]])),
		""
	);
	assert.equal(
		getResolvedCollectionDocType(collection, new Map([["items", { status: "loaded", childDocType: "Sales Invoice Item" }]])),
		"Sales Invoice Item"
	);
});

test("unresolved or failed child metadata blocks condition validation", () => {
	assert.equal(getCollectionMetadataIssues(collection, new Map()).length, 1);
	assert.match(
		getCollectionMetadataIssues(collection, new Map([["items", { status: "failed", error: "metadata request failed" }]]))[0],
		/metadata request failed/
	);
	assert.deepEqual(
		getCollectionMetadataIssues(collection, new Map([["items", { status: "loaded", childDocType: "Sales Invoice Item" }]])),
		[]
	);
});

test("variable-backed collections do not require child DocType metadata", () => {
	const variableCollection = { ...collection, source: { scope: "vars", segments: ["rows"] } };
	assert.deepEqual(getCollectionMetadataIssues(variableCollection, new Map()), []);
});
