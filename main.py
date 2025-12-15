from typing import Optional

# ----------------------------
# Basic number-theoretic tools
# ----------------------------

def nu2(n: int) -> int:
    """2-adic valuation ν2(n) for n>0."""
    if n <= 0:
        raise ValueError("nu2 is defined here for positive integers only")
    return (n & -n).bit_length() - 1  # since (n & -n) = 2^{ν2(n)}

def odd_part(n: int) -> int:
    """odd(n) = n / 2^{ν2(n)} for n>0."""
    return n >> nu2(n)

def in_residue_set_mod20(n: int, residues: set[int]) -> bool:
    return (n % 20) in residues


# ----------------------------
# Primitive Collatz map (for reference)
# ----------------------------

def T(n: int) -> int:
    """Primitive Collatz map."""
    return n // 2 if (n % 2 == 0) else 3 * n + 1


# ----------------------------
# Exit maps / macro maps
# ----------------------------

def E0_exit(n: int) -> int:
    """
    Exit map for the 0-component (multiples of 10).
    JS: firstLeavingElementOf0Loop(n)

    For n = 10k, we have T(10k)=5k and then remove powers of 2:
    E0(10k) = 5 * odd(k).
    """
    if n % 10 != 0:
        return n // 2
    k = n // 10
    return 5 * odd_part(k)

def E8_exit(n: int) -> int:
    """
    Exit map for the 8↔9 component.
    JS: firstLeavingElementOf8Loop(n)

    If n ≢ 18 (mod 20), return n/2.
    If n ≡ 18 (mod 20), write n = 20m - 2 and return:
      E8(n) = (10 * 3^{ν2(m)+1} * odd(m) - 2)/2.
    """
    if (n - 18) % 20 != 0:
        return n // 2

    m = (n + 2) // 20
    a = nu2(m)
    r = odd_part(m)
    N_out = 10 * (3 ** (a + 1)) * r - 2
    return N_out // 2

def F6_macro(n: int) -> int:
    """
    Macro-map for the local 6→3→0→5→6 component:
      F6(n) = 3 * odd(3n+2) + 1
    JS: macroF(n)
    """
    u = 3 * n + 2
    return 3 * odd_part(u) + 1

def E6_exit(n: int) -> int:
    """
    Bounded macro-scan exit routine for the 6-component.
    JS: firstLeavingElementOf6Loop(n)

    C6 is defined modulo 20 by residues {0,3,5,6}.
    If n not in C6: return n/2.
    Else iterate F6 at most B = bitlen(3n+2) times, stopping early if we leave C6.
    Return fk/2 at the end.
    """
    C6 = {0, 3, 5, 6}
    if not in_residue_set_mod20(n, C6):
        return n // 2

    u0 = 3 * n + 2
    B = u0.bit_length()  # exact binary length ℓ(u0)
    fk = n

    for _ in range(B):
        if not in_residue_set_mod20(fk, C6):
            break
        fk = F6_macro(fk)

    return fk // 2

def F4_macro(n: int) -> int:
    """
    Three-odd-step macro-map used in the 4-component:
      F4(n) = 3*odd( 3*odd(3*odd(n)+1) + 1 ) + 1
    JS: Fbig(n)
    """
    a = odd_part(n)
    b = odd_part(3 * a + 1)
    c = odd_part(3 * b + 1)
    return 3 * c + 1

def _in_C4_by_last_digit(x: int) -> bool:
    """
    Membership test for the digit-cycle {1,2,4,7} mod 10.
    The JS implementation treats x==1 as terminal and excludes it from 'inCycle'.
    """
    if x == 1:
        return False
    return (x % 10) in {1, 2, 4, 7}

def _micro_step_checker_C4(n: int) -> Optional[int]:
    """
    Given n, form a = 3*odd(n)+1 and scan a/2^r for r=1..ν2(a).
    Return the first cand that leaves C4 (by last-digit test), else None.
    """
    a = 3 * odd_part(n) + 1
    t = nu2(a)
    for r in range(1, t + 1):
        cand = a >> r
        if not _in_C4_by_last_digit(cand):
            return cand
    return None

