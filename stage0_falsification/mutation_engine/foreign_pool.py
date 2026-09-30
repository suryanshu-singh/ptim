"""A pool of tools semantically unrelated to every family in tool_families.py.

Used as the source of "random addition" candidates (mutation_type="random"):
tools that share no domain vocabulary with the target family, so they act as
a near-zero-interference control.
"""
from __future__ import annotations

from stage0_falsification.common import Tool

FOREIGN_TOOLS: list[Tool] = [
    Tool("convert_currency", "Convert an amount from one currency to another using current exchange rates.",
         "utility", {"amount": "number", "from_currency": "string", "to_currency": "string"}),
    Tool("translate_text", "Translate a piece of text from one language to another.",
         "utility", {"text": "string", "target_language": "string"}),
    Tool("generate_qr_code", "Generate a QR code image encoding a given URL or text string.",
         "utility", {"content": "string"}),
    Tool("check_weather", "Get the current weather forecast for a given city.",
         "utility", {"city": "string", "date": "string"}),
    Tool("compress_file", "Compress a file or folder into a zip archive.",
         "utility", {"path": "string"}),
    Tool("send_fax", "Send a fax containing a document to a given fax number.",
         "utility", {"fax_number": "string", "document_id": "string"}),
]


def foreign_tool_for(seed: int) -> Tool:
    return FOREIGN_TOOLS[seed % len(FOREIGN_TOOLS)]
