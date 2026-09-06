name: Document Extraction Issue
description: Report an issue where a supplier quotation (PDF, Excel, CSV) was extracted inaccurately
labels: ["extraction", "data-quality"]
body:
  - type: markdown
    attributes:
      value: |
        **Note:** Please NEVER attach confidential, proprietary, or sensitive documents.
        Anonymize or synthesize your document before attaching.
  - type: dropdown
    id: format
    attributes:
      label: Document Format
      options:
        - "Native PDF (vector text)"
        - "Scanned PDF (raster image)"
        - "Excel (.xlsx, .xls)"
        - "CSV"
        - "Other"
    validations:
      required: true
  - type: textarea
    id: expected_vs_actual
    attributes:
      label: Expected vs. Actual Extraction
      description: What fields or line items were missed or extracted incorrectly?
      placeholder: |
        Expected: Unit price $45.00 for Line 2, Lead time 14 days
        Actual: Unit price parsed as $450.00, Lead time missed
    validations:
      required: true
  - type: textarea
    id: sample_snippet
    attributes:
      label: Anonymized Table or Text Snippet
      description: Provide an anonymized sample illustrating the layout.
