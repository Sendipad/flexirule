# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Loop Action Handler.

Implements iteration over collections with loop state management.
"""

from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import ActionContract


class LoopHandler(ActionHandler):
	"""Handler for Loop action type."""

	action_type = "Loop"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Loop",
			required_fields=["config", "return_variable"],
			has_next_true=True,
			has_next_false=True,
			terminal=False,
			css={"icon": "fa fa-refresh", "color": "#f59e0b"},
			field_labels={
				"return_variable": "Item Alias",
			},
			show_return_variable=True,
			require_return_variable=True,
			node_type="loop",
			category="Control Flow",
			configurable=True,
			config_component="LoopConfig",
		)

	def execute(self, action, context, engine):
		"""
		Execute loop iteration logic.

		Manages iteration state in context['vars']['_loops'][action_id].
		Each execution advances the loop by one iteration.

		Config options:
		- iterator: Expression to resolve to iterable (e.g., "doc.items")
		- alias: Variable name for current item (default: "item")

		Context variables set:
		- vars[alias]: Current item
		- vars['loop']: Dict with index, first, last, length

		Returns:
		    Tuple of (has_more, next_action_id)
		    - next_step_if_true while iterating
		    - next_step_if_false when complete
		"""
		# Initialize loop state storage
		if "_loops" not in context["vars"]:
			context["vars"]["_loops"] = {}

		loop_state = context["vars"]["_loops"].get(action.action_id, {"index": 0, "initialized": False})

		config = engine._get_action_config(action)

		iterator_name = config.get("iterator")  # e.g., "doc.items" or "vars.my_list"
		item_alias = action.return_variable or config.get("alias") or "item"

		items = []
		if iterator_name:
			# Resolve iterator expression
			items = engine._evaluate_python_value(iterator_name, context, default=[])

		if not isinstance(items, list | tuple):
			engine._log(
				"WARNING",
				_("Loop iterator {0} is not a list/tuple. Got {1}").format(iterator_name, type(items)),
			)
			items = []

		current_index = loop_state["index"]

		if current_index < len(items):
			# Valid iteration - set context variables
			item = items[current_index]
			context["vars"][item_alias] = item
			context["vars"]["loop"] = {
				"index": current_index,
				"first": current_index == 0,
				"last": current_index == len(items) - 1,
				"length": len(items),
			}

			# Advance index for next iteration
			loop_state["index"] += 1
			context["vars"]["_loops"][action.action_id] = loop_state
			return True, action.next_step_if_true
		else:
			# Loop finished - cleanup
			if action.action_id in context["vars"]["_loops"]:
				del context["vars"]["_loops"][action.action_id]
			return False, action.next_step_if_false


# Register the handler
HandlerRegistry.register(LoopHandler())
