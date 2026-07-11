# Troubleshooting

Common issues and their resolutions when using the Repo-Native Symbolic Science framework through an agent.

---

## Missing Scientific Definitions

**Symptom**: Agent stops with `human_information_request.md` listing undefined symbols.

**Cause**: The raw expression contains symbols, indices, operators, or functions that have not been declared by the human scientist.

**Resolution**:
1. Read the `human_information_request.md` file — it lists exactly what is missing
2. Provide authoritative definitions for each listed entity
3. The agent will record the decisions and resume

**Prevention**: Provide definitions for all symbols when submitting the raw expression. See `HUMAN_SCIENTIST_GUIDE.md` for the complete list of information to provide.

---

## Unsupported Backend Capability

**Symptom**: Agent returns `UNSUPPORTED_CAPABILITY` or reports that no backend can satisfy the request.

**Cause**: The requested computation requires a capability (e.g., exact symbolic integration of a special function, a proprietary algorithm) that no available backend provides.

**Resolution**:
1. Check if the capability can be decomposed into simpler operations
2. Consider whether numerical approximation is acceptable (with appropriate caveats)
3. If Mathematica is available and provides the capability, request Mathematica as the backend
4. If no backend provides the capability, the computation cannot proceed — reformulate the scientific question

**The framework will not silently substitute a different operation type.**

---

## Mathematica Unavailable

**Symptom**: Agent reports `ENGINE_UNAVAILABLE` when Mathematica is requested or needed.

**Cause**: Mathematica is an optional commercial backend. It is not required for the core workflow.

**Resolution**:
1. The framework operates fully with SymPy for exact symbolic computation and NumPy/SciPy/mpmath for numerical support
2. If Mathematica-specific capabilities (e.g., `Series`, `Simplify_with_TimeConstrained`) are essential:
   - Install Mathematica on the system and ensure `wolframscript` is on the PATH
   - Or reformulate the request to use SymPy equivalents (`sympy.series`, `sympy.simplify`)
3. For mixed workflows, use SymPy as primary with numerical support from Python

**The framework is designed for open-source operation; Mathematica is optional.**

---

## Dependency Missing

**Symptom**: Agent reports import errors, `ModuleNotFoundError`, or `runner_not_found`.

**Cause**: Required Python packages are not installed.

**Resolution**:
1. The agent will request authorization before installing dependencies
2. Authorize the installation:

```bash
python3 -m pip install sympy numpy scipy mpmath jsonschema
```

3. The agent resumes after dependencies are installed

**Required packages**: `sympy`, `numpy`, `scipy`, `mpmath`, `jsonschema`.
**Optional**: Mathematica (proprietary, not installable via pip).

---

## Timeout

**Symptom**: Agent reports `TIMEOUT` with partial results.

**Cause**: The computation exceeded the declared time limit.

**Resolution**:
1. The framework does NOT promote partial results — anything marked TIMEOUT is incomplete
2. Retry with:
   - A longer timeout
   - A simpler sub-expression
   - A different backend
   - Decomposed into smaller computation units
3. Examine the execution truth record for warnings about complexity

**Never treat a timeout partial result as verified.**

---

## Branch-Sensitive Expression

**Symptom**: Agent flags an expression as branch-sensitive and requires explicit assumptions.

**Cause**: The expression contains branch-sensitive functions (`sqrt`, `log`, `arcsin`, fractional powers) whose simplification depends on branch choices.

**Example**: `sqrt(x^2)` simplifies to `|x|` for real x, but to `x` if x ≥ 0 is assumed.

**Resolution**:
1. Declare the domain for branch-sensitive variables:
   - `x > 0` → principal branch
   - `x ∈ ℝ` → real-valued branch with absolute value
   - `x ∈ ℂ` → principal branch with standard cuts
2. Record the branch convention in the scientific adapter
3. Re-run the computation

**The framework will not silently choose a branch.**

---

## Noncommutative Ordering

