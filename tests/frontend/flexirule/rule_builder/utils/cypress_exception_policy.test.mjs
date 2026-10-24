import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

function listFiles(directory) {
	return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
		const path = join(directory, entry.name);
		if (entry.isDirectory()) return listFiles(path);
		return /\.(?:js|mjs|cjs|ts)$/.test(entry.name) ? [path] : [];
	});
}

test("Cypress sources do not globally suppress uncaught application exceptions", () => {
	const handlerPattern = /Cypress\.on\s*\(\s*["']uncaught:exception["']/;
	const offenders = listFiles("cypress").filter((path) =>
		handlerPattern.test(readFileSync(path, "utf8"))
	);

	assert.deepEqual(
		offenders,
		[],
		"Unexpected uncaught:exception handlers can hide real application failures"
	);
});
