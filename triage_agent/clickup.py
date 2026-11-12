import json
import os
from urllib.request import Request, urlopen

from .models import Finding


def create_or_print_ticket(finding: Finding) -> str:
    token = os.getenv("CLICKUP_API_TOKEN")
    list_id = os.getenv("CLICKUP_LIST_ID")
    if not token or not list_id:
        print("\nClickUp is not configured; console-only finding follows.\n")
        print(finding.model_dump_json(indent=2))
        return "console"

    description = (
        f"{finding.summary}\n\nSeverity: {finding.severity}\n\n"
        "Evidence:\n" + "\n".join(f"- {item}" for item in finding.evidence)
        + f"\n\nSuggested next step:\n{finding.suggested_next_step}"
    )
    body = json.dumps({
        "name": finding.title,
        "description": description,
        "priority": finding.priority,
    }).encode("utf-8")
    request = Request(
        f"https://api.clickup.com/api/v2/list/{list_id}/task",
        data=body,
        headers={"Authorization": token, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    task_id = result.get("id", "unknown")
    url = result.get("url", "")
    print(f"Created ClickUp task {task_id}: {url}")
    return str(task_id)
