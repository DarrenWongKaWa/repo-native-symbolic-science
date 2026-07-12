# Full Profile Instructions

The full profile replays permitted symbolic scientific fixtures. It requires Wolfram kernel.

## Requirements

- Wolfram kernel (wolfram, wolframscript, or math) on PATH
- SymPy (optional, for cross-engine verification)
- The export-safe Wolfram Language (.wl) files in the `active/` directory

## What the Full Profile Tests

1. **12x12 exact linear solve** — Cross-engine verification of the repaired coupled solve using SymPy (exact), NumPy (numerical), and Wolfram (exact)
2. **All-zero identities** — The repaired pair IBP residual and seven-kernel reconstruction residual are verified across engines
3. **Repaired four-kernel formula** — Structural validation of the reduced formula with 20 components and 4 surviving kernels
4. **General closed form** — Sanity checks on the human-readable repaired formula
5. **Rice-Mele projection** — Demonstration that projected agreement does not imply general equality

## How to Run

```bash
python benchmarks/sigma_xxx_finite_gamma_replay/repair_lineage/scripts/run_benchmark.py --profile full
```

## Expected Behavior When Wolfram Is Unavailable

```
SKIP: Wolfram kernel not found on PATH. Full profile requires Wolfram.
```

The fast and standard profiles are always available. The full profile fails closed:
- If Wolfram is unavailable → WOLFRAM_UNAVAILABLE_SKIP (no false passes)
- If Wolfram script produces errors → FAIL logged with error detail
- All paths are relative to the benchmark directory; no notebook global state

## Wolfram Environment Caveat

Local Mathematica startup/autoload files (e.g. MathematicaMCP packages,
`Kernel/init.m`, `Autoload/` directory) may emit text on stdout/stderr that
interferes with machine-readable benchmark output parsing.

During independent review, a local run produced 38/39 because MathematicaMCP
autoload corrupted stdout during the `wolfram_12x12_rank` test. The benchmark
correctly failed closed (no false PASS was reported). The failure was
classified as `UNRESOLVED_ENVIRONMENT_FAILURE` — not a benchmark defect and not
a scientific issue.

### Clean-kernel invocation

To avoid autoload interference:

```bash
# Use -rawterm to suppress initialization output
wolfram -rawterm -script script.wl

# Or set a temporary user base directory
wolfram -script script.wl -pwfile /dev/null
```

The benchmark invokes Wolfram via `subprocess` with the `-script` flag. A
clean Wolfram installation without user-level autoload packages will produce
correct output.

## Deterministic Hashes

The full profile preserves deterministic scientific output hashes when Wolfram is available. The output SHA manifest is recorded in:

```
benchmark_profile_results.json (output_sha_manifest section)
```

## Cross-Engine Verification

When SymPy and Wolfram are both available, the 12x12 linear solve is verified across engines:

- SymPy: Exact rational arithmetic via `Matrix.solve()`
- Wolfram: Exact arithmetic via `LinearSolve` and `MatrixRank`
- NumPy: Numerical verification via `numpy.linalg.solve` (standard profile)

Generator-verifier separation is enforced: the same engine must not generate and verify the same result. Cross-engine comparison matrix:

| Generator | Verifier | Status |
|-----------|----------|--------|
| SymPy     | Wolfram  | IDEAL  |
| Wolfram   | SymPy    | IDEAL  |
| SymPy     | SymPy    | WARNING (same engine) |
| Wolfram   | Wolfram  | WARNING (same engine) |
