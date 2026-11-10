# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems.

Use GitHub's private reporting instead: **Security → Report a vulnerability** on this repository. You'll get a reply within a week.

## Scope

cse-mcp is read-only. It only sends requests to `https://www.cse.lk/api/`, and it stores no credentials or user data. The things that matter most:

- anything that makes the server contact a host other than cse.lk
- tool output that could carry prompt-injection content to the AI in a misleading way
- problems in the release pipeline (PyPI, the `.mcpb` bundle, the MCP Registry entry)

Only the latest release gets security fixes.
