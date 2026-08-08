---
name: exsuwako-paper-writing
description: Draft, revise, and review ExSuwako cryptography papers with the 2024-339 rhetorical style for abstracts and introductions, the 2024-313 theorem-driven style for technical sections, consistent terminology, and evidence-bounded claims.
---

# ExSuwako Paper Writing

## Branch Scope

This workflow applies only on a curated venue branch that contains
`paper/writing_guide.md` and `paper/exp_todo.md`.  `main` intentionally omits
those manuscript-planning files; use it only for factual mathematical or
prior-art maintenance, then carry a confirmed correction to the appropriate
venue branch.

Use this skill when drafting or revising `paper/writing_guide.md`, a future
ExSuwako paper, its abstract or introduction, theorem and complexity sections,
or paper-facing terminology and claim wording.

Treat the following files as the local writing references:

- `paper/templates/2024-339.pdf`: rhetorical model for the abstract and
  introduction;
- `paper/templates/2024-313.pdf`: theorem-driven model for the technical body;
- `paper/writing_guide.md`: current ExSuwako outline, claim status, and
  submission gates;
- `paper/exp_todo.md`: sole authoritative experimental execution checklist;
- `README.md`: current notation, scope, and conservative research status.

Do not copy sentences, distinctive phrasing, or paper-specific claims from the
PDFs. Transfer their organization, tone, level of explanation, and transition
logic only.

## Workflow

1. Read the relevant section of `paper/writing_guide.md`, consult
   `paper/exp_todo.md` before writing an experimental claim, and inspect the
   actual PDF reference before drafting.
2. Build a short claim ledger. Mark each statement as proved, experimentally
   supported, planned, or unresolved.
3. Build a terminology ledger before changing prose. Choose one canonical term
   for each central object and preserve it throughout the paper.
4. Draft in the section-specific style below.
5. Check formulas, cross-references, terminology, and claim strength.
6. Run `git diff --check` and report any unverified claims or missing evidence.

## Three Writing Rules

### 1. Match the Two Reference Voices

Use a restrained, research-paper tone:

- State the problem before introducing notation.
- Explain why the limitation matters before presenting the construction.
- Use explicit transitions such as `We first`, `We then`, and `Finally` when
  they clarify dependency, but avoid rhetorical inflation.
- Separate established results, conjectural interpretation, and planned work.
- Prefer precise verbs such as `define`, `prove`, `derive`, `construct`,
  `measure`, and `compare`.
- Avoid claims such as `first`, `optimal`, `practical`, `constant-time`, or
  `significant speedup` unless the corresponding audit or experiment exists.

Use the 2024-339 style for accessibility: introduce the cryptographic or
computational pain point, identify the concrete loss in existing approaches,
state the proposed transformation, and explain its consequence in language a
cryptographer outside the subarea can follow.

Use the 2024-313 style for technical authority: define the algebraic objects,
fix assumptions and cost models, state lemmas and theorems, prove them in a
dependency-respecting order, and derive parameterized complexity bounds before
discussing examples.

### 2. Assign the Templates to the Right Sections

#### Abstract and Introduction: 2024-339 Rhetorical Template

Use this order:

1. Establish the role of finite-field arithmetic in cryptographic computation.
2. Isolate the reduction bottleneck for sparse characteristic-two moduli.
3. Explain that tap Hamming weight alone does not capture the sequential
   feedback-chain cost.
4. State the gap: conventional serial reduction preserves the chain, while
   dense reciprocal or matrix methods incur setup or representation costs.
5. Present ExSuwako as a sparse, matrix-free application of the reciprocal
   operator using Frobenius factors.
6. State the proved algebraic result and exact round parameter.
7. State implementation or benchmark results only when they exist.
8. End with a bounded statement of cryptographic relevance and limitations.

In the introduction, follow the abstract with motivation, the limitation of
existing paradigms, the research question, contributions, a high-level
technical overview, scope, and paper organization. Keep the first pages
readable without requiring the reader to know $U$, $V$, or $r$.

#### Technical Body: 2024-313 Theorem-Driven Template

Use this dependency order:

1. Preliminaries and notation.
2. Existing reduction paradigms and the fixed cost model.
3. Sparse feedback-operator formulation.
4. Structural lemmas, including nilpotence and Frobenius identities.
5. Generalized Suwako algorithm.
6. Correctness theorem and proof.
7. Work, depth, space, setup, and schedule-complexity analysis.
8. Concrete parameter regimes and limitations of the bounds.
9. Implementations and evaluation.
10. Prior-art boundary, discussion, and conclusion.

Do not present benchmark claims before defining what is counted. Do not bury
the main correctness argument inside implementation details. Put long routine
proofs, exhaustive-test methodology, and additional tables in appendices or
supplementary material.

### 3. Follow the Authoritative Paper Outline

Treat `paper/writing_guide.md` as the single source of truth for the final
paper structure. Do not duplicate or independently maintain the section
outline in this skill. Read the guide before drafting a new section, and update
the guide when the paper structure changes.

Preserve its high-level division:

- 339-style motivation in the abstract and introduction;
- 313-style definitions, theorems, proofs, and complexity analysis in the
  technical body;
- separate prior-art, implementation, evaluation, limitations, and appendix
  sections;
- submission gates maintained in the guide and experimental TODOs maintained
  only in `paper/exp_todo.md`.

## Terminology and Consistency

Create a terminology ledger before editing. Keep one term for each concept and
change it only when the abstraction level changes.

- Call the contribution `method` or `algorithm` unless the paper has a
  precisely defined scheme; use `framework` only for a broader analytical
  framework.
- Use `sparse modulus`, `sparse tap set`, and `feedback operator` consistently.
- Define `Delta_t = m - t` and `Delta_min` before using them.
- Define the exact round count
  $$r = \left\lceil \log_2(m/\Delta_{\min}) \right\rceil$$
  before using `r` in an algorithm or bound.
- Distinguish `feedback depth`, `parallel depth`, and `gate depth`.
- Distinguish `reduction cost`, `multiplication cost`, `setup cost`, and
  `amortized cost`.
- Use `ISA` for architecture-level claims. Use `platform`, `system`,
  `machine`, or board names for concrete evaluation hardware.
- Format identifiers literally when appropriate: `AVX2`, `PCLMULQDQ`, `VEC`,
  library names, parameter-set names, and modulus names.
- Do not silently turn `word work` into `instruction count` or `XOR count`
  into `gate count`.

## Claim Boundaries

Maintain four evidence levels:

- **Proved:** follows from a stated theorem under stated assumptions.
- **Measured:** supported by a reproducible implementation and experiment.
- **Suggested:** an interpretation that needs broader evidence.
- **Open:** a TODO, conjecture, or unresolved prior-art question.

Apply these rules:

- Keep novelty conditional until the prior-art audit is complete.
- Do not claim an asymptotic improvement to complete field multiplication when
  only the reduction term improves.
- Report the exact ceiling for `r`; use
  $\Theta(1 + \log(m/\Delta_{\min}))$ for asymptotic prose.
- State when results depend on fixed public moduli, generated schedules, word
  size, SIMD width, memory traffic, or setup amortization.
- Describe exhaustive tests as correctness evidence, not as a proof of
  novelty, optimality, or practical superiority.
- Preserve limitations: no automatic constant-time claim, no lower-bound claim,
  no optimality claim, and no application claim without evidence.

## Review Checklist

Before finalizing a section, check:

- Does the abstract state a problem, a method, a proved result, and an impact
  claim at matching evidence levels?
- Does the introduction explain why the problem matters before introducing
  the operator notation?
- Is every symbol defined before use, especially `m`, `T`, `Delta_t`,
  `Delta_min`, `U`, `V`, `H`, `L`, and `r`?
- Does each theorem have assumptions, a precise statement, and a proof path?
- Are synchronous updates explicit in the algorithm?
- Are reduction-only and end-to-end measurements separated?
- Are the strongest relevant baselines and prior-art families addressed?
- Are `scheme/framework`, `ISA/platform/system`, and cost-model terms used
  consistently?
- Are unsupported claims marked as TODO instead of being polished into facts?
- Does the prose remain concise, formal, and readable to a cryptographer who is
  not an expert in sparse finite-field reduction?

After editing, run `git diff --check`. For Markdown, also check math delimiters
and code fences. For LaTeX, compile only when the user requests a build or when
the edit affects syntax or layout.
