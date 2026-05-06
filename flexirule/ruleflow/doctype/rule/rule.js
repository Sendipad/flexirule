frappe.ui.form.on("Rule", {
	onload(frm) {
		frm._process_ops_cache = {};
		flexirule.contracts?.loadContractsFromBackend?.();
		apply_trigger_type_contract(frm);

		const actions_field = frm.get_field("actions");
		if (actions_field && actions_field.grid) {
			const grid = actions_field.grid;
			const op_field = grid.fields_dict["operation"];
			const rule_field = grid.fields_dict["rule"];

			if (rule_field) {
				rule_field.get_query = function () {
					const filters = [
						["Rule", "trigger_type", "=", "Callable Event"],
						["Rule", "exposed_as_subrule", "=", 1],
						["Rule", "is_active", "=", 1],
					];

					if (frm.doc.name) {
						filters.push(["Rule", "name", "!=", frm.doc.name]);
					}

					return { filters };
				};
			}

			if (op_field) {
				op_field.get_data = function () {
					const row = this.grid_row.doc;
					if (!row || !row.action_type) return [];

					const contractOptions =
						flexirule.contracts?.getOperationOptions?.(row.action_type, {
							processName: row.process_name,
						}) || [];
					if (contractOptions.length) {
						return contractOptions.map((op) => ({
							value: op.value || op.func_name,
							description: op.process_name || "",
						}));
					}

					if (!row.process_name || row.action_type !== "Process") return [];

					const cached = frm._process_ops_cache[row.process_name];
					if (cached) {
						return cached.map((op) => ({ value: op, description: "" }));
					}

					return frappe
						.call({
							method: "flexirule.ruleflow.api.get_process_operations",
							args: { process_name: row.process_name },
						})
						.then((r) => {
							const ops = r.message || [];
							frm._process_ops_cache[row.process_name] = ops;
							return ops.map((op) => ({ value: op, description: "" }));
						});
				};
			}
		}
	},

	is_active(frm) {
		if (frm.doc.is_active === 0 && frm._was_active) {
			frm.set_value("is_active", 1);
			show_deactivation_dialog(frm);
			return;
		}

		apply_active_lock(frm);
		frm.refresh_fields();
		frm._was_active = frm.doc.is_active;
	},

	refresh(frm) {
		if (frm.is_new()) return;

		frm._was_active = frm.doc.is_active;

		frm.page.clear_primary_action();
		frm.page.set_primary_action(__("Visual Builder"), () => {
			frappe.set_route("rule-builder", frm.doc.name);
		});

		frm.page.clear_custom_actions();
		frm.add_custom_button(__("Amend Rule"), () => amend_rule(frm), __("Actions"));
		frm.add_custom_button(__("Test Rule"), () => test_rule(frm), __("Actions"));
		frm.add_custom_button(__("Clear Cache"), () => clear_rule_cache(frm), __("Actions"));

		apply_trigger_type_contract(frm);
		apply_active_lock(frm);

		update_dashboard_indicators(frm);

		if (frm.doc.actions?.length) {
			frm.doc.actions.forEach((row) => {
				update_operation_options(frm, "Rule Action", row.name);
			});
		}
	},

	before_insert(frm) {
		if (
			frm.doc.document_type &&
			frm.doc.trigger_event &&
			(!frm.doc.actions || !frm.doc.actions.length)
		) {
			frm.add_child("actions", {
				action_id: "root",
				action_type: "Entry Action",
				is_enabled: 1,
			});
			frm.refresh_field("actions");
		}
	},

	trigger_type(frm) {
		apply_trigger_type_contract(frm, { clear_hidden_values: true });
	},
});

frappe.ui.form.on("Rule Action", {
	form_render(frm, cdt, cdn) {
		toggle_action_fields(frm, cdt, cdn);
		update_operation_options(frm, cdt, cdn);
	},

	refresh(frm, cdt, cdn) {
		toggle_action_fields(frm, cdt, cdn);
		update_operation_options(frm, cdt, cdn);
	},

	action_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.action_type !== "Process") {
			frappe.model.set_value(cdt, cdn, "process_name", null);
			frappe.model.set_value(cdt, cdn, "operation", null);
			frappe.model.set_value(cdt, cdn, "config", null);
		}

		toggle_action_fields(frm, cdt, cdn);
	},

	process_name(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "operation", null);
		frappe.model.set_value(cdt, cdn, "config", null);
		update_operation_options(frm, cdt, cdn);
	},

	configure_operation(frm, cdt, cdn) {
		configure_operation_from_form(frm, cdt, cdn);
	},
});

