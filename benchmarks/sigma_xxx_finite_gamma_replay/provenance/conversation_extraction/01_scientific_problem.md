# Scientific Problem

## Observable

**[HUMAN_CONFIRMED]**

\[
\sigma_{xxx}\equiv\sigma^{dc}_{kkk}.
\]

It is the projected one-dimensional nonlinear DC conductivity.

## Dimensional scope

**[HUMAN_CONFIRMED]** One-dimensional momentum \(k\), with all Cartesian response indices already
projected to the same direction. Band labels remain multiband until the Rice–Mele specialization.

## DC limit status and finite-\(\Gamma\) target

**[HUMAN_CONFIRMED]**

```text
DC limit first
Gamma remains finite and exact
then normalization, decomposition, simplification,
closed-form construction and model-specific validation
```

The raw object is post-DC and finite-\(\Gamma\). A pre-raw \(\Gamma\)-expansion is forbidden.

## Motivation for closed-form simplification

**[EXPLICITLY_STATED_IN_CONVERSATION]** The raw expression contains long PolyGamma-weighted rational
coefficients, multiple energy-denominator towers, diagonal and off-diagonal \(h\)-matrix elements, and
genuine three-band products. The goal is to replace this raw representation with an exact,
auditable physical basis while preserving finite-\(\Gamma\) dependence and exact reconstruction.

## Model-independent projected stage

**[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** The projected multiband response is organized as

\[
\sigma^{xxx}=
\frac{e^3}{h}\int_{\rm BZ}\frac{dk}{2\pi}
\sum_{r,\eta,a}PG^\eta_{r,a}
\left[
C_0(a)+\sum_{b\ne a}C_1(a,b)+
\sum_{\substack{b\ne a\\c\ne a,b}}C_2(a,b,c)
\right].
\]

The active derivation establishes center, pair, and loop sectors; closes the pair \(h^{xx}\) geometry;
canonicalizes loop orientation; fuses seven kernels; and proves the three pair-velocity kernels form an
explicit BZ total derivative.

## Rice–Mele model-specific stage

**[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]**

\[
H(k)=t_0\cos k\,\sigma_x+\delta t\sin k\,\sigma_y+m\sigma_z,
\qquad
\epsilon_{1,2}(k)=\mp E(k).
\]

For two bands with spinless TRS, the genuine three-band loop sum is empty, the center contribution is BZ odd,
and the verified pair total derivative integrates away. The remaining ordered-pair shift-vector channel agrees
with the previously verified Modify5 longitudinal normal form.

## Established

- **[HUMAN_CONFIRMED]** raw post-DC finite-\(\Gamma\) boundary
- **[SYMBOLICALLY_VERIFIED]** \(118\)-row sector ledger and exact reconstruction
- **[SYMBOLICALLY_VERIFIED]** center/pair/loop physical organization
- **[SYMBOLICALLY_VERIFIED]** pair geometric closure and pair IBP reconstruction
- **[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** final four-kernel projected closed form
- **[SYMBOLICALLY_VERIFIED]** Rice–Mele specialization
- **[NUMERICALLY_SUPPORTED]** pointwise, integrated, mesh, gauge, and scaling validations

## Not established

- **[HUMAN_CONFIRMED]** general tensorial \(\sigma_{abc}\)
- **[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** center-sector IBP exactness
- **[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** loop-sector IBP exactness
- **[HUMAN_SUPPLIED_PREVIOUSLY_VERIFIED]** equality of the full projected expression with Anan Eq. (5)
- **[HUMAN_CONFIRMED]** general multiband vanishing of center or loop sectors
- **[HUMAN_CONFIRMED]** autonomous promotion of a new canonical formula
