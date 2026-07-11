# Generic Raw Expression Ingestion

## Purpose
Freeze raw bytes and their SHA-256 fingerprint, audit the expression structure, and create a held (non-transformed, non-simplified) representation. This skill captures the source-of-truth for a raw expression BEFORE any transformation occurs. It must never transform, simplify, reduce, rewrite, or otherwise alter the expression — its sole output is a faithful, audited, frozen representation labelled `RAW_INGESTED`.

## Activation Conditions
This skill MUST be activated when:
- The routing skill emits `routing_target: "generic_raw_expression_ingestion"` with `task_class: "ingestion"`.
- A new raw expression file (`.m`, `.wl`, `.txt`, `.tex`, or adapter-specified format) is provided.
- A human explicitly requests "ingest this expression" or "freeze this raw input."
- An adapter signals that a new source file must be registered in the provenance system.
- A previously ingested expression must be re-ingested with corrected metadata (append/reingest).

This skill MUST NOT be activated for:
- Expressions that have already been transformed (use `candidate_symbolic_transformation`).
- Expressions that need normalization (use `generic_expression_normalization_and_decomposition`).
- Expressions presented for verification (use `exact_and_bounded_symbolic_verification`).

## Required Inputs
1. **Source file path** (mandatory): Absolute path to the raw expression file to be ingested.
2. **Routing decision** (mandatory): The `routing_decision.json` that authorized this ingestion.
3. **Source metadata** (mandatory when available):
   - `source_origin`: Where the expression came from (paper, derivation, human-written, generated).
   - `source_authority`: The authoritative reference (DOI, arXiv ID, internal doc ID).
   - `source_date`: When the source was created or last modified.
   - `source_format`: The file format / language dialect (e.g., `wolfram_mathematica_13`, `latex_math`, `python_sympy_1`).
4. **Adapter configuration** (optional but recommended):
   - Convention maps for indices, symbols, summation conventions.
   - Known assumptions about the expression domain.
   - Sector definitions for tagging sub-expressions.
   - Allowed and forbidden transformations that will be inherited by downstream tasks.
   - Regression targets that must be preserved.

## Required Output Directory
```
skills/generic_raw_expression_ingestion/output/
```
Within this directory, a subdirectory named `{raw_object_id}/` contains all artifacts for this ingestion, where `{raw_object_id}` is the SHA-256 of the source file.

## Required Output Artifacts

### 1. generic_raw_object.json (always produced)
Schema:
```json
{
  "raw_object_id": "string (SHA-256 of source file)",
  "status": "RAW_INGESTED",
  "source_file_path": "string",
  "source_file_sha256": "string",
  "source_metadata": {
    "origin": "string",
    "authority": "string",
    "date": "string (ISO 8601)",
    "format": "string"
  },
  "expression_inventory": {
    "free_symbols": ["string"],
    "indexed_symbols": [
      {
        "symbol_name": "string",
        "index_structure": "string (e.g. '_{a}^{bc}')",
        "free_indices": ["string"],
        "dummy_indices": ["string"],
        "external_indices": ["string"],
        "index_domain": "string (e.g. 'latin_lowercase', 'greek_lowercase', 'spacetime')",
        "index_range": "string (e.g. '0..3', '1..n', '1..D')"
      }
    ],
    "dummy_indices_global": ["string"],
    "external_indices_global": ["string"],
    "summation_convention": "string (e.g. 'einstein_explicit', 'einstein_implicit', 'none')",
    "operator_commutativity": {
      "multiplication": "commutative | noncommutative | mixed",
      "addition": "commutative | noncommutative",
      "function_application": "commutative | noncommutative | not_applicable"
    }
  },
  "assumptions": {
    "domain": "string (e.g. 'real', 'complex', 'symbolic')",
    "known_symmetries": ["string"],
    "known_identities": ["string (references to identity UUIDs)"],
    "branch_sensitive_functions": ["string"],
    "parity_constraints": "string | null"
  },
  "transformation_constraints": {
    "allowed_transformations": ["string (level A-G or specific rule names)"],
    "forbidden_transformations": ["string (level A-G or specific rule names)"],
    "regression_targets": [
      {
        "target_id": "string",
        "description": "string",
        "reference_expression_sha": "string"
      }
    ]
  },
  "adapter_metadata": {
    "adapter_name": "string | null",
    "adapter_version": "string | null",
    "adapter_provided_conventions": {},
    "adapter_provided_constraints": {}
  },
  "ingestion_timestamp": "string (ISO 8601)",
  "ingestion_agent": "string",
  "audit": {
    "expression_length_bytes": "integer",
    "term_count_estimate": "integer",
    "max_nesting_depth": "integer",
    "unrecognized_constructs": ["string"],
    "parse_warnings": ["string"]
  }
}
```

