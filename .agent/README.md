# Agent Governance Directory (`.agent/`)

## Architectural Role & Scope
This directory defines the autonomous governance directives, operational principles, squad assignments, and boundary guardrails for each agent in the multi-agent video post-production fleet.

## Itemized File Breakdown
- [`agy1.md`](agy1.md): Master directive and strategic roadmap for the Lead Orchestrator (`agy1`), defining fleet dispatch, dependency ordering, and final release criteria.
- [`agy11.md`](agy11.md): Dedicated operational directive and technical principles for the Tool Development & Visual Extraction Squad (`agy11`), establishing standards for visual fidelity, MCP schema compliance, and asynchronous idle notification.
- [`agy51.md`](agy51.md): Operational directive for the Audio, Narration & Editing Collective (`agy51`).
- [`agy100.md`](agy100.md): Operational directive for the Quality Control & Gatekeeper agent (`agy100`).

## Governance & Precedence
Directives defined in `./.agent/agy[x].md` hold absolute priority over default recommendations. Operational agents must maintain these directives and align implementations strictly with the scopes established in [`agent_assignments.json`](../agent_assignments.json).
