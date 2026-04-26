/**
 * Compile a ConditionBuilder tree into a Python/Jinja boolean expression string.
 *
 * Input: { op: "and", conditions: [ { left: { ref: "doc.status" }, op: "==", right: { value: "Open" } }, ... ] }
 * Output: "doc.status == 'Open' and doc.total > 100"
 */

const SIMPLE_PATH_RE = /^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$/;
const ALLOWED_ROOTS = new Set([
	"doc",
	"old_doc",
	"vars",
	"item",
	"loop",
	"caller",
	"rule",
	"doctype",
]);

export function normalizeTemplatePath(path, knownVarRoots = []) {
	const raw = String(path || "").trim();
	if (!raw || !SIMPLE_PATH_RE.test(raw)) return raw;

	const roots = new Set(knownVarRoots || []);
	const root = raw.split(".", 1)[0];
	if (ALLOWED_ROOTS.has(root)) return raw;
	if (roots.has(root)) return raw;
	return `doc.${raw}`;
}

function normalizeInlineJinja(content, knownVarRoots = []) {
	if (!content || typeof content !== "string") return content || "";
	return content.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_m, expr) => {
		const normalized = normalizeTemplatePath(expr, knownVarRoots);
		if (!normalized) return "";
		return `{{ ${normalized} }}`;
	});
}

export function compileConditionTree(node, knownVarRoots = []) {
	if (!node) return "";
	// Raw expression stored during Jinja import – pass through as-is
	if (node._raw_expr !== undefined) return node._raw_expr || "True";

	// Group node (and/or)
	if (Array.isArray(node.conditions)) {
		if (!node.conditions.length) return "True";

		const parts = node.conditions
			.map((child) => compileConditionTree(child, knownVarRoots))
			.filter(Boolean);

		if (!parts.length) return "True";
		if (parts.length === 1) return parts[0];

		const joiner = node.op === "or" ? " or " : " and ";
		return "(" + parts.join(joiner) + ")";
	}

	// Collection node (any/all)
	if (node.collection !== undefined) {
		const alias = node.alias || "item";
		const collection = normalizeTemplatePath(node.collection || "[]", knownVarRoots) || "[]";
		const whereExpr = node.where ? compileConditionTree(node.where, knownVarRoots) : "True";
		const quantifier = node.op === "all" ? "all" : "any";
		return `${quantifier}(${whereExpr} for ${alias} in ${collection})`;
	}

	// Simple condition (left op right)
	if (node.left !== undefined) {
		const left = normalizeTemplatePath(node.left.ref || "", knownVarRoots);
		if (!left) return "";

		const op = node.op || "==";

		// Unary operators
		if (op === "is_set") return left;
		if (op === "is_not_set") return `not ${left}`;

		// Get right value
		let right;
		if (node.right?.ref) {
			right = normalizeTemplatePath(node.right.ref, knownVarRoots);
		} else {
			right = formatValue(node.right?.value);
		}

		// Map operators
		const opMap = {
			"==": "==",
			"!=": "!=",
			">": ">",
			"<": "<",
			">=": ">=",
			"<=": "<=",
			in: "in",
			"not in": "not in",
			like: "like",
			"not like": "not like",
			contains: "in",
			not_contains: "not in",
		};

		const pyOp = opMap[op] || op;

		if (op === "contains" || op === "not_contains") {
			// Reverse: right in left
			return `${right} ${pyOp} ${left}`;
		}

		return `${left} ${pyOp} ${right}`;
	}

	return "";
}

