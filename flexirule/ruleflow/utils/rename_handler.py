# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Schema-aware JSON reference updater for Frappe document renames."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import frappe


def _update_flex_value(
	val: Any, target_type: str, old_name: str, new_name: str, target_doctype: str | None = None
) -> tuple[Any, bool]:
	"""Transform a FlexValue object if it contains a target reference."""
	if not isinstance(val, Mapping):
		return val, False

	mode = val.get("mode")
	changed = False
	new_val = dict(val)

	if mode == "static":
		value_type = val.get("value_type")
		current_value = val.get("value")
		if value_type == "string" and current_value == old_name:
			if target_type == "doctype":
				new_val["value"] = new_name
				changed = True
			elif target_type == "docname":
				new_val["value"] = new_name
				changed = True
		elif value_type == "list" and isinstance(current_value, list):
			new_list = []
			list_changed = False
			for item in current_value:
				if isinstance(item, str) and item == old_name:
					new_list.append(new_name)
					list_changed = True
				else:
					new_list.append(item)
			if list_changed:
				new_val["value"] = new_list
				changed = True

	elif mode == "resolver":
		config = val.get("config")
		if isinstance(config, dict):
			updated_config, cfg_changed = update_action_config(
				config, target_type, old_name, new_name, target_doctype
			)
			if cfg_changed:
				new_val["config"] = updated_config
				changed = True

	elif mode == "template":
		pass

	return new_val, changed


def update_condition_node(
	node: Any, target_type: str, old_name: str, new_name: str, target_doctype: str | None = None
) -> tuple[Any, bool]:
	"""Recursively update canonical condition JSON tree."""
	if not isinstance(node, Mapping):
		return node, False

	node_type = node.get("type")
	changed = False
	new_node = dict(node)

	if node_type == "group":
		children = node.get("children")
		if isinstance(children, list):
			new_children = []
			for child in children:
				updated_child, child_changed = update_condition_node(
					child, target_type, old_name, new_name, target_doctype
				)
				new_children.append(updated_child)
				if child_changed:
					changed = True
			if changed:
				new_node["children"] = new_children

	elif node_type == "comparison":
		operator = node.get("operator")
		left = node.get("left")
		right = node.get("right")

		if target_type == "doctype" and operator in ("is_submittable", "has_field"):
			if isinstance(left, Mapping) and left.get("mode") == "static":
				if left.get("value") == old_name:
					updated_left, l_changed = _update_flex_value(
						left, target_type, old_name, new_name, target_doctype
					)
					if l_changed:
						new_node["left"] = updated_left
						changed = True

		if left is not None:
			updated_left, l_changed = _update_flex_value(
				left, target_type, old_name, new_name, target_doctype
			)
			if l_changed:
				new_node["left"] = updated_left
				changed = True

		if right is not None:
			updated_right, r_changed = _update_flex_value(
				right, target_type, old_name, new_name, target_doctype
			)
			if r_changed:
				new_node["right"] = updated_right
				changed = True

	elif node_type == "collection_predicate":
		where_clause = node.get("where")
		if where_clause is not None:
			updated_where, w_changed = update_condition_node(
				where_clause, target_type, old_name, new_name, target_doctype
			)
			if w_changed:
				new_node["where"] = updated_where
				changed = True

	return new_node, changed


def update_action_config(
	config: Any, target_type: str, old_name: str, new_name: str, target_doctype: str | None = None
) -> tuple[Any, bool]:
	"""Transform action configuration dict/JSON."""
	if not isinstance(config, dict):
		return config, False

	changed = False
	new_config = dict(config)

	if target_type == "doctype":
		doctype_keys = (
			"reference_doctype",
			"target_doctype",
			"document_type",
			"doctype",
			"for_doctype",
		)
		for key in doctype_keys:
			if key in new_config and new_config[key] == old_name:
				new_config[key] = new_name
				changed = True

	elif target_type == "docname":
		docname_keys = ("reference_docname", "target_docname", "docname", "document_name")
		cfg_dt = new_config.get("reference_doctype") or new_config.get("target_doctype")
		if target_doctype is None or cfg_dt is None or cfg_dt == target_doctype:
			for key in docname_keys:
				if key in new_config and new_config[key] == old_name:
					new_config[key] = new_name
					changed = True

	if "filters" in new_config:
		filters = new_config["filters"]
		if isinstance(filters, dict) and "type" in filters:
			updated_filters, f_changed = update_condition_node(
				filters, target_type, old_name, new_name, target_doctype
			)
			if f_changed:
				new_config["filters"] = updated_filters
				changed = True
		elif isinstance(filters, dict):
			new_filters_dict = dict(filters)
			f_changed = False
			for fk, fv in new_filters_dict.items():
				if target_type == "docname" and fv == old_name:
					new_filters_dict[fk] = new_name
					f_changed = True
				elif target_type == "doctype" and fv == old_name:
					new_filters_dict[fk] = new_name
					f_changed = True
			if f_changed:
				new_config["filters"] = new_filters_dict
				changed = True
		elif isinstance(filters, list):
			new_filters_list = []
			f_changed = False
			for fitem in filters:
				if isinstance(fitem, list) and len(fitem) >= 4:
					f_copy = list(fitem)
					if target_type == "doctype" and f_copy[0] == old_name:
						f_copy[0] = new_name
						f_changed = True
					if f_copy[3] == old_name:
						if target_type == "docname" or (target_type == "doctype" and f_copy[1] == "doctype"):
							f_copy[3] = new_name
							f_changed = True
					new_filters_list.append(f_copy)
				else:
					new_filters_list.append(fitem)
			if f_changed:
				new_config["filters"] = new_filters_list
				changed = True

	if "condition" in new_config and isinstance(new_config["condition"], dict):
		updated_cond, c_changed = update_condition_node(
			new_config["condition"], target_type, old_name, new_name, target_doctype
		)
		if c_changed:
			new_config["condition"] = updated_cond
			changed = True

	return new_config, changed


