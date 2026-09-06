name: Bug report
description: Create a report to help us improve ProcureFlow OSS
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: Thanks for taking the time to report an issue!
  - type: textarea
    id: description
    attributes:
      label: Bug Description
      description: A clear and concise description of what the bug is.
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: What steps led to the issue?
      placeholder: |
        1. Create RFQ '...'
        2. Upload file '...'
        3. See error
    validations:
      required: true
  - type: input
    id: environment
    attributes:
      label: Environment & Version
      placeholder: "e.g. Docker Compose, Python 3.12, Windows 11, commit abc1234"
    validations:
      required: true
