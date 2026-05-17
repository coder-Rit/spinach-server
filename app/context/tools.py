call_tools_prompt_raw = """
You are an intelligent assistant for a project management system.
You help users manage projects, tasks, stories, comments, and users.

{tools_context}

{rag_context}

{prioritized_messages}

## YOUR JOB
Analyze the user's message and decide whether to:
- call a tool, or
- ask the user for missing required information.

## RESPONSE FORMAT (strict)
Always respond ONLY with a raw JSON object in exactly one of these shapes:

1) When a tool can be called:
{{
  "action": "call_tool",
  "tool": "<tool_name>",
  "params": {{
    "<param_name>": "<value>",
    ...
  }},
  "reason": "<one line explaining why this tool was chosen>"
}}

2) When required information is missing:
{{
  "action": "ask_user",
  "question": "<short direct question asking for the missing information>",
  "missing_fields": ["<field_1>", "<field_2>"],
  "reason": "<one line explaining why clarification is needed>"
}}

## RULES
- `tool` must be one of the tool names from the provided tools context above.
- `params` must only include params listed under that tool's `required` or `optional` lists.
- Omit optional params (do not pass null) when defaults apply — see each tool's `defaults`.
- Never pass `db`, `current_user`, `user_id`, or `created_by`; those are injected automatically.
- For any UUID you do not know, use a lookup tool first (find_projects, find_tasks, find_users) instead of guessing.
- If a required field is missing and cannot be inferred safely, return `action = "ask_user"`.
- If the user's intent requires multiple sequential tool calls, return only the FIRST one.
- Never include explanation or markdown outside the JSON object.

## NOTE
- My User UUID: {my_uuid}

## EXAMPLES

User: "Create a task called Fix login bug in the Alpha project"
{{
  "action": "call_tool",
  "tool": "find_projects",
  "params": {{
    "project_name": "Alpha"
  }},
  "reason": "Need to resolve project UUID before creating the work item."
}}

User: "Create a task called Fix login bug"
{{
  "action": "ask_user",
  "question": "Which project should I create this task in?",
  "missing_fields": ["project_id"],
  "reason": "Project is required before creating a work item."
}}

User: "Show me all overdue tasks"
{{
  "action": "call_tool",
  "tool": "get_overdue_items",
  "params": {{}},
  "reason": "No filters needed; tool returns all overdue items by default."
}}

User: "Who am I?"
{{
  "action": "call_tool",
  "tool": "get_my_info",
  "params": {{}},
  "reason": "No params required; uses the authenticated user."
}}

User: "Assign the login bug task to Alice"
{{
  "action": "call_tool",
  "tool": "find_users",
  "params": {{
    "name": "Alice"
  }},
  "reason": "Need Alice's user_id before reassigning the work item."
}}

User: "Assign it to Alice"
{{
  "action": "ask_user",
  "question": "Which task should I assign to Alice?",
  "missing_fields": ["work_item_id"],
  "reason": "The task is required before reassignment."
}}
"""


tools_metadata = """
You are a tool-routing classifier for a project management system.

Your ONLY job is to analyze the user's message and identify which entities and operations are needed to fulfill the request.

---

## ENTITIES
As per need, Choose one or more from:
- `user`
- `project`
- `work_item`
- `comment`
- `analytics`

## OPERATIONS
As per need, Choose one or more from:
- `get`
- `create`
- `update`
- `delete`

---

## RULES
- Return ONLY a raw JSON object. No explanation, no markdown, no extra text.
- Always include `get` if any ID/name needs to be resolved before another operation.
- Multiple entities and operations are allowed if the request spans more than one.

## NOTES
- work_item also refred as tasks and stories.
- user message may contains ids like "CDA-34" meanins his taking about work_items ignore other ids that this formate.
---
## EXAMPLES

User: "Create a task in the Alpha project and assign it to John"
[
  { "entity": "project", "operation": "get" },
  { "entity": "user", "operation": "get" },
  { "entity": "work_item", "operation": "create" }
]

User: "who i am"
[
  { "entity": "user", "operation": "get" }
]

User: "Delete the comment on CAD-42"
[
  { "entity": "work_item", "operation": "get" },
  { "entity": "comment", "operation": "delete" }
]
 
---

Now classify the following:
User: "{USER_MESSAGE}"

"""


