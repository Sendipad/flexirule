/**
 * FlexiRule Text Generator Utilities
 * Handle Jinja template <-> Text segments array <-> Tiptap HTML
 */

/**
 * Compile segments array into a raw Jinja template string.
 */
export function compileSegmentsToJinja(segments, options = {}) {
	if (!segments || !Array.isArray(segments)) return "";

	return segments
		.map((seg) => {
			if (seg.type === "text") return seg.content || "";
			if (seg.type === "translation") return `{{ _("${seg.content}") }}`;
			if (seg.type === "variable") return `{{ ${seg.path} }}`;
			if (seg.type === "conditional") {
				const cond = serializeCondition(seg.condition);
				let res = `{% if ${cond} %}${compileSegmentsToJinja(seg.then_segments, options)}`;
				if (seg.elif_branches) {
					seg.elif_branches.forEach((branch) => {
						const bCond = serializeCondition(branch.condition);
						res += `{% elif ${bCond} %}${compileSegmentsToJinja(
							branch.segments,
							options
						)}`;
					});
				}
				if (seg.else_segments && seg.else_segments.length > 0) {
					res += `{% else %}${compileSegmentsToJinja(seg.else_segments, options)}`;
				}
				res += "{% endif %}";
				return res;
			}
			if (seg.type === "loop") {
				return `{% for ${seg.iterator} in ${seg.iterable} %}${compileSegmentsToJinja(
					seg.segments,
					options
				)}{% endfor %}`;
			}
			return "";
		})
		.join("");
}

/**
 * Parse a raw Jinja template string into segments array.
 */
export function parseJinjaToSegments(template) {
	if (!template || !template.trim()) return [];
	const tokens = _tokenize(template);
	const { segments } = _parseLevel(tokens, 0, []);
	return segments;
}

/**
 * Convert internal segments array into Tiptap HTML.
 * This version uses a marker-based approach to render the structure inline.
 */
export function decodeData(str) {
	if (!str) return {};
	try {
		return JSON.parse(decodeURIComponent(escape(atob(str))));
	} catch (e) {
		// Fallback for old non-encoded data
		try {
			return JSON.parse(str);
		} catch (e2) {
			console.error("Decoding error:", e2);
			return {};
		}
	}
}

export function encodeData(obj) {
	try {
		return btoa(unescape(encodeURIComponent(JSON.stringify(obj))));
	} catch (e) {
		console.error("Encoding error:", e);
		return "";
	}
}

export function convertHtmlToSegments(html) {
	if (!html) return [];
	const parser = new DOMParser();
	const doc = parser.parseFromString(html, "text/html");

	function parseRange(nodes, startIdx, endIdx) {
		const result = [];
		let i = startIdx;
		while (i < endIdx) {
			const node = nodes[i];
			if (node.nodeType === Node.TEXT_NODE) {
				const text = node.textContent;
				if (text && text.trim().length > 0) {
					const last = result[result.length - 1];
					if (last && last.type === "text") last.content += text;
					else result.push({ type: "text", content: text, _key: _genKey() });
				}
				i++;
			} else if (node.nodeType === Node.ELEMENT_NODE) {
				const dataType = node.getAttribute("data-type");
				if (dataType === "variable") {
					result.push({
						type: "variable",
						path: node.getAttribute("data-path"),
						_key: _genKey(),
					});
					i++;
				} else if (dataType === "translation") {
					const textContent = node.textContent;
					if (textContent && textContent.trim().length > 0) {
						result.push({ type: "translation", content: textContent, _key: _genKey() });
					}
					i++;
				} else if (dataType === "logic") {
					const attrs = decodeData(node.getAttribute("data-logic-type"));
					if (attrs.isStart) {
						// Find matching end for THIS start
						let skip = i + 1;
						let depth = 1;
						let elseIdx = -1;
						let endIdxInner = -1;

						while (skip < endIdx) {
							const nextNode = nodes[skip];
							if (
								nextNode.nodeType === Node.ELEMENT_NODE &&
								nextNode.getAttribute("data-type") === "logic"
							) {
								const nAttrs = decodeData(nextNode.getAttribute("data-logic-type"));
								if (nAttrs.isStart) depth++;
								else if (nAttrs.isEnd) depth--;
								else if (nAttrs.isElse && depth === 1) elseIdx = skip;

								if (depth === 0) {
									endIdxInner = skip;
									break;
								}
							}
							skip++;
						}

						const seg = { _key: attrs._key || _genKey(), type: attrs.type };
						const finalEnd = endIdxInner === -1 ? endIdx : endIdxInner;

						if (attrs.type === "conditional") {
							seg.condition = attrs.condition;
							if (elseIdx !== -1) {
								seg.then_segments = parseRange(nodes, i + 1, elseIdx);
								seg.else_segments = parseRange(nodes, elseIdx + 1, finalEnd);
							} else {
								seg.then_segments = parseRange(nodes, i + 1, finalEnd);
								seg.else_segments = [];
							}
							seg.elif_branches = []; // TODO: Handle elif badges
						} else if (attrs.type === "loop") {
							seg.iterator = attrs.iterator;
							seg.iterable = attrs.iterable;
							seg.segments = parseRange(nodes, i + 1, finalEnd);
						}
						result.push(seg);
						i = finalEnd + 1;
					} else {
						i++;
					}
				} else {
					// Recurse into children for layout elements
					result.push(...parseRange(node.childNodes, 0, node.childNodes.length));
					i++;
				}
			} else {
				i++;
			}
		}
		return result;
	}

	return parseRange(doc.body.childNodes, 0, doc.body.childNodes.length);
}

