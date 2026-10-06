import {
	createFilterLeaf,
	createFilterGroup,
	deserializeFilterPayload,
	serializeFilterTree,
	validateFilterTree,
	FilterTreeValidationError,
} from "../../flexirule/public/js/flexirule/rule_builder/components/rule_config/filter_tree_adapter.js";

describe("Query Filter Tree adapter", () => {
	it("keeps a newly created blank leaf as editable UI state", () => {
		const leaf = createFilterLeaf({ doctype: "User", createId: () => "leaf-1" });

		expect(leaf).to.deep.include({
			id: "leaf-1",
			type: "leaf",
			doctype: "User",
			field: "",
			operator: "=",
		});
		expect(leaf.value).to.deep.equal({ mode: "static", value: "" });
		expect(validateFilterTree(createFilterGroup({ children: [leaf] })).valid).to.eq(false);
	});

	it("rejects an incomplete leaf instead of serializing it as an executable filter", () => {
		const tree = createFilterGroup({
			children: [createFilterLeaf({ doctype: "User", createId: () => "leaf-1" })],
		});

		expect(() => serializeFilterTree(tree)).to.throw(FilterTreeValidationError);
	});

	it("serializes a valid leaf and preserves its FlexValue structure", () => {
		const tree = createFilterGroup({
			children: [{
				id: "leaf-1",
				type: "leaf",
				doctype: "User",
				field: "email",
				operator: "=",
				value: { mode: "variable", value: "vars.email" },
			}],
		});

		expect(serializeFilterTree(tree)).to.deep.equal([
			"User",
			"email",
			"=",
			{ mode: "variable", value: "vars.email" },
		]);
	});

	it("preserves nested AND/OR grouping during round trip", () => {
		const payload = [
			["User", "enabled", "=", 1],
			"and",
			[
				["User", "role", "=", "System Manager"],
				"or",
				["User", "role", "=", "Administrator"],
			],
		];

		const tree = deserializeFilterPayload(payload, { createId: (() => {
			let i = 0;
			return () => "node-" + ++i;
		})() });

		expect(serializeFilterTree(tree)).to.deep.equal(payload);
	});

	it("keeps empty root distinct from an incomplete leaf", () => {
		const emptyRoot = createFilterGroup({ createId: () => "root" });
		const blankLeaf = createFilterGroup({
			createId: () => "root",
			children: [createFilterLeaf({ doctype: "User", createId: () => "leaf" })],
		});

		expect(validateFilterTree(emptyRoot, { allowEmptyRoot: true }).valid).to.eq(true);
		expect(validateFilterTree(blankLeaf, { allowEmptyRoot: true }).valid).to.eq(false);
	});
});
