"""Canonical tool + task definitions for six tool families.

Train families (calendar, crm, finance) and held-out test families
(travel, legal, developer_tools) mirror the tool-family split in
section 18 of the PTIM design doc, so downstream evaluation can measure
generalization to genuinely unseen tool families rather than leaking
near-duplicate tools across train/test.

Task queries are deliberately grounded (concrete dates/IDs) rather than
relying on relative phrasing ("tomorrow", "the Johnson case") for whatever
a tool's `required_fields` demands. This was not a stylistic choice -- the
first real run showed the model correctly declining to call a tool and
asking a clarifying question (e.g. "what's today's date?", "what's the
event ID?") whenever a required field had no unambiguous value in the
query. That's sensible model behavior, not a measurement bug; the fix is
grounding the query and/or marking genuinely optional fields as optional
(via `required_fields`), not fighting the model into guessing.
"""
from __future__ import annotations

from stage0_falsification.common import Tool, Task

TRAIN_FAMILIES = ["calendar", "crm", "finance", "email"]
TEST_FAMILIES = ["travel", "legal", "developer_tools", "project_management"]
ALL_FAMILIES = TRAIN_FAMILIES + TEST_FAMILIES


def _tools(family: str, specs: list[tuple]) -> list[Tool]:
    """Each spec is (name, description, input_schema) or
    (name, description, input_schema, required_fields)."""
    tools = []
    for spec in specs:
        name, description, schema = spec[0], spec[1], spec[2]
        required = spec[3] if len(spec) > 3 else None
        tools.append(Tool(name=name, description=description, family=family,
                           input_schema=schema, required_fields=required))
    return tools


CALENDAR_TOOLS = _tools("calendar", [
    ("create_event", "Create a new calendar event with a title, start time, end time, and optional attendees.",
     {"title": "string", "start_time": "string", "end_time": "string", "attendees": "array", "location": "string"},
     ["title", "start_time", "end_time"]),
    ("list_events", "List calendar events within a given date range.",
     {"start_date": "string", "end_date": "string"}),
    ("delete_event", "Delete an existing calendar event by its event ID.",
     {"event_id": "string"}),
    ("update_event", "Update the time, title, or attendees of an existing calendar event.",
     {"event_id": "string", "title": "string", "start_time": "string", "end_time": "string", "attendees": "array"},
     ["event_id"]),
    ("find_free_slot", "Find a free time slot for a meeting among a list of attendees within a date range.",
     {"attendees": "array", "duration_minutes": "integer", "start_date": "string", "end_date": "string"},
     ["attendees", "duration_minutes"]),
    ("set_reminder", "Set a reminder notification for an existing calendar event.",
     {"event_id": "string", "minutes_before": "integer"}),
])

CALENDAR_TASKS = [
    Task("Schedule a 30 minute meeting titled 'Product Sync' with Alice and Bob on 2026-08-28 from 14:00 to 14:30.",
         "calendar", "create_event"),
    Task("What's on my calendar between 2026-09-01 and 2026-09-07?", "calendar", "list_events"),
    Task("Cancel my meeting with event ID evt_4471.", "calendar", "delete_event"),
    Task("Move the appointment with event ID evt_2290 to 2026-09-02 at 10:00.", "calendar", "update_event"),
    Task("Find a free 60 minute slot for Sarah and me sometime in the next week.", "calendar", "find_free_slot"),
]

CRM_TOOLS = _tools("crm", [
    ("create_contact", "Create a new contact record in the CRM with name, email, and company.",
     {"name": "string", "email": "string", "company": "string", "phone": "string"},
     ["name", "email"]),
    ("search_contacts", "Search CRM contacts by name, company, or email.",
     {"query": "string"}),
    ("update_contact", "Update fields on an existing CRM contact record.",
     {"contact_id": "string", "fields": "object"}),
    ("log_activity", "Log a call, email, or meeting activity against a CRM contact or deal.",
     {"contact_id": "string", "activity_type": "string", "notes": "string"},
     ["contact_id", "activity_type"]),
    ("create_deal", "Create a new sales deal or opportunity linked to a contact or company.",
     {"contact_id": "string", "deal_name": "string", "value": "number", "stage": "string"},
     ["contact_id", "deal_name", "value"]),
    ("list_deals", "List sales deals filtered by stage or owner.",
     {"stage": "string", "owner": "string"}, []),
])

CRM_TASKS = [
    Task("Add a new contact named John Smith from Acme Corp, email john.smith@acmecorp.com.",
         "crm", "create_contact"),
    Task("Find the contact record for someone named Priya.", "crm", "search_contacts"),
    Task("Log a call activity against contact ID contact_882 with notes 'Discussed Q3 renewal.'",
         "crm", "log_activity"),
    Task("Open a new deal named 'Acme Corp Renewal' worth $50000 for contact ID contact_882.",
         "crm", "create_deal"),
    Task("Show me all deals currently in the negotiation stage.", "crm", "list_deals"),
]

