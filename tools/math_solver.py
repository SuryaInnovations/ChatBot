"""
Mathematical and symbolic computation tool using SymPy and exact numerical methods.
Follows the structured Formula -> Substitution -> Calculation -> Final Answer standard.
"""

from typing import Dict, Any
import sympy as sp

def solve_math_expression(expression: str, task_type: str = "solve") -> Dict[str, Any]:
    """
    Solves mathematical expressions, equations, calculus, or simplifications.
    task_type can be: 'eval', 'simplify', 'solve_equation', 'derivative', 'integral'.
    """
    try:
        if task_type == "simplify":
            expr = sp.sympify(expression)
            result = sp.simplify(expr)
            latex_res = sp.latex(result)
            return {
                "success": True,
                "input": expression,
                "result": str(result),
                "latex": latex_res
            }
        elif task_type == "solve_equation":
            # Assume expression equals 0 or split on '='
            if "=" in expression:
                left, right = expression.split("=", 1)
                expr = sp.sympify(left) - sp.sympify(right)
            else:
                expr = sp.sympify(expression)
            symbols = list(expr.free_symbols)
            if not symbols:
                return {"success": False, "error": "No variable found in equation"}
            solutions = sp.solve(expr, symbols[0])
            return {
                "success": True,
                "variable": str(symbols[0]),
                "solutions": [str(s) for s in solutions],
                "latex": sp.latex(solutions)
            }
        elif task_type == "derivative":
            parts = expression.split(",")
            expr = sp.sympify(parts[0])
            var = sp.Symbol(parts[1].strip()) if len(parts) > 1 else list(expr.free_symbols)[0]
            deriv = sp.diff(expr, var)
            return {
                "success": True,
                "derivative": str(deriv),
                "variable": str(var),
                "latex": sp.latex(deriv)
            }
        elif task_type == "integral":
            parts = expression.split(",")
            expr = sp.sympify(parts[0])
            var = sp.Symbol(parts[1].strip()) if len(parts) > 1 else list(expr.free_symbols)[0]
            integ = sp.integrate(expr, var)
            return {
                "success": True,
                "integral": str(integ),
                "variable": str(var),
                "latex": sp.latex(integ)
            }
        else: # eval / direct calculation
            expr = sp.sympify(expression)
            exact = expr
            numeric = expr.evalf()
            return {
                "success": True,
                "exact": str(exact),
                "numeric": float(numeric) if numeric.is_number and not numeric.has(sp.I) else str(numeric)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_finance(calc_type: str, principal: float, rate_pct: float, time_years: float, n_compounds: int = 1) -> Dict[str, Any]:
    """
    Calculates compound interest, simple interest, or EMI.
    """
    try:
        r = rate_pct / 100.0
        if calc_type.lower() in ["compound", "compound_interest"]:
            amount = principal * ((1 + r / n_compounds) ** (n_compounds * time_years))
            interest = amount - principal
            return {
                "success": True,
                "type": "Compound Interest",
                "formula": "A = P * (1 + r/n)^(n*t)",
                "principal": principal,
                "rate_pct": rate_pct,
                "years": time_years,
                "total_amount": round(amount, 2),
                "total_interest": round(interest, 2)
            }
        elif calc_type.lower() in ["simple", "simple_interest"]:
            interest = (principal * rate_pct * time_years) / 100.0
            amount = principal + interest
            return {
                "success": True,
                "type": "Simple Interest",
                "formula": "SI = (P * R * T) / 100",
                "principal": principal,
                "rate_pct": rate_pct,
                "years": time_years,
                "total_amount": round(amount, 2),
                "total_interest": round(interest, 2)
            }
        elif calc_type.lower() in ["emi"]:
            monthly_rate = r / 12.0
            months = int(time_years * 12)
            emi = principal * monthly_rate * ((1 + monthly_rate)**months) / (((1 + monthly_rate)**months) - 1)
            total_payment = emi * months
            total_interest = total_payment - principal
            return {
                "success": True,
                "type": "EMI",
                "formula": "EMI = [P x R x (1+R)^N]/[(1+R)^N-1]",
                "monthly_emi": round(emi, 2),
                "total_payment": round(total_payment, 2),
                "total_interest": round(total_interest, 2)
            }
        return {"success": False, "error": f"Unknown finance type: {calc_type}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