**Symptom**: Agent reports `POLICY_VIOLATION` or `ORDER_PRESERVATION_FAIL` when working with noncommutative objects.

**Cause**: The expression contains noncommutative operators (matrices, quantum operators, differential operators) and a commutative reordering was attempted or detected.

**Resolution**:
1. Verify that all noncommutative operators are declared in the `commutativity_metadata`
2. Check that no transformation implicitly reorders noncommutative products
3. If a reordering was attempted but rejected — this is correct behavior; the order is preserved
4. If a reordering is scientifically justified, authorize it explicitly as an allowed operation

**The framework preserves noncommutative ordering by default.**

---

## Translation Loss

**Symptom**: Agent reports `translation_loss_detected` when moving between backends.

**Cause**: The expression contains constructs that do not translate cleanly between engine languages (e.g., SymPy `Piecewise` → Mathematica `Piecewise` needs manual adjustment).

**Resolution**:
1. The translation loss is recorded explicitly
2. The agent will mark `exact_cross_engine_verification_eligible` as `false`
3. If cross-engine verification is essential:
   - Manually verify the translation mapping
   - Use the same expression language for all backends
   - Record the loss as a documented caveat

**Translation loss does not invalidate results; it restricts which claims can be made.**

---

## Incomplete Execution Truth

**Symptom**: Verification reports `missing_execution_truth_field`.

**Cause**: The execution truth record is missing one or more of the 22 required fields.

**Resolution**:
1. This is a framework execution issue — the agent should automatically fill missing fields
2. If it persists, request the agent to re-run the computation and capture complete execution truth
3. Check that the `bounded_computation_backend_execution` skill is correctly configured

**Incomplete execution truth cannot support a verification claim.**

---

## Human Gate Required

**Symptom**: Agent stops and displays a blocking message requesting human authorization.

**Cause**: The operation requires explicit human authorization (IBP, canonical promotion, limit reordering, etc.) and no authorization has been provided.

**Resolution**:
1. Read the blocking message — it specifies exactly what authorization is needed
2. Provide the authorization explicitly in natural language:
   > I authorize integration by parts for the expression F under the declared boundary conditions. I acknowledge that this authorization does not include canonical promotion.
3. The agent records the decision and proceeds

**The framework will not proceed past a human gate without explicit authorization.** Common gates:

| Operation | Required Authorization |
|-----------|----------------------|
| Integration by parts (IBP) | Explicit per-case authorization |
| Boundary term discard | Boundary conditions + authorization |
| Canonical promotion | Explicit canonization statement |
| Limit reordering | Non-commuting limit justification |
| Blocker 5 lift | Explicit acknowledgement |
| Mathematica license check | License confirmation |

---

## General Troubleshooting Checklist

1. **Dependencies installed?** `python3 -m pip list | grep -E "sympy|numpy|scipy|mpmath|jsonschema"`
2. **Engine fixtures pass?** `python3 tests/engine_fixtures/run_fixture_suite.py`
3. **Reuse fixtures pass?** `python3 scripts/run_reuse_fixture_suite.py`
4. **Skills discoverable?** Check `skills/*/SKILL.md` exists and is readable
5. **JSON schemas valid?** Validate schemas against JSON Schema draft-07
6. **Agent can read REPO_POLICY.md?** File must be readable in the repository root
7. **No private content leak?** The public repo should not contain `sigma_xxx` or `sigma_abc` scientific content (framework references are allowed)
8. **Absolute paths?** No file in the public repo should contain absolute filesystem paths

---

## When to Escalate

Escalate to the human scientist when:
- A scientific definition is genuinely unknown (not just unrecorded)
- Two verified results contradict each other
- A backend produces unexpected behavior that cannot be explained
- The framework's safety mechanisms prevent a scientifically justified operation
- A new type of assumption or symmetry requires a new scientific adapter rule

When escalating, the agent should provide:
1. The exact blocking condition
2. All evidence gathered so far
3. The specific decision needed from the human
4. The implications of each possible decision