### 2. frozen_source_copy (always produced)
A byte-for-byte copy of the source file stored at `{raw_object_id}/frozen_source.{ext}`, where `{ext}` matches the source format.

### 3. ingestion_audit_report.md (always produced)
Human-readable Markdown report summarizing:
- The expression inventory (free symbols, indexed symbols, dummy indices, external indices).
- Index domains and summation conventions.
- Detected assumptions and symmetries.
- Adapter-provided metadata (if any).
- Transformation constraints (allowed, forbidden, regression targets).
- Any parse warnings or unrecognized constructs.
- Explicit statement that the expression has NOT been transformed or simplified.

### 4. adapter_analysis.json (conditional)
Produced ONLY if an adapter was provided. Records:
- How adapter conventions were applied to the inventory.
- Any discrepancies between adapter expectations and actual expression structure.
- Adapter-identified sector boundaries within the expression.

### 5. incomplete_inventory_flags.json (conditional)
Produced ONLY if the inventory could not be fully populated. Lists:
- Symbols whose index structure could not be determined.
- Index domains that are ambiguous.
- Assumptions that are plausibly needed but not provided.
- A severity level for each gap (WARNING vs BLOCKER).

## Allowed Operations
- Read the source file byte-for-byte.
- Compute SHA-256 of the source file.
- Copy the source file as a frozen artifact.
- Parse the expression syntactically (NOT semantically) to inventory symbols, indices, and structure.
- Detect and classify free symbols, indexed symbols, dummy indices, and external indices.
- Detect summation conventions from explicit sum notation or adapter metadata.
- Detect operator commutativity from structural patterns or adapter metadata.
- Record known symmetries from adapter or explicit annotation in the source.
- Identify branch-sensitive functions (e.g., `Abs`, `Sign`, `Arg`, `Sqrt`, `Log`) that require care in transformations.
- Record transformation constraints from the adapter.
- Flag unrecognized syntactic constructs as warnings.
- Set initial status to `RAW_INGESTED`.
- Label the ingestion with a timestamp and agent identifier.
- Compute basic audit statistics (byte length, term count estimate, max nesting depth).

## Forbidden Operations
- **Any form of transformation, simplification, reduction, or rewriting** of the expression.
- Expanding products, contracting indices, or applying any algebraic identity.
- Substituting one symbol for another.
- Normalizing coefficient ordering or term ordering.
- Canonicalizing dummy indices.
- Applying integration-by-parts or differential identities.
- Setting any status other than `RAW_INGESTED` (never `CANONICAL`, `VERIFIED`, `INTEGRATED`, or `CANDIDATE_TRANSFORMED`).
- Guessing missing semantics (e.g., assuming `g_{ab}` is a metric tensor because of the letter `g`).
- Inferring index domains from symbol names alone.
- Adding assumptions that are not explicitly stated in the source or adapter.
- Resolving parse warnings by silently correcting the source.
- Overwriting a previously ingested raw object with the same `raw_object_id` without creating a new ingestion event (append/reingest).

## Semantic Blockers
The following conditions MUST block ingestion completion and require human escalation via `human_scientist_semantic_escalation`:
1. **Unreadable source file**: The file cannot be opened, is empty, or contains only whitespace/non-printable characters.
2. **Unrecognized format**: The source format is not in the list of supported formats and no adapter can handle it.
3. **Unparseable expression**: The expression cannot be parsed into a syntactic tree by any available parser.
4. **Missing index domains**: Indexed symbols are detected but no index domain or range information is available (from source or adapter).
5. **Ambiguous summation convention**: Summation over repeated indices is ambiguous (some indices appear to be summed, others not) and no adapter resolves it.
6. **Conflicting adapter**: The adapter's expectations contradict the actual expression structure in a way that cannot be resolved automatically.
7. **Missing transformation constraints**: The adapter did not provide `allowed_transformations` and `forbidden_transformations`, and no repo-level defaults exist.
8. **SHA collision**: A raw object with the same `raw_object_id` already exists and the human has not explicitly authorized a re-ingest.

## Task Lifecycle
1. **RECEIVE**: Accept the routing decision and source file path.
2. **VALIDATE_INPUTS**: Verify the source file exists, is readable, and has a recognized format.
3. **FREEZE**: Copy the source file byte-for-byte into the output directory. Compute and record SHA-256.
4. **PARSE**: Parse the expression syntactically into a tree. Record parse warnings (do NOT correct).
5. **INVENTORY**: Walk the parse tree and identify: free symbols, indexed symbols, dummy indices, external indices, index domains, summation conventions, operator commutativity.
6. **AUGMENT_WITH_ADAPTER**: If an adapter is provided, apply its conventions to fill gaps in the inventory. Flag discrepancies.
7. **RECORD_ASSUMPTIONS**: Extract explicit assumptions from the source (e.g., `Assuming[...]`) and from the adapter.
8. **RECORD_CONSTRAINTS**: Record `allowed_transformations`, `forbidden_transformations`, and `regression_targets`.
9. **AUDIT**: Compute basic statistics. Identify unrecognized constructs. Flag semantic gaps (missing index domains, etc.).
10. **DECIDE**: If semantic blockers exist → escalate to `human_scientist_semantic_escalation`. Otherwise → write output artifacts.
11. **WRITE**: Produce `generic_raw_object.json`, `frozen_source_copy`, `ingestion_audit_report.md`, and conditional artifacts.
12. **SET_STATUS**: Set `status: "RAW_INGESTED"` in `generic_raw_object.json`.
13. **LOG**: Append to the repo-level ingestion registry.