def _check_macro_internal_for_leaving_C4(fk: int) -> Optional[int]:
    """
    Mirrors your JS checkMacroInternalForLeaving:
      - start with a = fk/2, strip powers of 2 while checking last-digit membership
      - run micro-step checker on a
      - if none, run micro-step checker on (3a+1)
    """
    a = fk // 2

    while a % 2 == 0:
        if not _in_C4_by_last_digit(a):
            return a
        a //= 2

    res = _micro_step_checker_C4(a)
    if res is not None:
        return res

    return _micro_step_checker_C4(3 * a + 1)

def E4_exit(n0: int) -> int:
    """
    Bounded macro-scan 'first leaving element' routine for the 4-component.
    JS: firstLeavingElement4Cycle(n0)

    Cutoff: UB = bitlen(3n0+2) + ν2(3n0+2).
    At each macro-state fk, scan internal candidates; if found, return it.
    Else advance fk := F4(fk). If UB exceeded, raise.
    """
    if n0 <= 0:
        raise ValueError("n0 must be a positive integer")

    t = 3 * n0 + 2
    UB = t.bit_length()

    fk = n0
    for _ in range(UB + 1):
        found = _check_macro_internal_for_leaving_C4(fk)
        if found is not None:
            return found
        fk = F4_macro(fk)

    raise RuntimeError("Reached UB without leaving C4 (bounded scan exhausted).")

# ----------------------------
# Simplified Collatz, just look at the 4-cycle
# ----------------------------
def solve_C4_hub(n: int) -> int:
    """
    Final 'hub' routine centered at the 4-component.

    Importance:
    Empirically (and in the reduced mod-10 transition graph), all trajectories
    are routed into the 4-component; from there, the solver can be organized as
    a short, fixed pipeline:
        C4  --(E4_exit)-->  (possibly) C6  --(E6_exit)-->  C8  --(E8_exit)-->  C4
    If the C4 exit immediately yields 1, we are done; otherwise we apply the
    subsequent exit routines in sequence. This concentrates the solver's control
    flow into one canonical entry point, making the 4-component the natural
    "glue" between the nontrivial residue components.
    """
    while True:
        a = E4_exit(n)
        if a == 1:
            return 1
        n = E8_exit(E6_exit(a))	

# ----------------------------
# Top-level reduced solver
# ----------------------------

def _prefix_is_even(n: int) -> bool:
    """Decimal prefix parity (digits before the last digit)."""
    return ((n // 10) % 2) == 0

def reduced_collatz_solver(n: int) -> int:
    """
    Reduced Collatz solver implementing your digit-routing logic.

    This is an executable routing framework:
    - exact exit maps for 0- and 8-components,
    - bounded macro-scans for 4- and 6-components,
    - direct odd step for {1,3,5,7,9},
    - branching at last digit 2 via prefix parity.

    Returns 1 once n < 10, matching your JS base case.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")

    while n >= 10:
        d = n % 10

        if d == 0:
            n = E0_exit(n)              # jump to 3
        elif d in {1, 3, 5, 7, 9}:
            n = 3 * n + 1               # odd step
        elif d == 2:
            if _prefix_is_even(n):
                n = (n // 2) * 3 + 1    # 4
            else:
                n = n // 2				# 6
        elif d == 4:
            n = E4_exit(n)              # 6 or end
        elif d == 6:
            n = E6_exit(n)              # 8
        elif d == 8:
            n = E8_exit(n)              # 6
        else:
            raise RuntimeError(f"Unhandled last digit {d} (should be impossible).")

    return 1

if __name__ == "__main__":
    # Smoke-test: run the reduced solver on the first 10,000 positive integers.
    for n in range(1, 10_001):
        try:
            reduced_collatz_solver(n)
        except Exception as exc:
            raise RuntimeError(f"Solver failed on n={n}") from exc

    print("OK: reduced_collatz_solver ran successfully for n = 1..10000")
	
	# Smoke-test: run the compressed 4-cycle test
    for n in range(14, 1_000_001, 10):
        try:
            solve_C4_hub(n)
        except Exception as exc:
            raise RuntimeError(f"Solver failed on n={n}") from exc

    print("OK: solve_C4_hub ran successfully for n = 14..1_000_000")