function apply_active_lock(frm) {
	const is_active = !!frm.doc.is_active;

	frm.fields.forEach((field) => {
		if (!field.df || field.df.fieldname === "is_active") return;
		frm.set_df_property(field.df.fieldname, "read_only", is_active ? 1 : 0);
	});

	frm.set_df_property("is_active", "read_only", 0);

	Object.values(frm.fields_dict).forEach((f) => {
		if (!f.grid) return;
		f.grid.cannot_add_rows = is_active;
		f.grid.cannot_delete_rows = is_active;
		f.grid.only_sortable = is_active;
		f.grid.wrapper.find(".grid-row, .grid-add-row").toggleClass("disabled", is_active);
	});

	frm.dashboard.clear_headline();
	if (is_active) {
		frm.dashboard.set_headline_alert(
			__("This rule is active and locked. Deactivate it to edit."),
			"orange"
		);
	}
}

function show_deactivation_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Deactivate Rule"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "info",
				options: `<p>${__("This rule is active. How would you like to proceed?")}</p>`,
			},
		],
		primary_action_label: __("Edit Current Rule"),
		primary_action() {
			d.hide();
			// Temporarily bypass the "was_active" check to prevent an infinite dialog loop
			frm._was_active = 0;

			// Explicitly set value and refresh to ensure UI state syncs
			frm.set_value("is_active", 0).then(() => {
				apply_active_lock(frm);
				frm.refresh_fields();
				frappe.show_alert({ message: __("Rule unlocked"), indicator: "blue" });
			});
		},
		secondary_action_label: __("Create Amendment & Edit"),
		secondary_action() {
			d.hide();
			create_amendment_and_edit(frm);
		},
	});

	d.show();
}

function create_amendment_and_edit(frm) {
	frappe.call({
		method: "flexirule.ruleflow.api.amend_rule",
		args: {
			rule_name: frm.doc.name,
		},
		freeze: true,
		callback(r) {
			if (r.message) {
				frappe.set_route("Form", "Rule", r.message);
			}
		},
	});
}

