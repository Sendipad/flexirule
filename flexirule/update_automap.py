import os
import re

# Hardcoded path for maintenance script - validate it's within project
file_path = "/home/erpnext/frappe-bench/apps/flexirule/flexirule/public/js/flexirule/rule_builder/controls/ResourceMapperControl.vue"

# Security: Validate file path is within expected directory structure
expected_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
resolved_path = os.path.abspath(file_path)

# Ensure the resolved path is within the flexirule app directory
if not resolved_path.startswith(expected_base) or not resolved_path.endswith("ResourceMapperControl.vue"):
	raise ValueError("Invalid file path: file must be within flexirule directory")

with open(file_path) as f:
	content = f.read()

# 1. Update scalarAutoMapPreview block
scalar_preview_old = """		<div v-if="scalarAutoMapPreview.length" class="rm-preview-box">
			<div class="rm-preview-title">
				{{ __("Auto-map Preview") }}
				<span class="rm-badge">{{ scalarAutoMapPreview.length }}</span>
			</div>
			<div class="rm-preview-list">
				<div
					v-for="(row, idx) in scalarAutoMapPreview"
					:key="`preview-${idx}`"
					class="rm-preview-row"
				>
					<code class="rm-target">{{ row.target }}</code>
					<i class="fa fa-long-arrow-left rm-arrow"></i>
					<code class="rm-source">{{ row.path }}</code>
				</div>
			</div>
			<div class="rm-preview-actions">
				<button class="rm-btn rm-btn-primary" @click="applyScalarAutoMap">
					{{ __("Apply") }}
				</button>
				<button class="rm-btn rm-btn-default" @click="cancelScalarAutoMap">
					{{ __("Cancel") }}
				</button>
			</div>
		</div>"""

scalar_preview_new = """		<div v-if="scalarAutoMapPreview.length" class="rm-preview-box">
			<div class="rm-preview-title">
				{{ __("Auto-map Preview") }}
				<span class="rm-badge">{{ scalarAutoMapPreview.length }}</span>
			</div>
			<div class="rm-preview-list">
				<div
					v-for="(row, idx) in scalarAutoMapPreview"
					:key="`preview-${idx}`"
					class="rm-preview-row rm-mapping-row"
					style="grid-template-columns: 1fr auto 1.6fr auto; padding: 4px 0;"
				>
					<div class="rm-cell rm-cell-target">
						<code class="rm-target">{{ row.target }}</code>
					</div>
					<div class="rm-cell rm-cell-arrow">
						<i class="fa fa-long-arrow-left rm-arrow"></i>
					</div>
					<div class="rm-cell rm-cell-source">
						<input type="text" class="form-control input-xs" v-model="row.path" />
					</div>
					<div class="rm-cell">
						<button class="rm-btn rm-btn-danger" @click="scalarAutoMapPreview.splice(idx, 1)">
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>
			<div class="rm-preview-actions mt-2">
				<button class="rm-btn rm-btn-primary" @click="applyScalarAutoMap">
					{{ __("Apply Mappings") }}
				</button>
				<button class="rm-btn rm-btn-default" @click="cancelScalarAutoMap">
					{{ __("Cancel") }}
				</button>
			</div>
		</div>"""

content = content.replace(scalar_preview_old, scalar_preview_new)

# 2. Update tableAutoMapPreview block
table_preview_old = """				<div v-if="tableAutoMapPreview[tIdx]?.length" class="rm-preview-box">
					<div class="rm-preview-title">
						{{ __("Table Auto-map Preview") }}
						<span class="rm-badge">{{ tableAutoMapPreview[tIdx].length }}</span>
					</div>
					<div class="rm-preview-list">
						<div
							v-for="(row, pIdx) in tableAutoMapPreview[tIdx]"
							:key="`table-preview-${tIdx}-${pIdx}`"
							class="rm-preview-row"
						>
							<code class="rm-target">{{ row.target }}</code>
							<i class="fa fa-long-arrow-left rm-arrow"></i>
							<code class="rm-source">{{ row.path }}</code>
						</div>
					</div>
					<div class="rm-preview-actions">
						<button
							class="rm-btn rm-btn-primary"
							@click="applyTableAutoMap(table, tIdx)"
						>
							{{ __("Apply") }}
						</button>
						<button class="rm-btn rm-btn-default" @click="cancelTableAutoMap(tIdx)">
							{{ __("Cancel") }}
						</button>
					</div>
				</div>"""

