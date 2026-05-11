# Tools File Structure

Tool context files follow the naming convention: `{entity}_{operation}_tools.md`

## Entities & Operations

| Entity       | Operations                        | Files                                                                                     |
|--------------|-----------------------------------|-------------------------------------------------------------------------------------------|
| `user`       | `get`                             | `user_get_tools.md`                                                                       |
| `project`    | `get`, `create`, `update`, `delete` | `project_get_tools.md`, `project_create_tools.md`, `project_update_tools.md`, `project_delete_tools.md` |
| `work_item`  | `get`, `create`, `update`, `delete` | `work_item_get_tools.md`, `work_item_create_tools.md`, `work_item_update_tools.md`, `work_item_delete_tools.md` |
| `comment`    | `get`, `create`, `delete`         | `comment_get_tools.md`, `comment_create_tools.md`, `comment_delete_tools.md`              |
| `analytics`  | `get`                             | `analytics_get_tools.md`                                                                  |

## Operation Definitions

- **get** — Read, search, or list records (no side effects).
- **create** — Insert a new record.
- **update** — Modify an existing record (includes reassign, bulk status, link, move).
- **delete** — Soft-delete a record.

## Adding New Tools

1. Identify the entity and operation.
2. Create a file: `{entity}_{operation}_tools.md`.
3. No code changes needed — `chat_helpers.py` loads all `*_tools.md` files automatically.