FINANCE_TOOLS = _tools("finance", [
    ("get_account_balance", "Retrieve the current balance for a given financial account.",
     {"account_id": "string"}),
    ("list_transactions", "List recent transactions for an account within a date range.",
     {"account_id": "string", "start_date": "string", "end_date": "string"}),
    ("transfer_funds", "Transfer funds between two accounts.",
     {"from_account": "string", "to_account": "string", "amount": "number"}),
    ("categorize_transaction", "Assign a spending category to a transaction.",
     {"transaction_id": "string", "category": "string"}),
    ("generate_expense_report", "Generate a summarized expense report for a date range.",
     {"start_date": "string", "end_date": "string", "group_by": "string"},
     ["start_date", "end_date"]),
    ("set_budget_alert", "Set an alert that triggers when spending in a category exceeds a threshold.",
     {"category": "string", "threshold": "number"}),
])

FINANCE_TASKS = [
    Task("What's the balance of account acct_1001 (checking)?", "finance", "get_account_balance"),
    Task("Show me all transactions for account acct_1001 between 2026-07-01 and 2026-07-31.",
         "finance", "list_transactions"),
    Task("Move $200 from my savings account to my checking account.", "finance", "transfer_funds"),
    Task("Tag transaction txn_5521 (the Starbucks charge) as dining.", "finance", "categorize_transaction"),
    Task("Give me an expense report from 2026-01-01 to 2026-03-31, grouped by category.",
         "finance", "generate_expense_report"),
]

TRAVEL_TOOLS = _tools("travel", [
    ("search_flights", "Search for available flights between two cities on a given date.",
     {"origin": "string", "destination": "string", "date": "string", "passengers": "integer"},
     ["origin", "destination", "date"]),
    ("book_flight", "Book a specific flight itinerary for a passenger.",
     {"flight_id": "string", "passenger_name": "string"}),
    ("search_hotels", "Search for available hotels in a city for a given date range.",
     {"city": "string", "check_in": "string", "check_out": "string"}),
    ("book_hotel", "Book a specific hotel room.",
     {"hotel_id": "string", "check_in": "string", "check_out": "string", "guest_name": "string"}),
    ("cancel_booking", "Cancel an existing flight or hotel booking by confirmation number.",
     {"confirmation_number": "string"}),
    ("get_itinerary", "Retrieve the full travel itinerary for an upcoming trip.",
     {"trip_id": "string"}),
])

TRAVEL_TASKS = [
    Task("Find flights from Chicago to Denver on 2026-09-04 for 1 passenger.", "travel", "search_flights"),
    Task("Book flight FL2291 for passenger Jordan Lee.", "travel", "book_flight"),
    Task("Find a hotel in Denver for check-in 2026-09-05 and check-out 2026-09-07.",
         "travel", "search_hotels"),
    Task("Cancel my hotel booking, confirmation ABC123.", "travel", "cancel_booking"),
    Task("What's my full itinerary for trip trip_7734 (the Denver trip)?", "travel", "get_itinerary"),
]

LEGAL_TOOLS = _tools("legal", [
    ("search_case_law", "Search case law database for precedents matching a legal query.",
     {"query": "string", "jurisdiction": "string"},
     ["query"]),
    ("draft_clause", "Draft a standard contract clause of a given type.",
     {"clause_type": "string", "parameters": "object"},
     ["clause_type"]),
    ("review_contract", "Review an uploaded contract for risk flags and non-standard terms.",
     {"document_id": "string"}),
    ("redline_document", "Generate redline/track-changes suggestions for a document against a template.",
     {"document_id": "string", "template_id": "string"}),
    ("lookup_statute", "Look up the text of a specific statute or regulation by citation.",
     {"citation": "string"}),
    ("file_deadline_reminder", "Set a reminder for a legal filing deadline.",
     {"case_id": "string", "deadline_date": "string", "description": "string"},
     ["case_id", "deadline_date"]),
])

LEGAL_TASKS = [
    Task("Find precedents on non-compete enforceability in California.", "legal", "search_case_law"),
    Task("Draft a standard indemnification clause.", "legal", "draft_clause"),
    Task("Review the NDA with document ID doc_3391 for anything unusual.", "legal", "review_contract"),
    Task("What does 17 U.S.C. section 512 say?", "legal", "lookup_statute"),
    Task("Set a filing deadline reminder for case case_5510 (the Johnson case) due on 2026-09-15.",
         "legal", "file_deadline_reminder"),
]