/**
 * Convert internal segments array into Tiptap HTML.
 */
export function convertSegmentsToHtml(segments, variableOptions = []) {
	if (!segments || !Array.isArray(segments)) return "<p></p>";

	const htmlParts = [];

	function getLabel(path) {
		const opt = variableOptions.find((o) => (o.value || o) === path);
		return opt ? opt.label || path : path;
	}

	function process(segs) {
		segs.forEach((seg) => {
			if (seg.type === "text") {
				const text = seg.content || "";
				const parts = text.split(/(\{\{.*?\}\})/g);
				parts.forEach((p) => {
					if (p.startsWith("{{") && p.endsWith("}}")) {
						const path = p.slice(2, -2).trim();
						const label = getLabel(path);
						htmlParts.push(
							`<span data-type="variable" data-path="${path}" data-label="${label}" class="tg-badge tg-badge-var">@${label}</span>`
						);
					} else if (p) {
						htmlParts.push(p);
					}
				});
			} else if (seg.type === "translation") {
				htmlParts.push(
					`<span data-type="translation" class="tg-badge tg-badge-trans">${seg.content}</span>`
				);
			} else if (seg.type === "variable") {
				const label = getLabel(seg.path);
				htmlParts.push(
					`<span data-type="variable" data-path="${seg.path}" data-label="${label}" class="tg-badge tg-badge-var">@${label}</span>`
				);
			} else if (seg.type === "conditional") {
				const condStr = serializeCondition(seg.condition);
				let fieldLabel = "";
				if (seg.condition?.left?.ref) fieldLabel = getLabel(seg.condition.left.ref);
				else if (seg.condition?.conditions?.[0]?.left?.ref)
					fieldLabel = getLabel(seg.condition.conditions[0].left.ref);

				const startAttrs = {
					type: "conditional",
					isStart: true,
					condition: seg.condition,
					_raw_expr: condStr,
					label: fieldLabel,
					_key: seg._key,
				};
				htmlParts.push(
					`<span data-type="logic" class="tg-badge tg-badge-if" data-logic-type='${encodeData(
						startAttrs
					)}'></span>`
				);

				process(seg.then_segments || []);

				if (seg.else_segments && seg.else_segments.length > 0) {
					const elseAttrs = { type: "conditional", isElse: true };
					htmlParts.push(
						`<span data-type="logic" class="tg-badge tg-badge-else" data-logic-type='${encodeData(
							elseAttrs
						)}'>ELSE</span>`
					);
					process(seg.else_segments);
				}

				const endAttrs = { type: "conditional", isEnd: true };
				htmlParts.push(
					`<span data-type="logic" class="tg-badge tg-badge-end" data-logic-type='${encodeData(
						endAttrs
					)}'>}</span>`
				);
			} else if (seg.type === "loop") {
				const collLabel = getLabel(seg.iterable);
				const startAttrs = {
					type: "loop",
					isStart: true,
					iterator: seg.iterator,
					iterable: seg.iterable,
					label: collLabel,
					_key: seg._key,
				};
				htmlParts.push(
					`<span data-type="logic" class="tg-badge tg-badge-loop" data-logic-type='${encodeData(
						startAttrs
					)}'></span>`
				);

				process(seg.segments || []);

				const endAttrs = { type: "loop", isEnd: true };
				htmlParts.push(
					`<span data-type="logic" class="tg-badge tg-badge-end" data-logic-type='${encodeData(
						endAttrs
					)}'>}</span>`
				);
			}
		});
	}

	process(segments);
	let result = htmlParts.join("");
	if (!result.startsWith("<p>")) result = `<p>${result}</p>`;
	return result;
}