def update_visual_data(
	visual_data: Any, target_type: str, old_name: str, new_name: str, target_doctype: str | None = None
) -> tuple[Any, bool]:
	"""Transform visual builder layout JSON."""
	if not isinstance(visual_data, dict):
		return visual_data, False

	changed = False
	new_visual = dict(visual_data)

	nodes = new_visual.get("nodes")
	if isinstance(nodes, list):
		new_nodes = []
		for node in nodes:
			if isinstance(node, dict):
				new_node = dict(node)
				node_changed = False

				for prop_key in ("data", "properties", "config"):
					if prop_key in new_node and isinstance(new_node[prop_key], dict):
						updated_prop, prop_changed = update_action_config(
							new_node[prop_key], target_type, old_name, new_name, target_doctype
						)
						if prop_changed:
							new_node[prop_key] = updated_prop
							node_changed = True

				if node_changed:
					changed = True
				new_nodes.append(new_node)
			else:
				new_nodes.append(node)
		if changed:
			new_visual["nodes"] = new_nodes

	return new_visual, changed


def update_schema_json(schema_data: Any, target_type: str, old_name: str, new_name: str) -> tuple[Any, bool]:
	"""Transform schema JSON array / object."""
	if not isinstance(schema_data, list):
		return schema_data, False

	if target_type != "doctype":
		return schema_data, False

	changed = False
	new_schema = []
	for item in schema_data:
		if isinstance(item, dict):
			new_item = dict(item)
			item_changed = False
			fieldtype = new_item.get("fieldtype")
			if fieldtype in ("Link", "Table", "Dynamic Link") and new_item.get("options") == old_name:
				new_item["options"] = new_name
				item_changed = True

			source = new_item.get("source")
			if isinstance(source, dict) and source.get("doctype") == old_name:
				new_source = dict(source)
				new_source["doctype"] = new_name
				new_item["source"] = new_source
				item_changed = True

			if item_changed:
				changed = True
			new_schema.append(new_item)
		else:
			new_schema.append(item)

	return new_schema, changed


def update_rule_json_references(
	rule_doc, target_type: str, old_name: str, new_name: str, target_doctype: str | None = None
) -> bool:
	"""Scan and update embedded JSON fields in a Rule document instance."""
	rule_changed = False

	# 1. Rule.trigger_condition
	if rule_doc.trigger_condition:
		try:
			cond_json = json.loads(rule_doc.trigger_condition)
			updated_cond, c_changed = update_condition_node(
				cond_json, target_type, old_name, new_name, target_doctype
			)
			if c_changed:
				rule_doc.trigger_condition = json.dumps(
					updated_cond, ensure_ascii=False, separators=(",", ":")
				)
				rule_changed = True
		except (TypeError, ValueError, json.JSONDecodeError):
			pass

	# 2. Rule.visual_data
	if rule_doc.visual_data:
		try:
			vis_json = json.loads(rule_doc.visual_data)
			updated_vis, v_changed = update_visual_data(
				vis_json, target_type, old_name, new_name, target_doctype
			)
			if v_changed:
				rule_doc.visual_data = json.dumps(updated_vis, ensure_ascii=False, separators=(",", ":"))
				rule_changed = True
		except (TypeError, ValueError, json.JSONDecodeError):
			pass

	# 3. Rule.input_schema & Rule.output_schema
	for schema_field in ("input_schema", "output_schema"):
		val = getattr(rule_doc, schema_field, None)
		if val:
			try:
				s_json = json.loads(val)
				updated_s, s_changed = update_schema_json(s_json, target_type, old_name, new_name)
				if s_changed:
					setattr(
						rule_doc,
						schema_field,
						json.dumps(updated_s, ensure_ascii=False, separators=(",", ":")),
					)
					rule_changed = True
			except (TypeError, ValueError, json.JSONDecodeError):
				pass

	# 4. Rule Action child table
	for action in rule_doc.get("actions") or []:
		action_changed = False
		# Action.config
		if action.config:
			try:
				cfg_json = json.loads(action.config)
				updated_cfg, cfg_changed = update_action_config(
					cfg_json, target_type, old_name, new_name, target_doctype
				)
				if cfg_changed:
					action.config = json.dumps(updated_cfg, ensure_ascii=False, separators=(",", ":"))
					action_changed = True
			except (TypeError, ValueError, json.JSONDecodeError):
				pass

		# Action.resolved_output_schema
		if action.resolved_output_schema:
			try:
				ros_json = json.loads(action.resolved_output_schema)
				updated_ros, ros_changed = update_schema_json(ros_json, target_type, old_name, new_name)
				if ros_changed:
					action.resolved_output_schema = json.dumps(
						updated_ros, ensure_ascii=False, separators=(",", ":")
					)
					action_changed = True
			except (TypeError, ValueError, json.JSONDecodeError):
				pass

		if action_changed:
			rule_changed = True

	return rule_changed


