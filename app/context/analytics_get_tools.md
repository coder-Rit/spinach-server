### ANALYTICS — GET TOOLS

**get_project_summary(project_id)**
Returns a project's total work items broken down by status, type, assignee, and overdue count.
- Use when the user asks "how's project X going?" or "give me a sprint summary".

**get_user_workload(user_id, project_id)**
Returns a user's active work items and a status breakdown. `project_id` is optional to scope it.
- Use when asked "what is Alice working on?" or "is someone overloaded?".

**get_overdue_items(project_id, assigned_to)**
Returns all work items past their end date that are not yet DONE. Both filters are optional.
- Use when asked "what's overdue?" or "show late tasks".
