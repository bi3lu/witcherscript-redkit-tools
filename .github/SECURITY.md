# Security Policy

## Supported Versions

Security updates are handled for the latest released version of WitcherScript
REDkit Tools.

## Reporting a Vulnerability

Please do not open public issues for security-sensitive reports.

Report vulnerabilities by opening a private GitHub security advisory for the
repository, or contact the maintainer privately if advisory access is not
available.

Include:

- affected version or commit
- operating system
- reproduction steps
- expected impact
- any relevant logs or sample files

## Scope

This project runs local tooling, reads local project files, starts local language
server processes, and can invoke configured REDkit/game commands. Reports around
unsafe command execution, path handling, arbitrary file writes, dependency
supply-chain issues, or extension startup behavior are in scope.

Issues in The Witcher 3, REDkit, VS Code, Python, .NET, Node.js, or third-party
extensions should be reported to their respective maintainers.