tools_info = {
    "user": {
        "get": {
            "find_users": {
                "description": "Find users by ID, email, name, or project involvement.",
                "required": [],
                "optional": ["user_ids", "emails", "name", "project_id"],
                "defaults": {},
                "notes": [
                    "Use name for partial match when resolving a person by display name.",
                    "Use before assign/reassign when assignee UUID is unknown.",
                    'Output: [{"user_id": "uuid", "name": "...", "email": "..."}]',
                ],
            },
            "get_my_info": {
                "description": "Current user's profile, managed projects, and workload.",
                "required": [],
                "optional": [],
                "defaults": {},
                "notes": [
                    "No params needed — uses the authenticated user.",
                    'Output: {"user_id", "name", "email", "managed_projects", "workload"}',
                ],
            },
        }
    },
    "project": {
        "get": {
            "find_projects": {
                "description": "Find projects by ID, partial name, manager, or status.",
                "required": [],
                "optional": ["project_ids", "project_name", "managed_by_id", "statuses"],
                "defaults": {},
                "notes": [
                    "Use project_name to resolve UUID before create/update on a project.",
                    "statuses values: OPEN, CLOSE.",
                    'Output: [{"project_id", "title", "status", "managed_by"}]',
                ],
            }
        },
        "create": {
            "create_project": {
                "description": "Create a new project.",
                "required": ["title"],
                "optional": ["description", "status", "managed_by_id"],
                "defaults": {
                    "description": "",
                    "status": "OPEN",
                    "managed_by_id": "current user",
                },
                "notes": [
                    "Do not pass managed_by_id unless the user names a different manager.",
                ],
            }
        },
        "update": {
            "update_project": {
                "description": "Update project title, description, or status.",
                "required": ["project_id"],
                "optional": ["title", "description", "status"],
                "defaults": {},
                "notes": [
                    "Only include optional fields that should change.",
                    "Resolve project_id via find_projects when unknown.",
                ],
            }
        },
        "delete": {
            "delete_project": {
                "description": "Soft-delete a project.",
                "required": ["project_id"],
                "optional": [],
                "defaults": {},
                "notes": ["Resolve project_id via find_projects when unknown."],
            }
        },
    },
    "work_item": {
        "get": {
            "find_tasks": {
                "description": "Find work items (tasks/stories) with flexible filters.",
                "required": [],
                "optional": [
                    "name",
                    "work_item_ids",
                    "project_id",
                    "display_ids",
                    "item_types",
                    "statuses",
                    "start_date",
                    "end_date",
                    "assigned_by_ids",
                    "assigned_to_ids",
                    "linked_work_item_id",
                ],
                "defaults": {},
                "notes": [
                    "Use name for partial title match; display_ids for keys like CDA-34.",
                    "item_types: TASK, STORY. statuses: TODO, IN_PROGRESS, CODE_COMPLETE, DEPLOYED_ON_STAGE, DONE.",
                    'Output: [{"work_item_id", "title", "status", "item_type", "display_id"}]',
                ],
            }
        },
        "create": {
            "create_work_item": {
                "description": "Create a task or story in a project.",
                "required": ["project_id", "title"],
                "optional": [
                    "item_type",
                    "status",
                    "assigned_to_id",
                    "description",
                    "start_date",
                    "end_date",
                    "linked_work_item_id",
                ],
                "defaults": {
                    "item_type": "TASK",
                    "status": "TODO",
                    "assigned_to_id": "current user if omitted",
                },
                "notes": [
                    "Resolve project_id via find_projects when unknown.",
                    "Resolve assigned_to_id via find_users when assigning to someone else.",
                ],
            }
        },
        "update": {
            "update_work_item": {
                "description": "Update one or more fields on a work item.",
                "required": ["work_item_id"],
                "optional": [
                    "name",
                    "item_type",
                    "description",
                    "start_date",
                    "end_date",
                    "status",
                    "assigned_to_id",
                ],
                "defaults": {},
                "notes": [
                    "Only pass fields that should change.",
                    "Resolve work_item_id via find_tasks when unknown.",
                ],
            },
            "reassign_work_item": {
                "description": "Reassign a work item to another user.",
                "required": ["work_item_id", "assigned_to_id"],
                "optional": [],
                "defaults": {},
                "notes": [
                    "Prefer over update_work_item when only the assignee changes.",
                    "Resolve IDs via find_tasks / find_users when unknown.",
                ],
            },
            "bulk_update_status": {
                "description": "Set status on multiple work items at once.",
                "required": ["work_item_ids", "status"],
                "optional": [],
                "defaults": {},
                "notes": [
                    "status: TODO, IN_PROGRESS, CODE_COMPLETE, DEPLOYED_ON_STAGE, DONE.",
                ],
            },
            "link_work_items": {
                "description": "Link a work item to another (parent/dependency).",
                "required": ["work_item_id", "linked_work_item_id"],
                "optional": [],
                "defaults": {},
                "notes": [],
            },
            "move_work_item": {
                "description": "Move a work item to a different project.",
                "required": ["work_item_id", "new_project_id"],
                "optional": [],
                "defaults": {},
                "notes": [
                    "Resolve new_project_id via find_projects when unknown.",
                ],
            },
        },
        "delete": {
            "delete_work_item": {
                "description": "Soft-delete a work item.",
                "required": ["work_item_id"],
                "optional": [],
                "defaults": {},
                "notes": ["Resolve work_item_id via find_tasks when unknown."],
            }
        },
    },
    "comment": {
        "get": {
            "list_comments": {
                "description": "List comments on a work item.",
                "required": ["work_item_id"],
                "optional": ["page", "size"],
                "defaults": {"page": 1, "size": 20},
                "notes": ["Resolve work_item_id via find_tasks when unknown."],
            }
        },
        "create": {
            "add_comment": {
                "description": "Add a comment or reply on a work item.",
                "required": ["work_item_id", "comment"],
                "optional": ["comment_reply_id"],
                "defaults": {},
                "notes": [
                    "comment_reply_id only when replying to an existing comment.",
                ],
            }
        },
        "delete": {
            "delete_comment": {
                "description": "Soft-delete a comment.",
                "required": ["comment_id"],
                "optional": [],
                "defaults": {},
                "notes": [],
            }
        },
    },
    "analytics": {
        "get": {
            "get_project_summary": {
                "description": "Project breakdown by status, type, assignee, and overdue count.",
                "required": ["project_id"],
                "optional": [],
                "defaults": {},
                "notes": [
                    "Use for 'how is project X going?' or sprint summaries.",
                    "Resolve project_id via find_projects when unknown.",
                ],
            },
            "get_user_workload": {
                "description": "A user's active items and status breakdown.",
                "required": [],
                "optional": ["user_id", "project_id"],
                "defaults": {"user_id": "current user"},
                "notes": [
                    "Omit user_id for the current user; set it after find_users for someone else.",
                ],
            },
            "get_overdue_items": {
                "description": "Work items past end date that are not DONE.",
                "required": [],
                "optional": ["project_id", "assigned_to_id"],
                "defaults": {},
                "notes": [
                    "Omit both filters for all overdue items.",
                ],
            },
        }
    },
}


def get_tool_required_fields() -> dict[str, list[str]]:
    """Flatten tools_info into tool_name -> required param names."""
    required: dict[str, list[str]] = {}
    for operations in tools_info.values():
        for tools in operations.values():
            for tool_name, spec in tools.items():
                required[tool_name] = spec.get("required", [])
    return required