def update_process_json_references(
	process_doc, target_type: str, old_name: str, new_name: str, target_doctype: str | None = None
) -> bool:
	"""Scan and update embedded JSON fields in a Process document instance."""
	process_changed = False

	if target_type == "doctype":
		for op in process_doc.get("operations") or []:
			op_changed = False
			if op.doctype_filters:
				try:
					f_json = json.loads(op.doctype_filters)
					if isinstance(f_json, list):
						new_filters = []
						f_changed = False
						for item in f_json:
							if isinstance(item, list) and len(item) >= 4 and item[0] == old_name:
								item_copy = list(item)
								item_copy[0] = new_name
								new_filters.append(item_copy)
								f_changed = True
							else:
								new_filters.append(item)
						if f_changed:
							op.doctype_filters = json.dumps(new_filters)
							op_changed = True
				except (TypeError, ValueError, json.JSONDecodeError):
					pass

			if op_changed:
				process_changed = True

	return process_changed


def process_rename_references(renamed_doctype: str, old_name: str, new_name: str) -> list[str]:
	"""Main hook entry point called after a document or DocType is renamed.

	Returns list of updated Rule names.
	"""
	if not old_name or not new_name or old_name == new_name:
		return []

	target_type = "doctype" if renamed_doctype == "DocType" else "docname"
	target_doctype = None if renamed_doctype == "DocType" else renamed_doctype

	updated_rule_names = []

	frappe.db.savepoint("flexirule_after_rename")

	try:
		# 1. Fetch Rules
		rules = frappe.get_all("Rule", fields=["name"])
		for r_dict in rules:
			try:
				rule_doc = frappe.get_doc("Rule", r_dict["name"])
				was_active = bool(rule_doc.is_active)
				changed = update_rule_json_references(
					rule_doc, target_type, old_name, new_name, target_doctype
				)
				if changed:
					if was_active:
						rule_doc.is_active = 0
						rule_doc.status = "Draft"
					rule_doc.flags.ignore_permissions = True
					rule_doc.save()
					if was_active:
						rule_doc.is_active = 1
						rule_doc.status = "Active"
						rule_doc.save()
					updated_rule_names.append(rule_doc.name)
			except Exception as exc:
				frappe.log_error(
					title=f"FlexiRule JSON rename error for Rule {r_dict['name']}",
					message=str(exc),
				)

		# 2. Fetch Processes if target_type == "doctype"
		if target_type == "doctype":
			processes = frappe.get_all("Process", fields=["name"])
			for p_dict in processes:
				try:
					proc_doc = frappe.get_doc("Process", p_dict["name"])
					changed = update_process_json_references(
						proc_doc, target_type, old_name, new_name, target_doctype
					)
					if changed:
						proc_doc.flags.ignore_permissions = True
						proc_doc.save()
				except Exception as exc:
					frappe.log_error(
						title=f"FlexiRule JSON rename error for Process {p_dict['name']}",
						message=str(exc),
					)

		# 3. Invalidate caches for updated rules
		if updated_rule_names:
			from flexirule.ruleflow.hooks import clear_rule_cache

			for rname in updated_rule_names:
				rule_doc = frappe.get_doc("Rule", rname)
				clear_rule_cache(rule_doc)

	except Exception as err:
		frappe.db.rollback(to_savepoint="flexirule_after_rename")
		frappe.log_error(
			title="FlexiRule process_rename_references failed",
			message=f"Failed updating JSON references from {old_name} to {new_name}: {err}",
		)
		raise

	return updated_rule_names
