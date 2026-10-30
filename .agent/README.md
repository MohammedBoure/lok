# Agent Governance Directory (`.agent/`)

## Architectural Overview: Linguistic Recommendation as Single Source of Truth (SSOT)
This directory defines the autonomous governance directives, operational principles, squad assignments, and boundary guardrails for each agent in the multi-agent video post-production fleet.

The fleet is structured around the architectural principle of **Linguistic Recommendation as Single Source of Truth (SSOT)**:
1. **User Linguistic Prompt:** Dictates 100% of facts, commercial messaging, dialect, and call-to-action.
2. **Visual Keyframes:** Act strictly as a Chronological Pacing Clock to determine scene boundaries and synchronization timestamps.
3. **Deterministic Assembly:** Compiles the structured Edit Decision List (EDL) through a robust 2-stage FFmpeg pipeline with sidechain audio ducking and synchronized kinetic typography.

## Squad Directives & Agent Roles
- [`agy1.md`](agy1.md): Master directive and strategic roadmap for the Lead Orchestrator (`agy1`), defining fleet dispatch, dependency ordering, and final release criteria.
- [`agy11.md`](agy11.md): Ingestion, Ambiguity & Linguistic Disentanglement Agent (`agy11` / `worker-1`). Disentangles directives from narrative content, probes and transcribes source audio, enforces `clarification_mode`, and applies phonetic dialect normalization.
- [`agy51.md`](agy51.md): Editorial & Timeline Director (`agy51` / `worker-2`). The SSOT editorial engine. Aligns narrative beats with scene cut boundaries and produces the human-readable Edit Decision List (EDL).
- [`agy100.md`](agy100.md): Audio Post-Production & FFmpeg Assembly Gatekeeper (`agy100` / `worker-3`). Executes TTS generation, sidechain audio ducking, deterministic 2-stage FFmpeg rendering, and pragmatic pipeline verification.

## Governance & Operational Invariants
- Directives defined in `./.agent/agy[x].md` hold absolute priority over default recommendations.
- All Git commits must be authored and committed under `MouhammedBoure <mohamadbormoz2@gmail.com>`.
- Typography Invariant: Strictly 0 occurrences of character U+0669 (`\u0669`) across all files, tests, documentation, and commits.
