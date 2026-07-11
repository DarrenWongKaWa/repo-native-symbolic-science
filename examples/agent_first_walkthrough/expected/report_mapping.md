# Expected Report Mapping

This file shows the expected provenance-to-report mapping for the traceable LaTeX report.

---

## Report Mapping

### Generated Report: `generated/report.tex`

### Equation-to-Provenance Mapping

| Equation | Source Task | Artifact SHA | Verifier Verdict | Assumptions | Human Gate | Status |
|----------|-------------|--------------|------------------|-------------|------------|--------|
| Eq. 1: G(x,y,z,n) definition | INGEST-SYNTH-001 | raw_object.json | RAW_INGESTED | None | None | Raw |
| Eq. 2: F1(x,n) = (x+1)^n*exp(-x) | NORM-SYNTH-001 | normalized_parent.json | EXACT_RECONSTRUCTION_PASS | Commutative scalars | None | Normalized |
| Eq. 3: F2(x,n) = gamma(n+1,x) | NORM-SYNTH-001 | child_expressions.json | EXACT_RECONSTRUCTION_PASS | Commutative scalars | None | Normalized |
| Eq. 4: F3(y,z,n) = sin(pi*z)*H_n(y) | NORM-SYNTH-001 | child_expressions.json | EXACT_RECONSTRUCTION_PASS | Commutative scalars | None | Normalized |
| Eq. 5: gamma identity | TRANS-SYNTH-001 | candidate_transformation.json | EXACT_RECONSTRUCTION_PASS | n ∈ ℕ₀ | HUMAN-GATE-SYNTH-001 | Verified |
| Eq. 6: Simplified G(x,y,z,n) | TRANS-SYNTH-001 | candidate_transformation.json | EXACT_RECONSTRUCTION_PASS | x>0, y∈ℝ, z∈ℝ, n∈ℕ₀ | HUMAN-GATE-SYNTH-001 | Verified |
| Eq. 7: Hermite convention declaration | — | human_decision_record.json | — | — | HUMAN-GATE-SYNTH-001 | Accepted |
| Eq. 8: Numerical regression summary | VERIF-SYNTH-002-NUM | numerical_evidence.json | NUMERICAL_REGRESSION_PASS | 100 samples, tol 1e-12 | None | Supporting |

### Sections

#### Abstract
Synthetic walkthrough demonstrating symbolic simplification of `G(x,y,z,n) = (x+1)^n*exp(-x) + gamma(n+1,x) + sin(pi*z)*H_n(y)` using the Repo-Native Symbolic Science framework. The gamma identity and Hermite polynomial conventions are verified. Numerical regression provides supporting evidence.

#### 1. Raw Expression
- Original expression with SHA-256 provenance
- Symbol inventory and structure

#### 2. Scientific Definitions and Conventions
- Hermite polynomial: physicist's convention
- Incomplete gamma: lower incomplete gamma
- Domain declarations for all variables

#### 3. Decomposition
- Three independent child sectors
- Parent reconstruction confirmation

#### 4. Transformation
- Gamma identity substitution
- Result: `G(x,y,z,n) = exp(-x)*(n!*sum_{k=0}^n x^k/k! + (x+1)^n) + sin(pi*z)*H_n(y)`

#### 5. Verification
- Exact symbolic difference verification (PASS)
- Numerical regression testing (PASS, supporting only)

#### 6. Provenance
- Complete artifact tree with SHA hashes
- Human gate decisions recorded
- Canonical status: NOT CANONICAL (Blocker 5 active)

#### 7. Declarations
- AI disclosure statement
- Known limitations and caveats
- Human scientist authorizations

### Compilation

```
pdflatex generated/report.tex
```

Requires human authorization for compilation. The TeX source is traceable; the PDF is a convenience output.
