"""Tax optimization suggestions.

Analyzes a computed tax return and suggests strategies to reduce tax liability.
"""

from __future__ import annotations

from dataclasses import dataclass
from ciphertax.tax.forms import TaxInput, TaxResult, FilingStatus
from ciphertax.tax.data.federal_2024 import FEDERAL_2024


@dataclass
class TaxSuggestion:
    """A tax optimization suggestion."""
    category: str          # "deduction", "credit", "retirement", "planning", "entity"
    title: str
    description: str
    potential_savings: float  # Estimated tax savings ($)
    priority: str          # "high", "medium", "low"
    action_items: list[str]


def analyze(tax_input: TaxInput, result: TaxResult) -> list[TaxSuggestion]:
    """Analyze a tax return and generate optimization suggestions.

    Args:
        tax_input: The tax input data.
        result: The computed tax result.

    Returns:
        List of TaxSuggestion objects, sorted by priority and potential savings.
    """
    suggestions: list[TaxSuggestion] = []
    data = FEDERAL_2024
    status = tax_input.filing_status.value

    # =========================================================================
    # 1. Standard vs Itemized Deduction
    # =========================================================================
    if result.deduction_type == "standard" and tax_input.itemized_deductions:
        diff = result.standard_deduction - result.itemized_deduction_total
        if diff < 5_000:
            suggestions.append(TaxSuggestion(
                category="deduction",
                title="You're close to itemizing",
                description=f"Your itemized deductions (${result.itemized_deduction_total:,.0f}) "
                           f"are only ${diff:,.0f} below the standard deduction "
                           f"(${result.standard_deduction:,.0f}). "
                           f"Bunching charitable contributions or prepaying state taxes "
                           f"could push you over the threshold.",
                potential_savings=diff * result.marginal_tax_rate,
                priority="medium",
                action_items=[
                    "Consider 'bunching' 2 years of charitable donations into 1 year",
                    "Consider a Donor-Advised Fund for large charitable gifts",
                    "Prepay state/local taxes if close to SALT cap",
                ],
            ))

    # =========================================================================
    # 2. Retirement Contributions
    # =========================================================================
    total_401k = sum(w.traditional_401k + w.roth_401k for w in tax_input.w2s)
    max_401k = data["retirement"]["401k_limit"]
    if tax_input.age >= 50:
        max_401k += data["retirement"]["401k_catch_up"]

    if total_401k < max_401k and result.total_wages > 0:
        room = max_401k - total_401k
        savings = room * result.marginal_tax_rate
        suggestions.append(TaxSuggestion(
            category="retirement",
            title="Maximize 401(k) contributions",
            description=f"You contributed ${total_401k:,.0f} to your 401(k). "
                       f"The limit is ${max_401k:,.0f} — you have ${room:,.0f} of room. "
                       f"Pre-tax contributions reduce your taxable income.",
            potential_savings=savings,
            priority="high" if room > 5_000 else "medium",
            action_items=[
                f"Increase 401(k) contribution by ${room:,.0f}",
                "Consider Roth vs Traditional based on current vs expected future tax rate",
                "Check if employer offers a match — contribute at least enough to get full match",
            ],
        ))

    # IRA
    ira_limit = data["retirement"]["ira_limit"]
    if tax_input.age >= 50:
        ira_limit += data["retirement"]["ira_catch_up"]

    if tax_input.traditional_ira_contribution < ira_limit:
        ira_room = ira_limit - tax_input.traditional_ira_contribution
        suggestions.append(TaxSuggestion(
            category="retirement",
            title="Consider IRA contribution",
            description=f"You can contribute up to ${ira_limit:,.0f} to an IRA. "
                       f"Traditional IRA contributions may be tax-deductible. "
                       f"Roth IRA contributions grow tax-free.",
            potential_savings=ira_room * result.marginal_tax_rate,
            priority="medium",
            action_items=[
                "Check IRA deduction eligibility based on income and employer plan coverage",
                "Consider Roth IRA if income is below phaseout threshold",
                f"You can contribute until April 15 for the {tax_input.tax_year} tax year",
            ],
        ))

    # SEP-IRA for self-employed
    if result.total_business_income > 0 and tax_input.sep_ira_contribution == 0:
        max_sep = min(
            result.total_business_income * 0.20,  # ~20% of net SE income
            data["retirement"]["sep_ira_limit"],
        )
        if max_sep > 1_000:
            suggestions.append(TaxSuggestion(
                category="retirement",
                title="Open a SEP-IRA for self-employment income",
                description=f"As a self-employed individual, you can contribute up to "
                           f"${max_sep:,.0f} to a SEP-IRA, reducing your taxable income.",
                potential_savings=max_sep * result.marginal_tax_rate,
                priority="high",
                action_items=[
                    f"Contribute up to ${max_sep:,.0f} to a SEP-IRA",
                    "Consider a Solo 401(k) for even higher contribution limits",
                    "Deadline: tax filing deadline (with extensions)",
                ],
            ))

    # =========================================================================
    # 3. HSA Contribution
    # =========================================================================
    if tax_input.hsa_deduction == 0 and result.total_wages > 0:
        hsa_limit = data["health_savings_account"]["self_only"]
        suggestions.append(TaxSuggestion(
            category="deduction",
            title="Consider an HSA contribution",
            description="If you have a high-deductible health plan (HDHP), HSA contributions "
                       "are tax-deductible, grow tax-free, and withdrawals for medical "
                       "expenses are tax-free (triple tax advantage).",
            potential_savings=hsa_limit * result.marginal_tax_rate,
            priority="medium",
            action_items=[
                "Check if your health plan qualifies as an HDHP",
                f"Self-only limit: ${data['health_savings_account']['self_only']:,}",
                f"Family limit: ${data['health_savings_account']['family']:,}",
            ],
        ))

    # =========================================================================
    # 4. QBI Deduction Awareness
    # =========================================================================
    if result.qbi_deduction > 0:
        suggestions.append(TaxSuggestion(
            category="deduction",
            title="You're receiving the QBI deduction",
            description=f"Your Qualified Business Income deduction is "
                       f"${result.qbi_deduction:,.0f}. This 20% deduction on qualified "
                       f"business income phases out above "
                       f"${data['qbi']['taxable_income_threshold']['single']:,} "
                       f"(single) / ${data['qbi']['taxable_income_threshold']['married_joint']:,} (MFJ).",
            potential_savings=result.qbi_deduction * result.marginal_tax_rate,
            priority="low",
            action_items=[
                "Keep taxable income below the QBI threshold if possible",
                "Maximize above-the-line deductions to preserve QBI deduction",
            ],
        ))

    # =========================================================================
    # 5. Tax-Loss Harvesting
    # =========================================================================
    if len(tax_input.f1099_bs) > 0 and result.net_long_term_gain > 0:
        suggestions.append(TaxSuggestion(
            category="planning",
            title="Consider tax-loss harvesting",
            description=f"You have net capital gains of ${result.total_capital_gains:,.0f}. "
                       f"Selling investments at a loss before year-end can offset gains. "
                       f"Watch the wash sale rule (can't rebuy within 30 days).",
            potential_savings=min(result.total_capital_gains, 10_000) * 0.15,
            priority="medium" if result.total_capital_gains > 5_000 else "low",
            action_items=[
                "Review portfolio for unrealized losses",
                "Sell losing positions to offset gains",
                "Wait 31 days before rebuying (or buy a similar but not identical fund)",
                f"Unused losses carry forward (up to ${data['capital_loss_deduction_limit']:,}/year against ordinary income)",
            ],
        ))

    # =========================================================================
    # 6. Filing Status Optimization
    # =========================================================================
    if status == "married_joint" and result.total_tax > 0:
        suggestions.append(TaxSuggestion(
            category="planning",
            title="Verify MFJ vs MFS comparison",
            description="In some cases (e.g., income-driven student loan repayment, "
                       "medical expense deduction, or liability concerns), Married Filing "
                       "Separately may be beneficial despite typically higher tax.",
            potential_savings=0,
            priority="low",
            action_items=[
                "Compare tax liability under MFJ vs MFS",
                "Consider MFS if one spouse has high medical expenses",
                "Check impact on student loan repayment plans",
            ],
        ))

    # =========================================================================
    # 7. Estimated Tax Payments
    # =========================================================================
    if result.amount_owed > 1_000 and result.self_employment_tax > 0:
        suggestions.append(TaxSuggestion(
            category="planning",
            title="Set up quarterly estimated tax payments",
            description=f"You owe ${result.amount_owed:,.0f}. Self-employed individuals "
                       f"should make quarterly estimated payments (Form 1040-ES) to avoid "
                       f"underpayment penalties.",
            potential_savings=result.amount_owed * 0.03,  # Approximate penalty avoidance
            priority="high",
            action_items=[
                "Calculate quarterly payments (1/4 of expected annual tax)",
                "Due dates: April 15, June 15, Sept 15, Jan 15",
                "Safe harbor: pay 100% of prior year tax (110% if AGI > $150K)",
            ],
        ))

    # Sort by priority then savings
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: (priority_order.get(s.priority, 9), -s.potential_savings))

    return suggestions
