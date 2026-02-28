# SmartRoute

Intelligent intake/extraction engine for inspector communications. Transforms messy inspector emails, portal text, and OCR'd attachments into normalized structured records with action routing.

## Features

- **Text Cleaning**: Removes security banners, email headers, reply quotes, and signatures
- **Hybrid Extraction**: Combines deterministic regex patterns with optional LLM enhancement
- **Field Normalization**: Standardizes dates, phone numbers, status terms, and addresses
- **Smart Routing**: Determines action requirements and routes to appropriate teams
- **Quality Metrics**: Provides confidence scores and identifies missing required fields

## Installation

```bash
pip install -e .
```

With LLM support:
```bash
pip install -e ".[llm]"
```

With development dependencies:
```bash
pip install -e ".[dev]"
```

## Quick Start

### Python API

```python
from smartroute import parse_message, Attachment

# Parse a simple email
raw_email = """
Permit #2511463
Address: 123 Main Street, Columbia, SC 29201
Inspection Status: Pass

The electrical inspection has been completed.
"""

record = parse_message(raw_email)

print(f"Permit: {record.permit.permit_number}")
print(f"Status: {record.inspection.status.value}")
print(f"Action Required: {record.operational.action_required}")
print(f"Route To: {record.operational.route_to_team.value}")
```

### With Attachments

```python
from smartroute import parse_message, Attachment

attachment = Attachment(
    filename="inspection_report.txt",
    content_type="text/plain",
    extracted_text="Additional details from OCR..."
)

record = parse_message(raw_email, attachments=[attachment])
```

### With LLM Enhancement

```python
from smartroute import parse_message
from smartroute.extractors import OpenAIClient

# Set OPENAI_API_KEY environment variable or pass directly
client = OpenAIClient()
record = parse_message(raw_email, llm_client=client)
```

### CLI Usage

```bash
# Basic usage
python -m smartroute.pipeline --input email.txt --out result.json

# With pretty printing
python -m smartroute.pipeline -i email.txt -o result.json --pretty

# With attachments
python -m smartroute.pipeline -i email.txt -a attachment1.txt -a attachment2.txt

# Specify source type
python -m smartroute.pipeline -i portal_text.txt --source-type portal
```

## Output Schema

The parser outputs a structured `SmartrouteRecord` with the following sections:

- **source**: Original and cleaned text, attachments
- **jurisdiction**: Name, county, state
- **permit**: Permit number, type, category
- **inspection**: Type, dates, status, notes
- **release**: Release type, date, structure type, reason
- **site**: Full address and parsed components
- **contacts**: Inspector, contractor, owner details
- **operational**: Routing decisions (action_required, route_to_team, priority)
- **quality**: Confidence scores and missing field identification

## Routing Logic

The router determines:

- **Action Required**: Based on status (fail), keywords (correction, reinspection), or release triggers
- **Route To Team**:
  - `RELEASE_DESK`: Release approvals, utility connections
  - `FIELD_DISPATCH`: Failed inspections, reinspections needed
  - `ENGINEERING`: Structural reviews, plan reviews
  - `PERMITTING`: Permit applications, status updates
  - `CUSTOMER_SERVICE`: General inquiries
- **Priority**: Low (passed, informational), Normal (standard action items), High (urgent keywords, failed with corrections)

## Development

Run tests:
```bash
pytest
```

With coverage:
```bash
pytest --cov=smartroute --cov-report=html
```

## License

MIT