export function serializeCondition(cond) {
	if (!cond) return "";
	if (cond.conditions && cond.conditions.length > 0) {
		const parts = cond.conditions.map((c) => serializeCondition(c)).filter(Boolean);
		if (parts.length === 0) return "";
		if (parts.length === 1) return parts[0];
		return `(${parts.join(` ${cond.op.toUpperCase()} `)})`;
	}
	if (cond.left) {
		const left =
			cond.left.ref ||
			(typeof cond.left.value === "string" ? `'${cond.left.value}'` : cond.left.value) ||
			"";
		let right = cond.right?.ref || cond.right?.value || "";

		// Handle array values for 'in' operator
		if (Array.isArray(right)) {
			// Frappe Autocomplete often returns ["Item", ["val1", "val2"]]
			const values = Array.isArray(right[1]) ? right[1] : right;
			right =
				"[" + values.map((v) => (typeof v === "string" ? `'${v}'` : v)).join(", ") + "]";
		} else if (typeof right === "string" && !cond.right?.ref) {
			right = `'${right}'`;
		}

		const op =
			cond.op === "is_set" ? "is not none" : cond.op === "is_not_set" ? "is none" : cond.op;
		if (op === "is not none" || op === "is none") return `${left} ${op}`;

		return `${left} ${op} ${right}`;
	}
	if (cond.field) {
		const val = typeof cond.value === "string" ? `'${cond.value}'` : cond.value;
		return `${cond.field} ${cond.operator} ${val}`;
	}
	return "";
}

// ─── Private Helpers ───

function _genKey() {
	return Math.random().toString(36).slice(2, 9);
}