DEVELOPER_TOOLS_TOOLS = _tools("developer_tools", [
    ("search_codebase", "Search the codebase for a symbol, string, or pattern.",
     {"query": "string", "path": "string"},
     ["query"]),
    ("run_tests", "Run the test suite or a specific test file.",
     {"test_path": "string"}),
    ("create_pull_request", "Open a pull request from a branch with a title and description.",
     {"branch": "string", "title": "string", "description": "string"},
     ["branch", "title"]),
    ("get_build_status", "Get the current CI build status for a branch or commit.",
     {"branch": "string"}),
    ("deploy_service", "Deploy a service to a target environment.",
     {"service": "string", "environment": "string", "version": "string"},
     ["service", "environment"]),
    ("rollback_deploy", "Roll back a service deployment to a previous version.",
     {"service": "string", "environment": "string"}),
])

DEVELOPER_TOOLS_TASKS = [
    Task("Find where the auth token is validated.", "developer_tools", "search_codebase"),
    Task("Run the tests at path tests/payments/.", "developer_tools", "run_tests"),
    Task("Open a pull request from branch feature/checkout-fix titled 'Fix checkout rounding bug'.",
         "developer_tools", "create_pull_request"),
    Task("Is the main branch build passing?", "developer_tools", "get_build_status"),
    Task("Deploy the checkout service to staging.", "developer_tools", "deploy_service"),
]

EMAIL_TOOLS = _tools("email", [
    ("send_email", "Send an email with a subject, body, and one or more recipients.",
     {"to": "array", "subject": "string", "body": "string", "cc": "array"},
     ["to", "subject", "body"]),
    ("search_inbox", "Search the inbox for emails matching a query.",
     {"query": "string"}),
    ("delete_email", "Delete an email by its message ID.",
     {"message_id": "string"}),
    ("mark_as_read", "Mark an email as read or unread by its message ID.",
     {"message_id": "string", "read": "boolean"}),
    ("create_draft", "Create a draft email with a subject and body, without sending it.",
     {"subject": "string", "body": "string", "to": "array"},
     ["subject", "body"]),
    ("add_label", "Add a label or tag to an email by its message ID.",
     {"message_id": "string", "label": "string"}),
])

EMAIL_TASKS = [
    Task("Send an email to jordan@example.com with subject 'Q3 Report' and body "
         "'Please find the Q3 report attached.'", "email", "send_email"),
    Task("Search my inbox for emails about 'invoice'.", "email", "search_inbox"),
    Task("Delete the email with message ID msg_8821.", "email", "delete_email"),
    Task("Mark the email with message ID msg_4410 as read.", "email", "mark_as_read"),
    Task("Create a draft email with subject 'Meeting Notes' and body "
         "'Draft notes from today's meeting.'", "email", "create_draft"),
]

PROJECT_MANAGEMENT_TOOLS = _tools("project_management", [
    ("create_ticket", "Create a new ticket or issue with a title, description, and priority.",
     {"title": "string", "description": "string", "priority": "string", "assignee": "string"},
     ["title", "description"]),
    ("search_tickets", "Search tickets by keyword, status, or assignee.",
     {"query": "string"}),
    ("update_ticket_status", "Update the status of an existing ticket by its ticket ID.",
     {"ticket_id": "string", "status": "string"}),
    ("assign_ticket", "Assign an existing ticket to a team member by ticket ID.",
     {"ticket_id": "string", "assignee": "string"}),
    ("add_comment", "Add a comment to an existing ticket by ticket ID.",
     {"ticket_id": "string", "comment": "string"}),
    ("create_sprint", "Create a new sprint with a name and date range.",
     {"name": "string", "start_date": "string", "end_date": "string"}),
])

PROJECT_MANAGEMENT_TASKS = [
    Task("Create a ticket titled 'Login button broken' with description 'Login button does not "
         "respond on mobile Safari' and priority high.", "project_management", "create_ticket"),
    Task("Search tickets for anything related to 'checkout'.", "project_management", "search_tickets"),
    Task("Update ticket TCK-2291 status to in-progress.", "project_management", "update_ticket_status"),
    Task("Assign ticket TCK-2291 to Maria.", "project_management", "assign_ticket"),
    Task("Add a comment 'Reproduced on staging' to ticket TCK-2291.", "project_management", "add_comment"),
]

FAMILY_TOOLS: dict[str, list[Tool]] = {
    "calendar": CALENDAR_TOOLS,
    "crm": CRM_TOOLS,
    "finance": FINANCE_TOOLS,
    "travel": TRAVEL_TOOLS,
    "legal": LEGAL_TOOLS,
    "developer_tools": DEVELOPER_TOOLS_TOOLS,
    "email": EMAIL_TOOLS,
    "project_management": PROJECT_MANAGEMENT_TOOLS,
}

FAMILY_TASKS: dict[str, list[Task]] = {
    "calendar": CALENDAR_TASKS,
    "crm": CRM_TASKS,
    "finance": FINANCE_TASKS,
    "travel": TRAVEL_TASKS,
    "legal": LEGAL_TASKS,
    "developer_tools": DEVELOPER_TOOLS_TASKS,
    "email": EMAIL_TASKS,
    "project_management": PROJECT_MANAGEMENT_TASKS,
}
