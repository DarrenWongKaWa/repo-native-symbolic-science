# Engine Fixture Suite

Synthetic, redistributable test fixtures for the multi-backend CAS adapter layer.

## Fixtures

The fixture catalog (`fixture_catalog.json`) defines E1 through E12 synthetic expressions:
- E1-E4: Simple algebraic expressions
- E5-E8: Trigonometric and transcendental functions
- E9-E12: Vector and matrix operations

## Running

```bash
python3 tests/engine_fixtures/run_fixture_suite.py
```

## Engine Coverage

- SymPy: E1-E12 (all fixtures)
- NumPy/SciPy/mpmath: E1-E10 (numeric-evaluable fixtures)
- Mathematica: optional, not required

## Note

All fixtures are synthetic and redistributable. No private sigma_xxx or sigma_abc
scientific artifacts are included.
