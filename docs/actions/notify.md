# Notify Action

The **Notify** action sends alerts and communications to users or external systems.

## Notification Channels
- **Toast**: A temporary browser notification that appears in the Frappe UI.
- **System Notification**: A permanent entry in the user's notification log.
- **Email**: Sends an email via Frappe's email queue.
- **External Provider**: Dispatches a notification through a custom registered provider (e.g., SMS, Slack).

## Content
All fields (Subject, Message, Recipients) support Jinja templates, allowing for highly personalized and data-driven notifications.

## Usage
Notifications are commonly used for:
- Informing a manager of a pending approval.
- Alerting a user about a validation error or a successful background process.
- Sending transaction summaries to customers.
