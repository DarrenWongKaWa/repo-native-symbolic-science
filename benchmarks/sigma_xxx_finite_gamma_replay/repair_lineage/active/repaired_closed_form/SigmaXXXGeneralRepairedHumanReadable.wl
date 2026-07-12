(* Created with the Wolfram Language : www.wolfram.com *)
<|"integrand" -> "I_general[k] = Sum_n Sum_{eta,r} PG^{eta}_{r,n} * [K_center \
* v_n^3 + Sum_{m!=n} K_pair_R * R_nm|A_nm|^2 + Sum_{m!=n,l!=n,m} (K_loop_ReL \
* Re L_nml + K_loop_ImL * Im L_nml)]", "conductivity" -> 
  "sigma_xxx = (e^3/h) * (-1/2*Pi) * Int_{BZ} dk/(2*Pi) I_general[k]", 
 "PG_definition" -> "PG^{eta}_{r,n} = psi^{(r)}(1/2 + beta*Gamma/(2*Pi) + \
eta*i*beta*(mu-epsilon_n)/(2*Pi))", "BZ" -> "k in [-pi,pi], periodic", 
 "normalization" -> "(e^3/h)*(-Pi/2)", "finite_Gamma" -> 
  "Gamma exact, no small-Gamma expansion", "surviving_kernels" -> 
  {"K_center", "K_pair_R", "K_loop_ReL", "K_loop_ImL"}, 
 "F_pair_coefficients" -> {"-|0" -> ((I/2)*d)/(G^2*Pi), 
   "-|1" -> (beta*d^2*((-I)*d + 3*G))/(4*(d + (2*I)*G)^2*G*Pi^2), 
   "-|2" -> (beta^2*d*((2*I)*d - G))/(24*(d + (2*I)*G)*Pi^3), 
   "+|0" -> ((-1/2*I)*d)/(G^2*Pi), "+|1" -> (beta*d^2*(I*d + 3*G))/
     (4*(d - (2*I)*G)^2*G*Pi^2), "+|2" -> (beta^2*d*((-2*I)*d - G))/
     (24*(d - (2*I)*G)*Pi^3)}|>
