# CAS Backends

## Supported Backends

### SymPy (Required)
- Role: open-source exact symbolic baseline
- License: BSD
- Used for: symbolic simplification, algebraic verification

### NumPy / SciPy / mpmath (Required)
- Role: numerical and high-precision support
- License: BSD
- Used for: numerical evaluation, high-precision verification

### Mathematica (Optional)
- Role: optional verified commercial backend
- License: Proprietary (Wolfram Research)
- Note: Mathematica is not mandatory; all core functionality works without it

## ENGINE_003 Verification Status

The multi-backend CAS adapter layer has been verified as:
**MINIMUM_MULTI_BACKEND_CAS_ADAPTER_LAYER_VERIFIED_WITH_CAVEAT**

### Documented Caveats

1. Mathematica path is optional; release success does not require Mathematica availability
2. Exact symbolic claims remain separate from numerical claims
3. Unsupported capability fails safely
4. Cross-engine verification has a documented usage boundary