function apply_trigger_type_contract(frm, options = {}) {
	const contract = flexirule.contracts?.getTriggerTypeContract?.(frm.doc.trigger_type) || {
		required_fields: [],
		optional_fields: [],
		hidden_fields: [],
	};
	const managedFields = [
		"document_type",
		"trigger_event",
		"trigger_condition",
		"compiled_expression",
	];
	const visibleFields = new Set([
		...(contract.required_fields || []),
		...(contract.optional_fields || []),
	]);
	const clearHiddenValues = !!options.clear_hidden_values;

	managedFields.forEach((fieldname) => {
		if (!frm.fields_dict[fieldname]) return;

		const isVisible = visibleFields.has(fieldname);
		frm.toggle_display(fieldname, isVisible);
		frm.set_df_property(
			fieldname,
			"reqd",
			contract.required_fields?.includes(fieldname) ? 1 : 0
		);

		if (clearHiddenValues && !isVisible && frm.doc[fieldname]) {
			frm.set_value(fieldname, null);
		}
	});
}
function update_dashboard_indicators(frm) {
	if (!frm.dashboard) return;

	frm.dashboard.clear_headline();

	if (frm.dashboard.indicator_area) {
		frm.dashboard.indicator_area.empty();
	}

	if (!frm._dashboard_rendered) {
		frm._dashboard_rendered = {};
	}

	frappe.call({
		method: "flexirule.ruleflow.api.get_rule_stats",
		args: { rule_name: frm.doc.name },
		callback: (r) => {
			if (!r.message) return;
			const stats = r.message;
			const indicators = [];

			if (stats.execution_count > 0) {
				indicators.push({
					label: __("Executed {0} times", [stats.execution_count]),
					color: "blue",
					key: "execution_count",
				});
				if (stats.success_rate < 100) {
					indicators.push({
						label: __("{0}% Success Rate", [stats.success_rate.toFixed(1)]),
						color: stats.success_rate > 90 ? "orange" : "red",
						key: "success_rate",
					});
				}
			}

			if (frm.doc.last_error) {
				indicators.push({
					label: __("Has Errors"),
					color: "red",
					key: "last_error",
				});
			}

			indicators.forEach((ind) => {
				if (!frm._dashboard_rendered[ind.key]) {
					frm.dashboard.add_indicator(ind.label, ind.color);
					frm._dashboard_rendered[ind.key] = true;
				}
			});
		},
	});
}
function test_rule(frm) {
	let d = new frappe.ui.Dialog({
		title: __("Test Rule"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "doctype",
				label: __("Document Type"),
				options: "DocType",
				default: frm.doc.document_type,
				reqd: 1,
			},
			{
				fieldtype: "Dynamic Link",
				fieldname: "docname",
				label: __("Document"),
				options: "doctype",
				reqd: 1,
			},
			{
				fieldtype: "Check",
				fieldname: "save_log",
				label: __("Create Execution Log"),
				description: __("Persist a log record even for this test run"),
				default: 1,
			},
		],
		primary_action_label: __("Test"),
		primary_action: (values) => {
			frappe.call({
				method: "flexirule.ruleflow.api.test_rule",
				args: {
					rule_name: frm.doc.name,
					doctype: values.doctype,
					docname: values.docname,
					dry_run: !values.save_log,
					skip_log_enqueue: !values.save_log,
				},
				callback: (r) => {
					if (r.message?.success) {
						// Highlight path in builder

						frappe.msgprint({
							title: __("Success"),
							message: r.message?.message || __("Rule test completed successfully"),
							indicator: "green",
						});
					} else {
						frappe.msgprint({
							title: __("Error"),
							message: r.message?.error || __("Test failed"),
							indicator: "red",
						});
					}
					d.hide();
				},
			});
		},
	});
	d.show();
}
function toggle_action_fields(frm, cdt, cdn) {
	const row = locals?.[cdt]?.[cdn];
	if (!row) return;
	const grid_field = frm.get_field("actions");
	if (!grid_field || !grid_field.grid) return;
	const grid_row = grid_field.grid.get_row(cdn);
	if (!grid_row) return;

	// All configuration fields that might be toggled
	const all_config_fields = [
		"process_name",
		"operation",
		"config",
		"timeout",
		"retry_count",
		"is_async",
		"on_error",
		"compiled_expression",
		"condition_json",
		"next_step_if_false",
		"rule",
		"skip_conditions",
		"skip_permissions",
		"configure_operation",
		"target_field",
		"value_template",
		"reference_doctype",
		"reference_docname",
		"mutation_mode",
		"input_mapping",
		"output_mapping",
		"input_source",
		"return_type",
		"return_variable",
		"resolved_output_schema",
	];

	// Initial Hide
	all_config_fields.forEach((f) => grid_row.toggle_display(f, false));

	const type = row.action_type;
	if (!type) return;

	const contract = flexirule.contracts?.getContract?.(type);
	if (!contract) return;

	// 1. Show required fields from contract
	const fields_to_show = [...(contract.required_fields || [])];

	// 2. Additional logic for dynamic fields
	if (type === "Process") {
		fields_to_show.push(
			"config",
			"timeout",
			"is_async",
			"on_error",
			"configure_operation",
			"mutation_mode",
			"return_variable"
		);
	} else if (type === "Condition") {
		fields_to_show.push("compiled_expression", "next_step_if_false");
	} else if (type === "Sub-Rule") {
		fields_to_show.push("skip_conditions", "skip_permissions");
	} else if (["Query Records", "Document Action"].includes(type)) {
		fields_to_show.push("input_source", "mutation_mode", "return_type", "return_variable");
	}

	// Always show operation if it has options or is for specific types
	if (
		contract.operation_options ||
		["Process", "Query Records", "Document Action"].includes(type)
	) {
		fields_to_show.push("operation");
	}

	const policyContext = {
		operation: row.operation,
		processName: row.process_name,
	};
	const showReturnType =
		flexirule.contracts?.shouldShowReturnType?.(type, policyContext) ?? false;
	const requireReturnType =
		flexirule.contracts?.isReturnTypeMandatory?.(type, policyContext) ?? false;
	if (showReturnType) {
		fields_to_show.push("return_type");
	}
	if (["Process", "Query Records", "Document Action"].includes(type)) {
		fields_to_show.push("return_variable");
	}

	// Handle reference_docname visibility
	if (type === "Query Records" && ["Query Doc", "Query Report"].includes(row.operation)) {
		fields_to_show.push("reference_docname");
	} else if (type === "Document Action" && row.operation === "Update Existing") {
		fields_to_show.push("reference_docname");
	} else if (type === "Process" && row.operation?.includes("Doc")) {
		fields_to_show.push("reference_docname");
	}

	// Deduplicate and filter existing fields
	const unique_fields = [...new Set(fields_to_show)];
	unique_fields.forEach((f) => {
		if (grid_row.get_field(f)) {
			grid_row.toggle_display(f, true);
		}
	});

	const returnTypeField = grid_row.get_field("return_type");
	if (returnTypeField) {
		returnTypeField.df.reqd = requireReturnType ? 1 : 0;
		returnTypeField.refresh();
	}

	// Update Operation Label if contract provides it
	const op_field = grid_row.get_field("operation");
	if (op_field) {
		const dynamicOperationLabel = flexirule.contracts?.getFieldLabel?.(type, "operation", {
			operation: row.operation,
			processName: row.process_name,
		});
		if (dynamicOperationLabel || contract.operation_label) {
			op_field.df.label = dynamicOperationLabel || contract.operation_label;
			op_field.refresh();
		} else {
			op_field.df.label = __("Operation / Mode");
			op_field.refresh();
		}
	}
}

