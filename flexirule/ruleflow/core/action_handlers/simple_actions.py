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
from flexirule.ruleflow.core.engine import SafeFrappeAPI
from flexirule.ruleflow.utils.field_resolver import parse_field_list


class StopHandler(ActionHandler):
	"""Handler for Stop action type - terminates rule execution."""

	action_type = "Stop"

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
			template_context = {
				"doc": context.get("doc"),
				"vars": context.get("vars", {}),
				"frappe": SafeFrappeAPI(),
				"utils": frappe.utils,
				"rule": engine.rule,
				"rule_url": frappe.utils.get_url_to_form("Rule", engine.rule.name),
			}
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


class SetValueHandler(ActionHandler):
	"""Handler for Set Value action type - updates document fields."""

	action_type = "Set Value"

	def execute(self, action, context, engine):
		"""
		Set Value action - updates a field or context variable using a Jinja template.

		Operations:
		- Current Document: sets target_field on context['doc']
		- Context Variable: sets variable_name in context['vars']
		- Reference Document: sets target_field on a referenced document via db.set_value
		"""
		operation = getattr(action, "operation", "Current Document")
		value_template = getattr(action, "value_template", "") or ""

		# Render Jinja template with SafeFrappeAPI to prevent write operations inside template
		template_context = {
			"doc": context.get("doc"),
			"vars": context.get("vars", {}),
			"frappe": SafeFrappeAPI(),
			"utils": frappe.utils,
			"rule": engine.rule,
			"rule_url": frappe.utils.get_url_to_form("Rule", engine.rule.name),
		}
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		rendered_value = frappe.render_template(value_template, template_context)  # nosemgrep: frappe-ssti

		if operation == "Context Variable":
			variable_name = getattr(action, "variable_name", None)
			if not variable_name:
				engine._log("WARNING", _("Set Value action missing variable_name"))
			else:
				if "vars" not in context:
					context["vars"] = {}
				context["vars"][variable_name] = rendered_value
				engine._log("INFO", _("Set context var {0} = {1}").format(variable_name, rendered_value))

		elif operation == "Reference Document":
			target_field = getattr(action, "target_field", None)
			ref_doctype = getattr(action, "reference_doctype", None)
			ref_docname_tpl = getattr(action, "reference_docname", None)

			if not target_field or not ref_doctype or not ref_docname_tpl:
				engine._log("WARNING", _("Set Value action missing target_field or reference details"))
			else:
				# Render the docname in case it contains a template variable
				ref_docname = frappe.render_template(  # nosemgrep: frappe-ssti
					ref_docname_tpl, template_context
				)
				if ref_docname:
					frappe.db.set_value(ref_doctype, ref_docname, target_field, rendered_value)
					engine._log(
						"INFO",
						_("Set {0} {1} field {2} = {3}").format(
							ref_doctype, ref_docname, target_field, rendered_value
						),
					)
				else:
					engine._log("WARNING", _("Resolved reference_docname is empty"))

		else:
			# Default to Current Document
			target_field = getattr(action, "target_field", None)
			if not target_field:
				engine._log("WARNING", _("Set Value action missing target_field"))
			else:
				doc = context.get("doc")
				if doc and hasattr(doc, "set"):
					doc.set(target_field, rendered_value)
					engine._log(
						"INFO", _("Set {0} = {1} on current document").format(target_field, rendered_value)
					)
				else:
					engine._log("WARNING", _("Cannot set field - no document in context"))

		return rendered_value, getattr(action, "next_step_if_true", None)


class RaiseErrorHandler(ActionHandler):
	"""Handler for Raise Error action type - throws ValidationError."""

	action_type = "Raise Error"

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
		template_context = {
			"doc": context.get("doc"),
			"vars": context.get("vars", {}),
			"frappe": SafeFrappeAPI(),
			"utils": frappe.utils,
			"rule": engine.rule,
			"rule_url": frappe.utils.get_url_to_form("Rule", engine.rule.name),
		}
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
		value_template = getattr(action, "value_template", "") or ""
		notification_type = self._normalize_mode(
			getattr(action, "operation", self.MODE_TOAST) or self.MODE_TOAST
		)
		config = engine._get_action_config(action)

		message = self._render_template(value_template, context, engine)
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
			recipients = self._get_recipients(config.get("recipients"), context)
			subject_template = config.get("subject") or _("Rule Notification: {0}").format(engine.rule.name)
			subject = self._render_template(subject_template, context, engine)
			attachments = self._build_email_attachments(config, doc)

			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				attachments=attachments,
				reference_doctype=getattr(doc, "doctype", None),
				reference_name=getattr(doc, "name", None),
			)
		elif notification_type == self.MODE_SYSTEM_NOTIFICATION:
			subject_template = config.get("subject") or _("Rule Notification")
			subject = self._render_template(subject_template, context, engine)
			for_user_template = config.get("for_user") or getattr(doc, "owner", None) or frappe.session.user
			for_user = self._render_scalar(for_user_template, context)

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
		return {
			"doc": context.get("doc"),
			"vars": context.get("vars", {}),
			"context": context,
			"frappe": SafeFrappeAPI(),
			"utils": frappe.utils,
			"rule": engine.rule if engine else None,
			"rule_url": frappe.utils.get_url_to_form("Rule", engine.rule.name) if engine else None,
		}

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

	def execute(self, action, context, engine):
		"""Entry Action - simply passes through to next step."""
		return None, action.next_step_if_true


# Register all handlers
HandlerRegistry.register(StopHandler())
HandlerRegistry.register(WaitHandler())
HandlerRegistry.register(SetValueHandler())
HandlerRegistry.register(RaiseErrorHandler())
HandlerRegistry.register(NotifyHandler())
HandlerRegistry.register(EntryActionHandler())