function formatValue(val) {
	if (val === null || val === undefined) return "None";
	if (typeof val === "boolean") return val ? "True" : "False";
	if (typeof val === "number") return String(val);
	if (Array.isArray(val)) {
		// Could be a [DocType, value] tuple for links
		if (val.length === 2 && typeof val[0] === "string") {
			return formatValue(val[1]);
		}
		return "[" + val.map(formatValue).join(", ") + "]";
	}
	// String - quote it
	const escaped = String(val).replace(/'/g, "\\'");
	return `'${escaped}'`;
}

/**
 * Compile segments array to a Jinja template string.
 */
export function compileSegmentsToJinja(segments, options = {}) {
	const knownVarRoots = options.knownVarRoots || [];
	if (!Array.isArray(segments)) return "";
	return segments
		.map((seg) => {
			if (!seg) return "";
			const t = (seg.type || "text").toLowerCase();

			if (t === "text")
				return normalizeInlineJinja(seg.content || seg.text || "", knownVarRoots);

			if (t === "variable") {
				const p = normalizeTemplatePath(seg.path || "", knownVarRoots);
				return p ? `{{ ${p} }}` : "";
			}

			if (t === "conditional") {
				const condExpr = seg.condition
					? compileConditionTree(seg.condition, knownVarRoots)
					: "True";
				let out = `{% if ${condExpr} %}`;
				out += compileSegmentsToJinja(seg.then_segments || [], { knownVarRoots });

				// elif branches
				if (Array.isArray(seg.elif_branches)) {
					for (const elif of seg.elif_branches) {
						const elifExpr = elif.condition
							? compileConditionTree(elif.condition, knownVarRoots)
							: "True";
						out += `{% elif ${elifExpr} %}`;
						out += compileSegmentsToJinja(elif.segments || [], { knownVarRoots });
					}
				}

				// else
				const elseContent = compileSegmentsToJinja(seg.else_segments || [], {
					knownVarRoots,
				});
				if (elseContent) {
					out += `{% else %}${elseContent}`;
				}

				out += "{% endif %}";
				return out;
			}

			if (t === "loop") {
				const iterable = normalizeTemplatePath(seg.iterable || "", knownVarRoots) || "[]";
				const iterator = seg.iterator || "item";
				const nestedRoots = [...knownVarRoots, iterator];

				let out = `{% for ${iterator} in ${iterable} %}`;
				out += compileSegmentsToJinja(seg.segments || [], { knownVarRoots: nestedRoots });
				out += `{% endfor %}`;

				return out;
			}

			return "";
		})
		.join("");
}

// ─── Jinja → Segments round-trip parser ────────────────────────────────────────

function _genKey() {
	return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function _tokenize(template) {
	const tokens = [];
	const re = /(\{\{-?\s*[\s\S]*?-?\}\}|\{%-?\s*[\s\S]*?-?%\})/g;
	let lastIdx = 0;
	let m;
	while ((m = re.exec(template)) !== null) {
		if (m.index > lastIdx)
			tokens.push({ kind: "text", value: template.slice(lastIdx, m.index) });
		const raw = m[1];
		if (raw.startsWith("{{")) {
			const expr = raw
				.replace(/^\{\{-?\s*/, "")
				.replace(/\s*-?\}\}$/, "")
				.trim();
			tokens.push({ kind: "var", expr });
		} else {
			const inner = raw
				.replace(/^\{%-?\s*/, "")
				.replace(/\s*-?%\}$/, "")
				.trim();
			const si = inner.search(/\s/);
			const tag = si === -1 ? inner : inner.slice(0, si);
			const args = si === -1 ? "" : inner.slice(si + 1).trim();
			tokens.push({ kind: "tag", tag, args });
		}
		lastIdx = m.index + m[0].length;
	}
	if (lastIdx < template.length) tokens.push({ kind: "text", value: template.slice(lastIdx) });
	return tokens;
}

function _mergeText(segments, value) {
	if (!value) return;
	const last = segments[segments.length - 1];
	if (last && last.type === "text") {
		last.content += value;
	} else {
		segments.push({ type: "text", content: value, _key: _genKey() });
	}
}

function _parseLevel(tokens, startIdx, stopTags) {
	const segments = [];
	let i = startIdx;
	const isStop = (tok) => tok && tok.kind === "tag" && stopTags && stopTags.includes(tok.tag);

	while (i < tokens.length) {
		const tok = tokens[i];
		if (isStop(tok)) return { segments, nextIdx: i };

		if (tok.kind === "text") {
			_mergeText(segments, tok.value);
			i++;
		} else if (tok.kind === "var") {
			segments.push({ type: "variable", path: tok.expr, _key: _genKey() });
			i++;
		} else if (tok.kind === "tag") {
			if (tok.tag === "if") {
				i++;
				const thenR = _parseLevel(tokens, i, ["elif", "else", "endif"]);
				i = thenR.nextIdx;
				const condSeg = {
					type: "conditional",
					condition: { op: "and", conditions: [], _raw_expr: tok.args },
					then_segments: thenR.segments,
					elif_branches: [],
					else_segments: [],
					_key: _genKey(),
				};
				while (i < tokens.length) {
					const t = tokens[i];
					if (!t || t.kind !== "tag") break;
					if (t.tag === "endif") {
						i++;
						break;
					}
					if (t.tag === "elif") {
						i++;
						const eR = _parseLevel(tokens, i, ["elif", "else", "endif"]);
						i = eR.nextIdx;
						condSeg.elif_branches.push({
							condition: { op: "and", conditions: [], _raw_expr: t.args },
							segments: eR.segments,
						});
					} else if (t.tag === "else") {
						i++;
						const elR = _parseLevel(tokens, i, ["endif"]);
						i = elR.nextIdx;
						condSeg.else_segments = elR.segments;
					} else break;
				}
				segments.push(condSeg);
			} else if (tok.tag === "for") {
				const fm = tok.args.match(/^(\w+)\s+in\s+(.+)$/);
				i++;
				if (fm) {
					const bodyR = _parseLevel(tokens, i, ["endfor"]);
					i = bodyR.nextIdx;
					if (i < tokens.length && tokens[i]?.tag === "endfor") i++;
					segments.push({
						type: "loop",
						iterator: fm[1],
						iterable: fm[2].trim(),
						segments: bodyR.segments,
						_key: _genKey(),
					});
				}
			} else {
				_mergeText(segments, `{% ${tok.tag}${tok.args ? " " + tok.args : ""} %}`);
				i++;
			}
		} else {
			i++;
		}
	}
	return { segments, nextIdx: i };
}

/**
 * Parse a raw Jinja template string into the FlexiRule segment array.
 * Handles: {{ var }}, {% if/elif/else/endif %}, {% for x in y/endfor %}
 */
export function parseJinjaToSegments(template) {
	if (!template || !template.trim()) return [];
	const tokens = _tokenize(template);
	const { segments } = _parseLevel(tokens, 0, []);
	return segments;
}