function update_operation_options(frm, cdt, cdn) {
	const row = locals?.[cdt]?.[cdn];
	if (!row || !row.action_type) return;

	const actions_field = frm.get_field("actions");
	if (!actions_field?.grid) return;
	const grid_row = actions_field.grid.get_row(row.name || cdn);
	if (!grid_row) return;

	const apply_ops = (ops) => {
		const field = grid_row.get_field("operation");
		if (!field) return;
		const normalized = (ops || []).map((op) => {
			if (typeof op === "string") return op;
			return op?.value || op?.func_name || op?.label;
		});
		const cleaned = normalized.filter(Boolean);
		field.df.options = cleaned.join("\n");
		field.set_data?.(cleaned);
		field.refresh();
	};

	const contractOptions =
		flexirule.contracts?.getOperationOptions?.(row.action_type, {
			processName: row.process_name,
		}) || [];
	if (contractOptions.length) {
		apply_ops(contractOptions);
		return;
	}

	if (row.action_type !== "Process" || !row.process_name) return;

	if (frm._process_ops_cache[row.process_name]) {
		apply_ops(frm._process_ops_cache[row.process_name]);
		return;
	}

	frappe
		.call({
			method: "flexirule.ruleflow.api.get_process_operations",
			args: { process_name: row.process_name },
		})
		.then((r) => {
			const ops = r.message || [];
			frm._process_ops_cache[row.process_name] = ops;
			apply_ops(ops);
		});
}

function amend_rule(frm) {
	frappe.call({
		method: "flexirule.ruleflow.api.amend_rule",
		args: {
			rule_name: frm.doc.name,
		},
		freeze: true,
		callback: (r) => {
			if (r.message) {
				frappe.set_route("Form", "Rule", r.message);
			}
		},
	});
}

function clear_rule_cache(frm) {
	frappe.call({
		method: "flexirule.ruleflow.api.clear_cache",
		args: { doctype: frm.doc.document_type },
		callback: () => {
			frappe.show_alert({ message: __("Rule cache cleared"), indicator: "green" });
		},
	});
}

function configure_operation_from_form(frm, cdt, cdn) {
	if (frm._config_dialog_active) return;

	const row = locals[cdt][cdn];
	if (!row.process_name || !row.operation) {
		frappe.msgprint(__("Please select a Process and Operation first"));
		return;
	}

	// Ensure config is parsed if it's a string
	let config = row.config;
	if (typeof config === "string" && config.trim()) {
		try {
			config = JSON.parse(config);
		} catch (e) {
			config = {};
		}
	}

	frm._config_dialog_active = true;

	const action = flexirule.integration.create_configurable_action({
		process_name: row.process_name,
		operation_name: row.operation,
		node_data: row,
		document_type: frm.doc.document_type,
	});

	const dialog = action.show_dialog({
		on_save: () => {
			frm.dirty();
			frm.refresh_field("actions");
			frappe.show_alert({ message: __("Configuration saved"), indicator: "green" });
		},
	});

	if (dialog) {
		const original_on_hide = dialog.on_hide;
		dialog.on_hide = () => {
			frm._config_dialog_active = false;
			if (typeof original_on_hide === "function") {
				original_on_hide.call(dialog);
			}
		};
	} else {
		frm._config_dialog_active = false;
	}
}