function _tokenize(str) {
	const tokens = [];
	let pos = 0;
	const regex = /(\{\{.*?\}\}|\{\%.*?\%\}|\{#.*?\#\})/g;
	let match;

	while ((match = regex.exec(str)) !== null) {
		if (match.index > pos) {
			tokens.push({ type: "text", content: str.slice(pos, match.index) });
		}
		const raw = match[0];
		if (raw.startsWith("{{")) {
			tokens.push({ type: "variable", content: raw.slice(2, -2).trim() });
		} else if (raw.startsWith("{%")) {
			const inner = raw.slice(2, -2).trim();
			const parts = inner.split(/\s+/);
			tokens.push({ type: "tag", tag: parts[0], content: inner });
		}
		pos = regex.lastIndex;
	}
	if (pos < str.length) {
		tokens.push({ type: "text", content: str.slice(pos) });
	}
	return tokens;
}

function _parseLevel(tokens, index, breakTags = []) {
	const segments = [];
	let i = index;

	while (i < tokens.length) {
		const t = tokens[i];
		if (t.type === "text") {
			segments.push({ type: "text", content: t.content, _key: _genKey() });
		} else if (t.type === "variable") {
			const trimmed = t.content.trim();
			if (trimmed.startsWith('_("') && trimmed.endsWith('")')) {
				const inner = trimmed.slice(3, -2);
				segments.push({ type: "translation", content: inner, _key: _genKey() });
			} else if (trimmed.startsWith("_('") && trimmed.endsWith("')")) {
				const inner = trimmed.slice(3, -2);
				segments.push({ type: "translation", content: inner, _key: _genKey() });
			} else {
				segments.push({ type: "variable", path: t.content, _key: _genKey() });
			}
		} else if (t.type === "tag") {
			if (breakTags.includes(t.tag)) {
				return { segments, nextIndex: i };
			}

			if (t.tag === "if") {
				const condStr = t.content.slice(2).trim();
				const node = {
					type: "conditional",
					condition: _parseCond(condStr),
					_key: _genKey(),
				};
				const thenResult = _parseLevel(tokens, i + 1, ["elif", "else", "endif"]);
				node.then_segments = thenResult.segments;
				i = thenResult.nextIndex;

				node.elif_branches = [];
				while (i < tokens.length && tokens[i].tag === "elif") {
					const elifCond = tokens[i].content.slice(4).trim();
					const branchResult = _parseLevel(tokens, i + 1, ["elif", "else", "endif"]);
					node.elif_branches.push({
						condition: _parseCond(elifCond),
						segments: branchResult.segments,
					});
					i = branchResult.nextIndex;
				}

				if (i < tokens.length && tokens[i].tag === "else") {
					const elseResult = _parseLevel(tokens, i + 1, ["endif"]);
					node.else_segments = elseResult.segments;
					i = elseResult.nextIndex;
				}
				segments.push(node);
			} else if (t.tag === "for") {
				const match = t.content.match(/for\s+(.+)\s+in\s+(.+)/);
				const node = {
					type: "loop",
					iterator: match?.[1]?.trim() || "item",
					iterable: match?.[2]?.trim() || "",
					_key: _genKey(),
				};
				const res = _parseLevel(tokens, i + 1, ["endfor"]);
				node.segments = res.segments;
				i = res.nextIndex;
				segments.push(node);
			}
		}
		i++;
	}
	return { segments, nextIndex: i };
}

function _parseCond(str) {
	const trimmed = str.trim();
	if (!trimmed) return { op: "and", conditions: [] };

	// Remove outer parentheses if they exist
	let clean = trimmed;
	if (clean.startsWith("(") && clean.endsWith(")")) {
		clean = clean.slice(1, -1).trim();
	}

	// Handle multiple conditions split by AND/OR
	const op = clean.includes(" OR ") ? "or" : "and";
	const parts = clean.split(new RegExp(` ${op.toUpperCase()} `, "i"));

	const conditions = parts.map((part) => {
		part = part.trim();

		// Handle 'is not none' and 'is none'
		if (part.includes(" is not none")) {
			return { left: { ref: part.replace(" is not none", "").trim() }, op: "is_set" };
		}
		if (part.includes(" is none")) {
			return { left: { ref: part.replace(" is none", "").trim() }, op: "is_not_set" };
		}

		// Handle binary operators: ==, !=, >, <, >=, <=, in
		const ops = ["==", "!=", ">=", "<=", ">", "<", " in "];
		for (const operator of ops) {
			if (part.includes(operator)) {
				const [leftSide, ...rightRest] = part.split(operator);
				const rightSide = rightRest.join(operator).trim();

				const left = { ref: leftSide.trim().replace(/^['"]|['"]$/g, "") };
				let right = { value: rightSide };

				// Parse right side value
				if (rightSide.startsWith("[") && rightSide.endsWith("]")) {
					// Parse list: ['a', 'b']
					try {
						const listStr = rightSide.replace(/'/g, '"');
						right.value = JSON.parse(listStr);
					} catch (e) {
						right.value = rightSide
							.slice(1, -1)
							.split(",")
							.map((v) => v.trim().replace(/^['"]|['"]$/g, ""));
					}
				} else if (rightSide.startsWith("'") || rightSide.startsWith('"')) {
					right.value = rightSide.slice(1, -1);
				} else if (!isNaN(rightSide) && rightSide !== "") {
					right.value = Number(rightSide);
				}

				return { left, op: operator.trim(), right };
			}
		}

		// Fallback for single references (e.g. 'doc.is_pos')
		return { left: { ref: part }, op: "==", right: { value: true } };
	});

	return { op, conditions };
}
