(* Reference Eq. (5) — PDF-authenticated from primary source *)
(* PDF SHA-256: fe1dea385c765608f48e2b3f0ce8b027c0433650b2cebfe4629dc9eb707cbc81 *)
(* Extracted from page 2 *)
eq5 = "\\sigma^{\\alpha\\alpha\\alpha} = \\frac{e^3}{\\hbar} \\int_{\\rm BZ} \\frac{d^d k}{(2\\pi)^d}\n\\Bigg[\n\\sum_{a\\neq b} R_{ab} |A_{ab}|^2 D^{(2)}_{ab}\n+ \\sum_{a\\neq b,\\,b\\neq c,\\,c\\neq a} {\\rm Re}[A_{ab}A_{bc}A_{ca}] D^{(3)}_{abc}\n\\Bigg]";
d2 = "D^{(2)}_{ab} = {\\rm Re}\\Bigg[\n\\frac{8\\Gamma(\\Delta_{ab}+i\\Gamma)}{(\\Delta_{ab}+2i\\Gamma)^2} f'_{+,a}\n- \\frac{2\\Gamma\\Delta_{ab}}{\\Delta_{ab}+2i\\Gamma} f''_{+,a}\n\\Bigg]";
d3 = "D^{(3)}_{abc} = {\\rm Re}\\Bigg[\n-\\left(\\frac{1}{\\Delta_{ac}}+\\frac{1}{\\Delta_{bc}}\\right)\\frac{8\\Gamma\\Delta_{ab}}{\\Delta_{ab}+2i\\Gamma} f'_{+,a}\n+ \\frac{2\\Gamma\\Delta_{ab}}{\\Delta_{ab}+2i\\Gamma} f''_{+,a}\n\\Bigg]";
