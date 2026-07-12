# Human Readability Review

## Audit Identification
- **Audit ID**: `{{ audit_id }}`
- **Supplement Request ID**: `{{ supplement_request_id }}`
- **Auditor Role**: `{{ auditor_role }}`
- **Audit Timestamp**: `{{ audit_timestamp }}`

## Overall Verdict

| Field | Value |
|-------|-------|
| **Readability Score** | `{{ readability_score }}` / 10 |
| **Publication Readiness** | `{{ publication_readiness }}` |
| **Critical Issues** | `{{ critical_issues_count }}` |
| **Major Issues** | `{{ major_issues_count }}` |
| **Minor Issues** | `{{ minor_issues_count }}` |

Publication readiness values: `READY`, `READY_WITH_MINOR_REVISIONS`, `REVISION_REQUIRED`, `NOT_READY`

## Blocking Issues
{{#each blocking_issues}}
- `{{ this }}`
{{/each}}

## Recommended Before Publication
{{#each recommended_before_publication}}
- `{{ this }}`
{{/each}}

## Detailed Checks (13 Check Types)

---

### 1. Equation Numbering Consistency
- **Verdict**: `{{ check_01_verdict }}`
- **Evidence**: `{{ check_01_evidence }}`
- **Location**: `{{ check_01_location }}`
- **Severity**: `{{ check_01_severity }}`
- **Recommendation**: `{{ check_01_recommendation }}`
- **Affected Equations**: `{{ check_01_affected_equations }}`

---

### 2. Cross-Reference Validity
- **Verdict**: `{{ check_02_verdict }}`
- **Evidence**: `{{ check_02_evidence }}`
- **Location**: `{{ check_02_location }}`
- **Severity**: `{{ check_02_severity }}`
- **Recommendation**: `{{ check_02_recommendation }}`
- **Affected Sections**: `{{ check_02_affected_sections }}`

---

### 3. Notation Defined Before Use
- **Verdict**: `{{ check_03_verdict }}`
- **Evidence**: `{{ check_03_evidence }}`
- **Location**: `{{ check_03_location }}`
- **Severity**: `{{ check_03_severity }}`
- **Recommendation**: `{{ check_03_recommendation }}`

**Undefined at First Use:**
{{#each check_03_undefined_symbols}}
- `{{ symbol }}` first used in `{{ location }}`, defined in `{{ definition_location }}`
{{/each}}

---

### 4. Index Convention Clarity
- **Verdict**: `{{ check_04_verdict }}`
- **Evidence**: `{{ check_04_evidence }}`
- **Location**: `{{ check_04_location }}`
- **Severity**: `{{ check_04_severity }}`
- **Recommendation**: `{{ check_04_recommendation }}`

---

### 5. Term Grouping Readability
- **Verdict**: `{{ check_05_verdict }}`
- **Evidence**: `{{ check_05_evidence }}`
- **Location**: `{{ check_05_location }}`
- **Severity**: `{{ check_05_severity }}`
- **Recommendation**: `{{ check_05_recommendation }}`
- **Affected Equations**: `{{ check_05_affected_equations }}`

---

### 6. Abbreviation Expansion Present
- **Verdict**: `{{ check_06_verdict }}`
- **Evidence**: `{{ check_06_evidence }}`
- **Location**: `{{ check_06_location }}`
- **Severity**: `{{ check_06_severity }}`
- **Recommendation**: `{{ check_06_recommendation }}`

**Unexpanded Abbreviations:**
{{#each check_06_unexpanded}}
- `{{ abbreviation }}` at `{{ location }}`
{{/each}}

---

### 7. Figure/Table Label Consistency
- **Verdict**: `{{ check_07_verdict }}`
- **Evidence**: `{{ check_07_evidence }}`
- **Location**: `{{ check_07_location }}`
- **Severity**: `{{ check_07_severity }}`
- **Recommendation**: `{{ check_07_recommendation }}`

---

### 8. Derivation Step Narrative Flow
- **Verdict**: `{{ check_08_verdict }}`
- **Evidence**: `{{ check_08_evidence }}`
- **Location**: `{{ check_08_location }}`
- **Severity**: `{{ check_08_severity }}`
- **Recommendation**: `{{ check_08_recommendation }}`

---

### 9. Physical Interpretation Accessibility
- **Verdict**: `{{ check_09_verdict }}`
- **Evidence**: `{{ check_09_evidence }}`
- **Location**: `{{ check_09_location }}`
- **Severity**: `{{ check_09_severity }}`
- **Recommendation**: `{{ check_09_recommendation }}`

---

### 10. Limiting Case Explicitness
- **Verdict**: `{{ check_10_verdict }}`
- **Evidence**: `{{ check_10_evidence }}`
- **Location**: `{{ check_10_location }}`
- **Severity**: `{{ check_10_severity }}`
- **Recommendation**: `{{ check_10_recommendation }}`

---

### 11. Mathematical Omission Transparency
- **Verdict**: `{{ check_11_verdict }}`
- **Evidence**: `{{ check_11_evidence }}`
- **Location**: `{{ check_11_location }}`
- **Severity**: `{{ check_11_severity }}`
- **Recommendation**: `{{ check_11_recommendation }}`

**Omissions without Reconstruction Rules:**
{{#each check_11_unreconstructible}}
- `{{ omission_id }}` for equation `{{ equation_label }}`
{{/each}}

---

### 12. Reproduction Instruction Completeness
- **Verdict**: `{{ check_12_verdict }}`
- **Evidence**: `{{ check_12_evidence }}`
- **Location**: `{{ check_12_location }}`
- **Severity**: `{{ check_12_severity }}`
- **Recommendation**: `{{ check_12_recommendation }}`

---

### 13. Reader Pathway Signposting
- **Verdict**: `{{ check_13_verdict }}`
- **Evidence**: `{{ check_13_evidence }}`
- **Location**: `{{ check_13_location }}`
- **Severity**: `{{ check_13_severity }}`
- **Recommendation**: `{{ check_13_recommendation }}`

---

## Reader Pathway Assessment

### physics_first
- **Accessibility Score**: `{{ physics_first_accessibility }}` / 10
- **Recommended Reading Time**: `{{ physics_first_reading_time }}` minutes
- **Prerequisite Clarity**: `{{ physics_first_prerequisite_clarity }}`

### derivation_checking
- **Accessibility Score**: `{{ derivation_checking_accessibility }}` / 10
- **Recommended Reading Time**: `{{ derivation_checking_reading_time }}` minutes
- **Step Completeness**: `{{ derivation_checking_step_completeness }}`

### machine_reproduction
- **Accessibility Score**: `{{ machine_reproduction_accessibility }}` / 10
- **Recommended Reading Time**: `{{ machine_reproduction_reading_time }}` minutes
- **Reproducibility Assessment**: `{{ machine_reproduction_reproducibility }}`

## Metadata
- **Previous Audit ID**: `{{ previous_audit_id }}`
- **Audit SHA-256**: `{{ audit_sha256 }}`