## Relation / Claim Types
This skill produces exactly ONE status claim:
- `RAW_INGESTED`: The expression has been frozen, inventoried, and is held without transformation. This status is prerequisite for ALL downstream tasks.

This skill does NOT produce any of the following claims:
- `CANDIDATE_TRANSFORMED` (that requires `candidate_symbolic_transformation`)
- `VERIFIED` (that requires `exact_and_bounded_symbolic_verification`)
- `CANONICAL` (that requires `provenance_claim_and_canonical_state`)
- Any `claim_relation` (that requires verification)

## Artifact Contract
- `generic_raw_object.json` MUST be valid JSON conforming to the schema above.
- `generic_raw_object.json` MUST have `status` field EXACTLY equal to `"RAW_INGESTED"`.
- `generic_raw_object.json` MUST contain a `raw_object_id` that matches the SHA-256 of `frozen_source_copy` byte-for-byte.
- `frozen_source_copy` MUST be byte-for-byte identical to the original source file.
- `ingestion_audit_report.md` MUST explicitly state "This expression has NOT been simplified, transformed, or verified."
- No output artifact may contain a derived, transformed, or simplified version of the expression.
- The `adapter_metadata` section MUST be `null` or empty if no adapter was provided (never an empty object with no provenance).
- All timestamps MUST be ISO 8601 format in UTC.

## Downstream Eligibility
An ingested raw expression is eligible for downstream processing ONLY if:
1. `generic_raw_object.json` exists and passes schema validation.
2. `status` is `"RAW_INGESTED"`.
3. `frozen_source_copy` exists and its SHA-256 matches `raw_object_id`.
4. No semantic blockers remain unresolved (all escalated gaps have been addressed by the human).
5. `transformation_constraints.allowed_transformations` is non-empty (the downstream skill knows what it may do).
6. The raw object has not been superseded by a later re-ingestion.

## Human Escalation Behavior
- When a semantic blocker is encountered, ingestion is PAUSED (not aborted). The system emits a structured escalation using `human_scientist_semantic_escalation`.
- The escalation MUST specify: which raw object is blocked, which semantic gap was detected, why it blocks ingestion, what the human should provide, and what partial work has been completed.
- The human may respond with: corrected metadata, an updated adapter, a revised source file, a declaration that the gap is irrelevant, or a cancellation.
- If the human provides corrected metadata, the ingestion task is re-run from the AUGMENT_WITH_ADAPTER step using the augmented context.
- If the human provides a revised source file, the entire ingestion is re-run from FREEZE.
- If the human declares the gap irrelevant, the gap is recorded as `HUMAN_WAIVED` with the human's rationale in `incomplete_inventory_flags.json`, and ingestion proceeds.
- If the human cancels, the partial work (frozen copy, partial inventory) is retained for audit but marked as `INGESTION_ABORTED`, and no downstream task may use it.

## Interaction with Other Skills
- **Receives from**: `scientific_symbolic_repo_entry` (routing decision).
- **Escalates to**: `human_scientist_semantic_escalation` (when semantic gaps are found).
- **Feeds into**: `generic_expression_normalization_and_decomposition` (the raw object is the input for normalization).
- **Feeds into**: `candidate_symbolic_transformation` (the raw object provides transformation constraints).
- **Referenced by**: `provenance_claim_and_canonical_state` (the raw object is the root of the provenance tree).
- **Referenced by**: `verified_provenance_to_latex_pdf` (the raw object is cited in the provenance manifest).

## Error Handling
- **File not found**: Halt, log error, escalate to human with "source file not found at path X".
- **Unsupported format**: Halt, log error, request format specification from human.
- **Parse failure with partial tree**: Record what was parsable, flag unparsed segments, escalate if the unparsed segments are structurally significant.
- **SHA mismatch after freeze**: Halt — this indicates a file-system integrity issue. Do not proceed.
- **Adapter not found**: Proceed without adapter metadata, but record `adapter_metadata: null` and flag any gaps that the adapter would have filled.
- **Empty expression**: Record a valid raw object with expression_length_bytes = 0 and term_count_estimate = 0. This is valid but will likely block downstream tasks.
