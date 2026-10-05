# HW5 final package

Student: Vedant Vartak; SID4: 3539.

Repository: https://github.com/vedantvartakwork/data260-3539

Submission ref: `hw5`. Resolve its final commit with
`git rev-parse 'hw5^{commit}'`, or inspect the GitHub `hw5` tag. The PDF cover's
`fcf24af64451a922c46316925edd387ce09a5101` is the earlier application baseline;
the final selected-PDF packaging commit necessarily follows that baseline.
No application source was changed during this packaging update.

The exact selected 48-page PDF is stored identically at:

- `reports/hw05/report.pdf`
- `output/pdf/Vartak_HW5.pdf`

SHA-256 for both:
`d80ec37e2fa520c02229d347d7f3441941b8e2a5c4b94986dafec2ce81b42cd8`.

## Checks recorded on 2026-10-05

- Live verification: 14/14; including backend health and both actual STDIO
  MCP tool calls. The verifier records the source commit and tag that were
  actually tested; the subsequent commit saves that output and selected PDF.
- Python test suite: 37/37; offline assert runner: 9/9.
- React production build: successful.
- Authenticated MySQL/API CRUD and relationship integration: 14/14,
  including deletion protection and cleanup of temporary fixtures.
- Package audit: 8/8; checks required paths, exact selected PDF, all 150 seeded
  failure sequences and CSV/metrics alignment, all four MealDB and six domain
  captures, and four saved agent scenario summaries against the JSONL log.
- Application code is in shared root-level `code/` and `mcp_servers/`;
  evidence, metrics, logs, contracts, and reflection are in `reports/hw05/`.

The report's experiment and Inspector records remain the original recorded
runs, not newly generated random results. The new API integration record is a
separate recheck and is not presented as the source of the older screenshots.

## External items not completed by a Git push

GitHub's collaborator API confirmed `supriyaselvanganesan` has write access.
`Sbnikitha` has a pending write invitation, not accepted collaborator access.
The invitee must accept it. The PDF must still be uploaded to the course portal
if that is required; this package upload does not perform a Canvas submission.
