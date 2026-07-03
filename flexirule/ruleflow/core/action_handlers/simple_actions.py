# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Simple Action Handlers.

Contains handlers for simpler action types that don't require
complex logic: Stop, Wait, Set Value, Raise Error, Notify.
"""

import time

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import (
	ActionContract,
	OperationContract,
)
from flexirule.ruleflow.core.action_plan_cache import get_action_plan
from flexirule.ruleflow.core.engine import SafeFrappeAPI
from flexirule.ruleflow.utils.field_resolver import parse_field_list


class StopHandler(ActionHandler):
	"""Handler for Stop action type - terminates rule execution."""

	action_type = "Stop"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Stop",
			required_fields=["operation"],
			has_next_true=False,
			has_next_false=False,
			terminal=True,
			css={"icon": "fa fa-stop", "color": "#ef4444"},
			operation_label="Terminal Mode",
			operation_options=["Success", "Error"],
			mandatory_fields={
				"Error": ["value_template"],
			},
			field_labels={"operation": "Terminal Mode"},
			node_type="stop",
			category="Control Flow",
			configurable=False,
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Success": OperationContract(
				operation="Success",
				action_overrides=[
					{"fieldname": "action_type", "default": "Stop"},
					{"fieldname": "operation", "default": "Success"},
					{"fieldname": "description", "description": "Terminates rule execution successfully"},
				],
			),
			"Error": OperationContract(
				operation="Error",
				action_overrides=[
					{"fieldname": "action_type", "default": "Stop"},
					{"fieldname": "operation", "default": "Error"},
					{
						"fieldname": "value_template",
						"reqd": 1,
						"description": "⚠️ Error message that will be raised",
					},
					{"fieldname": "description", "description": "Terminates rule execution with an error"},
				],
				validation={"backend": "validate_stop_error"},
			),
		}

	def execute(self, action, context, engine):
		"""
		Stop action terminal behavior.

		- Success: terminate flow silently.
		- Error: raise ValidationError using value_template.
		"""
		mode = (getattr(action, "operation", None) or "Success").strip()

		if mode == "Error":
			value_template = getattr(action, "value_template", "") or _(
				"Rule execution stopped by terminal error"
			)
			template_context = self._build_template_context(context, engine)
			# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
			message = frappe.render_template(value_template, template_context)  # nosemgrep: frappe-ssti

			# Append source link for traceability
			source_link = f'<div style="margin-top: 12px; font-size: 0.85em; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 8px;">{_("Source Rule")}: <a href="/app/rule/{engine.rule.name}" style="font-weight: bold;">{engine.rule.name}</a></div>'
			message += source_link

			engine._log("ERROR", _("Stop action raised error: {0}").format(message))
			frappe.throw(message)

		engine._log("INFO", _("Stop action encountered"))
		return None, None


class WaitHandler(ActionHandler):
	"""Handler for Wait action type - pauses execution."""

	action_type = "Wait"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Wait",
			required_fields=[],  # config.duration optional
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-clock-o", "color": "#64748b"},
			field_labels={"operation": "Wait Mode"},
			node_type="wait",
			category="Control Flow",
			configurable=True,
			config_component="WaitConfig",
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Wait": OperationContract(
				operation="Wait",
				action_overrides=[
					{"fieldname": "action_type", "default": "Wait"},
					{"fieldname": "description", "description": "Pauses execution for a specified duration"},
				],
			)
		}

	def execute(self, action, context, engine):
		"""
		Wait action - pauses execution for specified duration.

		Config options:
		- duration: Seconds to wait

		Falls back to action.timeout if duration not in config.
		"""
		config = engine._get_action_config(action)

		duration = config.get("duration", 0)
		if not duration and action.timeout:
			duration = action.timeout

		if duration > 0:
			engine._log("INFO", _("Waiting for {0} seconds...").format(duration))
			time.sleep(duration)

		return None, action.next_step_if_true


class RaiseErrorHandler(ActionHandler):
	"""Handler for Raise Error action type - throws ValidationError."""

	action_type = "Raise Error"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Raise Error",
			required_fields=["value_template"],
			has_next_true=False,
			has_next_false=False,
			terminal=True,
			css={"icon": "fa fa-exclamation-triangle", "color": "#dc2626"},
			field_labels={
				"config": "Error Details (JSON)",
			},
			node_type="raise-error",
			category="Control Flow",
			configurable=True,
			config_component="RaiseErrorConfig",
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Raise Error": OperationContract(
				operation="Raise Error",
				action_overrides=[
					{"fieldname": "action_type", "default": "Raise Error"},
					{
						"fieldname": "value_template",
						"reqd": 1,
						"description": "⚠️ Error message that will be raised",
					},
					{
						"fieldname": "description",
						"description": "Raises an exception to abort current operation",
					},
				],
				validation={"backend": "validate_raise_error"},
			)
		}

	def execute(self, action, context, engine):
		"""
		Raise Error action - throws ValidationError with Jinja message.

		Uses action.value_template for the error message.
		"""
		value_template = getattr(action, "value_template", "") or "Validation Error"
		config = self._parse_config(getattr(action, "config", None))
		error_type = (
			config.get("error_type") or getattr(action, "operation", None) or "Validation Error"
		).strip()
		error_title = (config.get("error_title") or "").strip() or None
		error_code = (config.get("error_code") or "").strip()

		# Render Jinja template with SafeFrappeAPI to prevent write operations
		template_context = self._build_template_context(context, engine)
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		message = frappe.render_template(value_template, template_context)  # nosemgrep: frappe-ssti

		# Append source link for traceability
		source_link = f'<div style="margin-top: 12px; font-size: 0.85em; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 8px;">{_("Source Rule")}: <a href="/app/rule/{engine.rule.name}" style="font-weight: bold;">{engine.rule.name}</a></div>'
		message += source_link

		if error_code:
			message = f"[{error_code}] {message}"

		engine._log("INFO", _("Raising {0}: {1}").format(error_type, message))

		if error_type == "Permission Error":
			frappe.throw(message, frappe.PermissionError)
		else:
			frappe.throw(message, title=error_title)


class NotifyHandler(ActionHandler):
	"""Handler for Notify action type - sends notifications."""

	action_type = "Notify"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Notify",
			required_fields=["value_template", "operation"],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-bell", "color": "#0ea5e9"},
			operation_label="Notification Type",
			operation_options=["Toast", "System", "Email", "System Notification", "Provider"],
			operation_policies={
				"Email": {
					"required_config_keys": ["subject", "recipients"],
				},
				"System Notification": {
					"required_config_keys": ["subject"],
				},
				"Provider": {
					"required_config_keys": ["provider", "recipient"],
				},
			},
			field_labels={"operation": "Notification Type"},
			node_type="notify",
			category="Notifications",
			configurable=True,
			config_component="NotifyConfig",
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Toast": OperationContract(
				operation="Toast",
				action_overrides=[
					{"fieldname": "action_type", "default": "Notify"},
					{"fieldname": "operation", "default": "Toast"},
					{"fieldname": "value_template", "reqd": 1},
					{"fieldname": "description", "description": "Shows a temporary notification to the user"},
				],
			),
			"System": OperationContract(
				operation="System",
				action_overrides=[
					{"fieldname": "action_type", "default": "Notify"},
					{"fieldname": "operation", "default": "System"},
					{"fieldname": "value_template", "reqd": 1},
					{"fieldname": "description", "description": "Sends a system notification"},
				],
			),
			"Email": OperationContract(
				operation="Email",
				action_overrides=[
					{"fieldname": "action_type", "default": "Notify"},
					{"fieldname": "operation", "default": "Email"},
					{"fieldname": "value_template", "reqd": 1},
					{"fieldname": "description", "description": "Sends an email notification"},
				],
				validation={"backend": "validate_email_notification"},
			),
			"System Notification": OperationContract(
				operation="System Notification",
				action_overrides=[
					{"fieldname": "action_type", "default": "Notify"},
					{"fieldname": "operation", "default": "System Notification"},
					{"fieldname": "value_template", "reqd": 1},
					{"fieldname": "description", "description": "Creates a system notification record"},
				],
			),
			"Provider": OperationContract(
				operation="Provider",
				action_overrides=[
					{"fieldname": "action_type", "default": "Notify"},
					{"fieldname": "operation", "default": "Provider"},
					{"fieldname": "value_template", "reqd": 1},
					{"fieldname": "description", "description": "Sends notification via external provider"},
				],
				validation={"backend": "validate_provider_notification"},
			),
		}

	MODE_TO_EMAIL = "Email"
	MODE_TOAST = "Toast"
	MODE_REALTIME = "System"
	MODE_SYSTEM_NOTIFICATION = "System Notification"
	MODE_PROVIDER = "Provider"

	def execute(self, action, context, engine):
		"""
		Notify action - sends notification using Jinja template and config.

		Supports notification types:
		- Toast: Browser alert message
		- System: Realtime publish to current session
		- Email: Email with configurable recipients / subject / attachments
		- System Notification: Creates a Notification Log row
		- Provider: Dispatches to a hook-registered provider
		"""
		plan = get_action_plan(engine.rule, action)
		fallback_config = engine._get_action_config(action)
		notification_type = plan.get("mode") or self._normalize_mode(
			getattr(action, "operation", self.MODE_TOAST) or self.MODE_TOAST
		)

		message = self._render_from_spec(
			plan.get("message_spec"), context, engine, default=getattr(action, "value_template", "") or ""
		)
		doc = context.get("doc")

		if notification_type == self.MODE_TOAST:
			frappe.msgprint(message, alert=True)
		elif notification_type == self.MODE_REALTIME:
			frappe.publish_realtime(
				"msgprint",
				{"message": message, "alert": True},
				user=frappe.session.user,
			)
		elif notification_type == self.MODE_TO_EMAIL:
			recipients = self._resolve_recipients_from_spec(
				plan.get("recipients_spec"), context, default_value=fallback_config.get("recipients")
			)
			subject = self._render_from_spec(
				plan.get("subject_spec"),
				context,
				engine,
				default=fallback_config.get("subject")
				or _("Rule Notification: {0}").format(engine.rule.name),
			)
			attachments = self._build_email_attachments({"attach_doc": plan.get("attach_doc")}, doc)

			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				attachments=attachments,
				reference_doctype=getattr(doc, "doctype", None),
				reference_name=getattr(doc, "name", None),
			)
		elif notification_type == self.MODE_SYSTEM_NOTIFICATION:
			subject = self._render_from_spec(
				plan.get("subject_spec"),
				context,
				engine,
				default=fallback_config.get("subject") or _("Rule Notification"),
			)
			for_user = self._resolve_value_from_spec(
				plan.get("for_user_spec"),
				context,
				default=fallback_config.get("for_user") or getattr(doc, "owner", None) or frappe.session.user,
			)

			notification = frappe.get_doc(
				{
					"doctype": "Notification Log",
					"for_user": for_user,
					"subject": subject,
					"email_content": message,
					"document_type": getattr(doc, "doctype", None),
					"document_name": getattr(doc, "name", None),
				}
			)
			notification.insert(ignore_permissions=True)
			message = notification.name
		elif notification_type == self.MODE_PROVIDER:
			config = {
				"provider": plan.get("provider") or fallback_config.get("provider"),
				"recipient": self._resolve_value_from_spec(
					plan.get("recipient_spec"), context, default=fallback_config.get("recipient")
				),
			}
			message = self._send_via_provider(config, context, message)
		else:
			frappe.throw(_("Unknown notification mode: {0}").format(notification_type))

		engine._log("INFO", _("Sent {0} notification").format(notification_type))
		return message, getattr(action, "next_step_if_true", None)

	def validate(self, action, context):
		errors = []
		mode = self._normalize_mode(getattr(action, "operation", self.MODE_TOAST) or self.MODE_TOAST)
		config = self._parse_config(getattr(action, "config", None))

		if mode == self.MODE_TO_EMAIL:
			if not config.get("recipients"):
				errors.append(_("Email notifications require recipients in config"))
			if not config.get("subject"):
				errors.append(_("Email notifications require a subject in config"))
		elif mode == self.MODE_SYSTEM_NOTIFICATION:
			if not config.get("subject"):
				errors.append(_("System Notification mode requires a subject in config"))
		elif mode == self.MODE_PROVIDER:
			if not config.get("provider"):
				errors.append(_("Provider mode requires a provider in config"))
			if not config.get("recipient"):
				errors.append(_("Provider mode requires a recipient in config"))

		return errors

	def _normalize_mode(self, mode):
		value = (mode or "").strip().lower()
		mode_map = {
			"toast": self.MODE_TOAST,
			"system": self.MODE_REALTIME,
			"email": self.MODE_TO_EMAIL,
			"system notification": self.MODE_SYSTEM_NOTIFICATION,
			"create_system_notification": self.MODE_SYSTEM_NOTIFICATION,
			"provider": self.MODE_PROVIDER,
			"realtime": self.MODE_REALTIME,
		}
		return mode_map.get(value, mode)

	def _template_context(self, context, engine=None):
		ctx = self._build_template_context(context, engine)
		ctx["context"] = context
		return ctx

	def _render_template(self, template, context, engine=None):
		template = template or ""
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		return frappe.render_template(
			template, self._template_context(context, engine)
		)  # nosemgrep: frappe-ssti

	def _render_scalar(self, value, context):
		if value is None:
			return None
		if isinstance(value, str):
			return self._render_template(value, context)
		return value

	def _render_from_spec(self, spec, context, engine=None, default=""):
		spec = spec or {}
		source = spec.get("source")
		if source == "jinja":
			return self._render_template(spec.get("value") or "", context, engine)
		if source == "literal":
			return spec.get("value")
		if isinstance(default, str):
			return self._render_template(default, context, engine)
		return default

	def _resolve_value_from_spec(self, spec, context, default=None):
		spec = spec or {}
		source = spec.get("source")
		if source == "jinja":
			return self._render_template(spec.get("value") or "", context)
		if source == "literal":
			return spec.get("value")
		if isinstance(default, str):
			return self._render_template(default, context)
		return default

	def _resolve_recipients_from_spec(self, spec, context, default_value=None):
		spec = spec or {}
		if spec.get("source") == "list":
			values = [self._resolve_value_from_spec(item, context) for item in spec.get("items") or []]
			return [v for v in values if v]
		value = self._resolve_value_from_spec(spec, context, default=default_value)
		if isinstance(value, list):
			return [v for v in value if v]
		return parse_field_list(value)

	def _get_recipients(self, recipients_value, context):
		rendered = self._render_scalar(recipients_value, context)
		if isinstance(rendered, list):
			return [r for r in rendered if r]
		return parse_field_list(rendered)

	def _build_email_attachments(self, config, doc):
		if not config.get("attach_doc") or not doc:
			return []

		try:
			return [frappe.attach_print(doc.doctype, doc.name, doc=doc)]
		except Exception as exc:
			frappe.log_error(f"Notify action: Failed to attach PDF: {exc}", "Notify Action Error")
			return []

	def _send_via_provider(self, config, context, message):
		"""Dispatch a notification through a hook-registered provider."""
		provider_name = config.get("provider")
		recipient = self._render_scalar(config.get("recipient"), context)
		providers = {}

		for app in frappe.get_installed_apps():
			app_providers = frappe.get_hooks("flexirule_notification_providers", app_name=app)
			if isinstance(app_providers, list):
				for provider_dict in app_providers:
					if isinstance(provider_dict, dict):
						providers.update(provider_dict)
			elif isinstance(app_providers, dict):
				providers.update(app_providers)

		if provider_name not in providers:
			frappe.throw(_("Notification provider '{0}' not found").format(provider_name))

		return frappe.get_attr(providers[provider_name])(
			recipient=recipient,
			message=message,
			doc=context.get("doc"),
			context=context,
			config=config,
		)


class EntryActionHandler(ActionHandler):
	"""Handler for Entry Action type - marks the start node."""

	action_type = "Entry Action"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Entry Action",
			required_fields=[],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-play", "color": "#22c55e"},
			field_labels={},
			node_type="start",
			category="Control Flow",
			configurable=False,
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Entry Action": OperationContract(
				operation="Entry Action",
				action_overrides=[
					{"fieldname": "action_type", "default": "Entry Action"},
					{"fieldname": "description", "description": "Entry point for rule execution flow"},
				],
			)
		}

	def execute(self, action, context, engine):
		"""Entry Action - simply passes through to next step."""
		return None, action.next_step_if_true


# Register all handlers
HandlerRegistry.register(StopHandler())
HandlerRegistry.register(WaitHandler())
HandlerRegistry.register(RaiseErrorHandler())
HandlerRegistry.register(NotifyHandler())
HandlerRegistry.register(EntryActionHandler())
