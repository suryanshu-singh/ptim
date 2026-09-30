"""Per-family candidate-addition sets: several candidates of each mutation type per family.

Concrete instantiation of the five mutation types in mutation_engine.py. Stage 0.5
scales this from 1-of-each (5/family, 30 total) to roughly 8/family (~48 total,
matching the design doc's "if the generator naturally produces 48-52, that's
acceptable") by adding a second near_duplicate, a second schema_confusable, and a
second random candidate per family. mixed_realistic and description_confusable stay
at one each -- mixed_realistic because it's a single hand-authored "what would a real
catalog add next" tool per family, description_confusable because one high-lexical-
overlap distractor per family is enough to cover that mutation type.
"""
from __future__ import annotations

from stage0_falsification.common import Tool
from stage0_falsification.catalog_generator.tool_families import FAMILY_TOOLS
from stage0_falsification.mutation_engine.mutation_engine import (
    make_random, make_near_duplicate, make_schema_confusable,
    make_description_confusable, make_mixed_realistic,
)

_SPEC = {
    "calendar": dict(
        near_dup_bases=["create_event", "list_events"],
        schema_confusable=[
            dict(base="create_event", new_name="book_conference_room",
                 new_desc="Book a conference room for a given time window."),
            dict(base="find_free_slot", new_name="check_room_availability",
                 new_desc="Check whether a specific room is available for a given duration within a date range."),
        ],
        desc_base="delete_event", desc_new_name="archive_old_events",
        desc_new_schema={"older_than_days": "integer"},
        random_seeds=[0, 3],
    ),
    "crm": dict(
        near_dup_bases=["create_contact", "create_deal"],
        schema_confusable=[
            dict(base="create_contact", new_name="register_vendor",
                 new_desc="Register a new third-party vendor in the vendor management system."),
            dict(base="log_activity", new_name="record_support_ticket",
                 new_desc="Record a support ticket against a contact with a ticket type and notes."),
        ],
        desc_base="search_contacts", desc_new_name="search_marketing_campaigns",
        desc_new_schema={"campaign_status": "string"},
        random_seeds=[1, 4],
    ),
    "finance": dict(
        near_dup_bases=["get_account_balance", "list_transactions"],
        schema_confusable=[
            dict(base="list_transactions", new_name="list_scheduled_payments",
                 new_desc="List upcoming scheduled payments within a date range."),
            dict(base="categorize_transaction", new_name="flag_disputed_transaction",
                 new_desc="Flag a transaction as disputed under a given dispute category."),
        ],
        desc_base="transfer_funds", desc_new_name="convert_investment_holdings",
        desc_new_schema={"holding_id": "string", "target_fund": "string"},
        random_seeds=[2, 5],
    ),
    "travel": dict(
        near_dup_bases=["search_flights", "search_hotels"],
        schema_confusable=[
            dict(base="search_flights", new_name="search_train_routes",
                 new_desc="Search for available train routes between two cities on a given date."),
            dict(base="book_flight", new_name="check_in_passenger",
                 new_desc="Check in a passenger for their flight ahead of departure."),
        ],
        desc_base="cancel_booking", desc_new_name="dispute_charge",
        desc_new_schema={"transaction_id": "string", "reason": "string"},
        random_seeds=[3, 0],
    ),
    "legal": dict(
        near_dup_bases=["search_case_law", "draft_clause"],
        schema_confusable=[
            dict(base="search_case_law", new_name="search_regulatory_filings",
                 new_desc="Search a regulatory filings database matching a query within a jurisdiction."),
            dict(base="review_contract", new_name="archive_document",
                 new_desc="Archive a legal document by its document ID."),
        ],
        desc_base="draft_clause", desc_new_name="translate_contract",
        desc_new_schema={"document_id": "string", "target_language": "string"},
        random_seeds=[4, 1],
    ),
    "developer_tools": dict(
        near_dup_bases=["run_tests", "deploy_service"],
        schema_confusable=[
            dict(base="create_pull_request", new_name="create_release_notes",
                 new_desc="Create release notes for a branch with a title and description."),
            dict(base="get_build_status", new_name="get_last_commit_author",
                 new_desc="Get the author of the last commit on a branch."),
        ],
        desc_base="get_build_status", desc_new_name="get_deployment_health",
        desc_new_schema={"service": "string", "environment": "string"},
        random_seeds=[5, 2],
    ),
    "email": dict(
        near_dup_bases=["search_inbox", "delete_email"],
        schema_confusable=[
            dict(base="send_email", new_name="post_announcement",
                 new_desc="Post an announcement to a channel with a subject and body, cc'ing additional recipients."),
            dict(base="create_draft", new_name="compose_template",
                 new_desc="Compose a reusable message template with a subject, body, and default recipients."),
        ],
        desc_base="mark_as_read", desc_new_name="toggle_notification_mute",
        desc_new_schema={"message_id": "string", "muted": "boolean"},
        random_seeds=[0, 4],
    ),
    "project_management": dict(
        near_dup_bases=["create_ticket", "search_tickets"],
        schema_confusable=[
            dict(base="update_ticket_status", new_name="update_deployment_status",
                 new_desc="Update the deployment status of an existing release by its release ID."),
            dict(base="assign_ticket", new_name="reassign_reviewer",
                 new_desc="Reassign the reviewer for an existing pull request by its ID."),
        ],
        desc_base="add_comment", desc_new_name="log_time_entry",
        desc_new_schema={"ticket_id": "string", "hours": "number"},
        random_seeds=[1, 5],
    ),
}


def candidates_for_family(family: str, random_seed: int = 0) -> list[Tool]:
    tools_by_name = {t.name: t for t in FAMILY_TOOLS[family]}
    spec = _SPEC[family]

    candidates = [make_random(family, seed) for seed in spec["random_seeds"]]
    candidates += [make_near_duplicate(tools_by_name[name]) for name in spec["near_dup_bases"]]
    candidates += [
        make_schema_confusable(tools_by_name[sc["base"]], sc["new_name"], sc["new_desc"])
        for sc in spec["schema_confusable"]
    ]
    candidates.append(make_description_confusable(
        tools_by_name[spec["desc_base"]], spec["desc_new_name"], spec["desc_new_schema"]
    ))
    candidates.append(make_mixed_realistic(family))

    return candidates
