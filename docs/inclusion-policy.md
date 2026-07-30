# Inclusion policy

## Classification

Every considered main-track paper receives exactly one relevance class:

- `CORE_SYSTEMS`
- `SYSTEMS_ADJACENT`
- `EXCLUDED`
- `NEEDS_HUMAN_REVIEW`

The relevance score ranges from 0 to 5 and measures fit to this corpus only. It
must never be described or displayed as a quality, impact, advisor, or prestige
score.

Every decision records:

- a one-sentence inclusion or exclusion rationale;
- one or more relevant system layers when applicable;
- confidence;
- source evidence; and
- the classifier's workflow status.

## Core systems

Use `CORE_SYSTEMS` when the primary contribution is in one or more of:

- operating systems, kernels, or kernel verification;
- distributed systems, databases, transactions, storage, or file systems;
- networking and networked systems;
- cloud, serverless, datacenter, virtualization, containers, or isolation;
- resource management and scheduling;
- architecture or hardware/software co-design;
- systems-oriented compilers, runtimes, or language mechanisms;
- systems verification;
- reliability, testing, debugging, observability, or performance diagnosis;
- mobile, edge, embedded, or IoT systems;
- ML systems or high-performance computing;
- energy-efficient and sustainable systems;
- privacy-preserving systems; or
- systems security.

## Systems-adjacent

Use `SYSTEMS_ADJACENT` when the work is useful to a systems applicant but its
primary contribution is closer to program analysis, formal methods, software or
hardware security, trusted execution, fuzzing, vulnerability discovery, network
security, privacy infrastructure, cyber-physical infrastructure, or applied ML
with a material systems artifact.

## Usually excluded

Security-venue membership alone is not enough. Usually use `EXCLUDED` for:

- pure cryptographic primitive or protocol design;
- purely theoretical security;
- social-science, perception, phishing, misinformation, moderation, or policy
  work without a systems contribution;
- pure ML attacks or defenses without a systems artifact; and
- biometric classification without a systems contribution.

At ASPLOS, exclude a new ML algorithm that has no architecture, compiler,
runtime, or systems contribution.

## Human review

Use `NEEDS_HUMAN_REVIEW` when:

- the paper type is unclear;
- only a title or incomplete program entry is available;
- the systems artifact cannot be established from available sources;
- two plausible classifications remain after reading the paper; or
- the source evidence conflicts.

Do not resolve uncertainty by guessing. Explain it in `relevance.json` and add a
review issue.

## Required reading before summary

When a full paper is available, the summary writer records reading coverage for:

- abstract;
- introduction;
- conclusion;
- system overview or design; and
- evaluation overview.

A title-and-abstract-only summary cannot pass release validation when the full
paper is available.

## Excluded records

Keep a minimal canonical record for excluded main-track papers so coverage
counts remain auditable. An excluded record needs metadata, relevance rationale,
sources, and review state; it does not require a story summary or PI resolution.
