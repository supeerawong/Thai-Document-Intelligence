# Thai official letter schema

Schema ID: `thai_official_letter`  
Schema version: `1.0.0`

The schema represents an external letter, internal memorandum, order, announcement, or unknown official document. Fields include agency, document number, normalized date, subject, recipient, references, attachments, body, signers, contact, page count, and aggregate confidence.

Dates preserve `original`, normalize a valid value to ISO-8601, and identify the Buddhist or Gregorian calendar. Unknown fields are `null`; list fields are empty arrays. Every high-value field has an entry in the result-level `fields` map containing confidence and provenance.

Schema versions change when meaning or validation changes. Additive optional fields may be introduced in a minor version; removals or meaning changes require a major schema version.