table_preview_new = """				<div v-if="tableAutoMapPreview[tIdx]?.length" class="rm-preview-box">
					<div class="rm-preview-title">
						{{ __("Table Auto-map Preview") }}
						<span class="rm-badge">{{ tableAutoMapPreview[tIdx].length }}</span>
					</div>
					<div class="rm-preview-list">
						<div
							v-for="(row, pIdx) in tableAutoMapPreview[tIdx]"
							:key="`table-preview-${tIdx}-${pIdx}`"
							class="rm-preview-row rm-mapping-row"
							style="grid-template-columns: 1fr auto 1.6fr auto; padding: 4px 0;"
						>
							<div class="rm-cell rm-cell-target">
								<code class="rm-target">{{ row.target }}</code>
							</div>
							<div class="rm-cell rm-cell-arrow">
								<i class="fa fa-long-arrow-left rm-arrow"></i>
							</div>
							<div class="rm-cell rm-cell-source">
								<input type="text" class="form-control input-xs" v-model="row.path" />
							</div>
							<div class="rm-cell">
								<button class="rm-btn rm-btn-danger" @click="tableAutoMapPreview[tIdx].splice(pIdx, 1)">
									<i class="fa fa-trash"></i>
								</button>
							</div>
						</div>
					</div>
					<div class="rm-preview-actions mt-2">
						<button
							class="rm-btn rm-btn-primary"
							@click="applyTableAutoMap(table, tIdx)"
						>
							{{ __("Apply Mappings") }}
						</button>
						<button class="rm-btn rm-btn-default" @click="cancelTableAutoMap(tIdx)">
							{{ __("Cancel") }}
						</button>
					</div>
				</div>"""

content = content.replace(table_preview_old, table_preview_new)

# 3. Update collectTableAutoMapRows
collect_table_old = """	childFields.forEach((cf) => {
		const target = cf.value;
		if (!target || existing.has(target)) return;
		// Skip system / internal fields
		if (AUTOMAP_EXCLUDE_FIELDS.has(target)) return;
		// Try to find a match in context variables, fallback to speculative mapping based on rowAlias
		const source = preferredSource(target, rowSourceOptions, `${rowAlias}.`);
		const sourcePath = source ? source.value : `${rowAlias}.${target}`;

		suggestions.push({
			target,
			source_type: "path",
			path: sourcePath,
			expr: "",
			literal: "",
		});
		existing.add(target);
	});"""

collect_table_new = """	childFields.forEach((cf) => {
		const target = cf.value;
		if (!target || existing.has(target)) return;
		// Skip system / internal fields
		if (AUTOMAP_EXCLUDE_FIELDS.has(target)) return;
		// Find a valid match in source schema
		const source = preferredSource(target, rowSourceOptions);
		if (!source) return; // Do not map if source field does not exist

		let sourcePath = source.value;
		// If the source comes from a child table (e.g. items.item_code), use rowAlias
		if (source.value.includes(".") && !source.value.startsWith("doc.") && !source.value.startsWith("vars.")) {
			sourcePath = `${rowAlias}.${target}`;
		} else if (source.value.startsWith("doc.") || source.value.startsWith("vars.")) {
			sourcePath = source.value;
		} else {
			sourcePath = `${rowAlias}.${target}`;
		}

		suggestions.push({
			target,
			source_type: "path",
			path: sourcePath,
			expr: "",
			literal: "",
		});
		existing.add(target);
	});"""

content = content.replace(collect_table_old, collect_table_new)

# Security: Re-validate before writing (path traversal protection)
resolved_path = os.path.abspath(file_path)
if not resolved_path.startswith(expected_base) or not resolved_path.endswith("ResourceMapperControl.vue"):
	raise ValueError("Invalid file path: file must be within flexirule directory")

with open(file_path, "w") as f:
	f.write(content)
