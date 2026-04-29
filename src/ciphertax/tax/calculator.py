"""Tax Calculator — computes federal income tax following IRS Form 1040 flow.

Implements the complete 1040 calculation:
1. Compute gross income from all sources
2. Apply above-the-line deductions → AGI
3. Apply standard or itemized deduction + QBI deduction
4. Calculate taxable income
5. Compute tax using brackets (ordinary + capital gains rates)
6. Apply credits
7. Add other taxes (SE, NIIT, Additional Medicare)
8. Subtract payments → refund or amount owed
"""

from __future__ import annotations

import logging
from typing import Optional

from ciphertax.tax.data.federal_2024 import FEDERAL_2024
from ciphertax.tax.forms import (
    FilingStatus,
    TaxInput,
    TaxResult,
)

logger = logging.getLogger(__name__)


class TaxCalculator:
    """Federal income tax calculator for a given tax year.

    Usage:
        calc = TaxCalculator(tax_year=2024)
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=75000, federal_tax_withheld=12000)],
        )
        result = calc.compute(tax_input)
        print(f"Tax: ${result.total_tax:,.2f}, Refund: ${result.refund:,.2f}")
    """

    def __init__(self, tax_year: int = 2024):
        self.tax_year = tax_year
        if tax_year == 2024:
            self.data = FEDERAL_2024
        else:
            raise ValueError(f"Tax year {tax_year} not supported. Available: 2024")

    def compute(self, tax_input: TaxInput) -> TaxResult:
        """Compute the full federal tax return."""
        status = tax_input.filing_status.value
        result = TaxResult()

        # =====================================================================
        # STEP 1: Compute gross income from all sources
        # =====================================================================
        result.total_wages = sum(w.wages for w in tax_input.w2s)
        result.total_interest = sum(f.interest_income for f in tax_input.f1099_ints)
        result.total_dividends = sum(f.ordinary_dividends for f in tax_input.f1099_divs)
        result.qualified_dividends = sum(f.qualified_dividends for f in tax_input.f1099_divs)

        # Business income (Schedule C + 1099-NEC)
        schedule_c_income = sum(sc.net_profit for sc in tax_input.schedule_cs)
        nec_income = sum(f.nonemployee_compensation for f in tax_input.f1099_necs)
        result.total_business_income = schedule_c_income + nec_income

        # Capital gains (Schedule D)
        result.net_short_term_gain = sum(
            (f.proceeds - f.cost_basis + f.wash_sale_loss_disallowed)
            for f in tax_input.f1099_bs if not f.is_long_term
        )
        result.net_long_term_gain = sum(
            (f.proceeds - f.cost_basis + f.wash_sale_loss_disallowed)
            for f in tax_input.f1099_bs if f.is_long_term
        )
        # Add capital gain distributions from 1099-DIV
        result.net_long_term_gain += sum(f.capital_gain_distributions for f in tax_input.f1099_divs)
        # Add K-1 capital gains
        result.net_short_term_gain += sum(k.short_term_capital_gain for k in tax_input.k1s)
        result.net_long_term_gain += sum(k.long_term_capital_gain for k in tax_input.k1s)
        # Apply capital loss carryover
        net_cap_gain = result.net_short_term_gain + result.net_long_term_gain - tax_input.capital_loss_carryover
        cap_loss_limit = self.data["capital_loss_deduction_limit"]
        if net_cap_gain < -cap_loss_limit:
            result.total_capital_gains = -cap_loss_limit
        else:
            result.total_capital_gains = net_cap_gain

        # Rental income
        result.total_rental_income = sum(r.net_income for r in tax_input.rental_properties)
        # Add K-1 rental
        result.total_rental_income += sum(k.rental_income for k in tax_input.k1s)

        # Retirement distributions
        result.total_retirement_income = sum(
            f.taxable_amount for f in tax_input.f1099_rs if not f.is_roth
        )

        # K-1 ordinary income
        k1_ordinary = sum(k.ordinary_income + k.guaranteed_payments for k in tax_input.k1s)

        # Other income
        result.total_other_income = (
            tax_input.unemployment_compensation
            + tax_input.gambling_income
            + tax_input.alimony_received
            + tax_input.other_income
            + k1_ordinary
        )

        # Social Security (simplified — up to 85% taxable based on income)
        if tax_input.ssa_1099:
            result.social_security_taxable = self._compute_ss_taxable(
                tax_input.ssa_1099.total_benefits, status, result
            )

        result.gross_income = (
            result.total_wages
            + result.total_interest
            + result.total_dividends
            + result.total_business_income
            + result.total_capital_gains
            + result.total_rental_income
            + result.total_retirement_income
            + result.social_security_taxable
            + result.total_other_income
        )

        # =====================================================================
        # STEP 2: Above-the-line deductions → AGI
        # =====================================================================
        se_income = result.total_business_income
        se_tax_deductible_half = 0.0
        if se_income > 0:
            taxable_se = se_income * self.data["se_tax_deductible_fraction"]
            se_tax_deductible_half = taxable_se * 0.153 / 2  # Deductible half of SE tax

        adjustments = (
            min(tax_input.educator_expenses, 300)
            + se_tax_deductible_half
            + tax_input.hsa_deduction
            + tax_input.self_employed_health_insurance
            + self._compute_student_loan_deduction(tax_input, result.gross_income, status)
            + tax_input.traditional_ira_contribution  # Simplified — should check phaseout
            + tax_input.sep_ira_contribution
            + tax_input.alimony_paid
        )
        # Early withdrawal penalty from 1099-INT
        adjustments += sum(f.early_withdrawal_penalty for f in tax_input.f1099_ints)

        result.total_adjustments = adjustments
        result.agi = max(0, result.gross_income - result.total_adjustments)

        # =====================================================================
        # STEP 3: Standard or itemized deduction
        # =====================================================================
        result.standard_deduction = self._compute_standard_deduction(tax_input, status)

        if tax_input.itemized_deductions:
            result.itemized_deduction_total = self._compute_itemized_total(
                tax_input.itemized_deductions, result.agi, status
            )

        if tax_input.force_itemize or (
            result.itemized_deduction_total > result.standard_deduction
            and tax_input.itemized_deductions is not None
        ):
            result.deduction_used = result.itemized_deduction_total
            result.deduction_type = "itemized"
        else:
            result.deduction_used = result.standard_deduction
            result.deduction_type = "standard"

        # QBI deduction (Section 199A)
        result.qbi_deduction = self._compute_qbi_deduction(tax_input, result.agi, status)

        # =====================================================================
        # STEP 4: Taxable income
        # =====================================================================
        result.taxable_income = max(0, result.agi - result.deduction_used - result.qbi_deduction)

        # =====================================================================
        # STEP 5: Compute tax
        # =====================================================================
        # Separate ordinary income from preferential-rate income
        preferential_income = max(0, result.net_long_term_gain) + result.qualified_dividends
        ordinary_taxable = max(0, result.taxable_income - preferential_income)

        result.ordinary_tax = self._compute_bracket_tax(ordinary_taxable, status)

        if preferential_income > 0:
            result.capital_gains_tax = self._compute_capital_gains_tax(
                result.taxable_income, preferential_income, status
            )
        else:
            result.capital_gains_tax = 0.0

        result.total_tax_before_credits = result.ordinary_tax + result.capital_gains_tax

        # =====================================================================
        # STEP 6: Credits
        # =====================================================================
        result.child_tax_credit = self._compute_child_tax_credit(tax_input, result.agi, status)
        # Foreign tax credit (simplified)
        foreign_tax = sum(f.foreign_tax_paid for f in tax_input.f1099_divs)
        result.other_credits = foreign_tax

        result.total_credits = result.child_tax_credit + result.other_credits
        # Nonrefundable credits limited to tax
        nonrefundable = min(result.total_credits, result.total_tax_before_credits)

        tax_after_credits = result.total_tax_before_credits - nonrefundable

        # =====================================================================
        # STEP 7: Other taxes
        # =====================================================================
        if se_income > 0:
            result.self_employment_tax = self._compute_se_tax(se_income)

        result.additional_medicare_tax = self._compute_additional_medicare(tax_input, status)
        result.niit = self._compute_niit(tax_input, result.agi, status)

        result.total_other_taxes = (
            result.self_employment_tax
            + result.additional_medicare_tax
            + result.niit
        )

        result.total_tax = tax_after_credits + result.total_other_taxes

        # =====================================================================
        # STEP 8: Payments and result
        # =====================================================================
        result.total_withholding = (
            sum(w.federal_tax_withheld for w in tax_input.w2s)
            + sum(f.federal_tax_withheld for f in tax_input.f1099_ints)
            + sum(f.federal_tax_withheld for f in tax_input.f1099_divs)
            + sum(f.federal_tax_withheld for f in tax_input.f1099_necs)
            + sum(f.federal_tax_withheld for f in tax_input.f1099_rs)
        )
        if tax_input.ssa_1099:
            result.total_withholding += tax_input.ssa_1099.federal_tax_withheld

        result.estimated_payments = (
            tax_input.estimated_tax_payments
            + tax_input.extension_payment
            + tax_input.prior_year_overpayment_applied
        )

        result.total_payments = result.total_withholding + result.estimated_payments

        if result.total_payments >= result.total_tax:
            result.refund = result.total_payments - result.total_tax
            result.amount_owed = 0.0
        else:
            result.refund = 0.0
            result.amount_owed = result.total_tax - result.total_payments

        # Effective and marginal rates
        if result.gross_income > 0:
            result.effective_tax_rate = result.total_tax / result.gross_income
        result.marginal_tax_rate = self._get_marginal_rate(result.taxable_income, status)

        logger.info(
            "Tax computed: Gross=$%,.0f, AGI=$%,.0f, Taxable=$%,.0f, "
            "Tax=$%,.0f, Refund=$%,.0f, Owed=$%,.0f",
            result.gross_income, result.agi, result.taxable_income,
            result.total_tax, result.refund, result.amount_owed,
        )

        return result

    # =========================================================================
    # BRACKET TAX COMPUTATION
    # =========================================================================

    def _compute_bracket_tax(self, taxable_income: float, status: str) -> float:
        """Compute ordinary income tax using marginal brackets."""
        rates = self.data["ordinary_rates"]
        brackets = self.data["ordinary_brackets"][status]
        return self._apply_brackets(taxable_income, rates, brackets)

    @staticmethod
    def _apply_brackets(income: float, rates: list[float], brackets: list[float]) -> float:
        """Apply marginal tax brackets to compute total tax."""
        if income <= 0:
            return 0.0

        tax = 0.0
        prev_bracket = 0.0

        for i, rate in enumerate(rates):
            if i < len(brackets):
                bracket_top = brackets[i]
                taxable_in_bracket = min(income, bracket_top) - prev_bracket
            else:
                # Last bracket — no upper limit
                taxable_in_bracket = income - prev_bracket

            if taxable_in_bracket > 0:
                tax += taxable_in_bracket * rate

            if i < len(brackets) and income <= brackets[i]:
                break
            prev_bracket = brackets[i] if i < len(brackets) else prev_bracket

        return round(tax, 2)

    def _compute_capital_gains_tax(
        self, taxable_income: float, preferential_income: float, status: str
    ) -> float:
        """Compute tax on long-term capital gains and qualified dividends."""
        rates = self.data["ltcg_rates"]
        brackets = self.data["ltcg_brackets"][status]

        # The preferential income "stacks" on top of ordinary income
        ordinary_income = taxable_income - preferential_income

        tax = 0.0
        income_so_far = ordinary_income

        for i, rate in enumerate(rates):
            if i < len(brackets):
                bracket_top = brackets[i]
            else:
                bracket_top = float("inf")

            if income_so_far >= bracket_top:
                continue

            taxable_at_rate = min(
                preferential_income - (tax / max(rate, 0.001) if rate > 0 else 0),
                bracket_top - income_so_far,
                preferential_income,
            )
            # Simpler approach: how much preferential income falls in each bracket
            pref_start = max(0, income_so_far - ordinary_income)
            pref_in_bracket = min(bracket_top, taxable_income) - max(income_so_far, ordinary_income)

            if pref_in_bracket > 0:
                tax += pref_in_bracket * rate

            income_so_far = bracket_top
            if income_so_far >= taxable_income:
                break

        # Handle income above last bracket
        if taxable_income > brackets[-1] and ordinary_income < taxable_income:
            above_last = taxable_income - max(brackets[-1], ordinary_income)
            if above_last > 0:
                tax += above_last * rates[-1]

        return round(max(0, tax), 2)

    def _get_marginal_rate(self, taxable_income: float, status: str) -> float:
        """Get the marginal tax rate for the given taxable income."""
        brackets = self.data["ordinary_brackets"][status]
        rates = self.data["ordinary_rates"]

        for i, bracket in enumerate(brackets):
            if taxable_income <= bracket:
                return rates[i]
        return rates[-1]

    # =========================================================================
    # DEDUCTIONS
    # =========================================================================

    def _compute_standard_deduction(self, tax_input: TaxInput, status: str) -> float:
        """Compute standard deduction including age/blindness additions."""
        base = self.data["standard_deduction"][status]

        additional_count = 0
        is_single_or_hoh = status in ("single", "head_of_household")

        if tax_input.age >= 65:
            additional_count += 1
        if tax_input.is_blind:
            additional_count += 1
        if status in ("married_joint", "married_separate"):
            if tax_input.spouse_age >= 65:
                additional_count += 1
            if tax_input.spouse_is_blind:
                additional_count += 1

        if is_single_or_hoh:
            additional = additional_count * self.data["additional_standard_deduction"]["single"]
        else:
            additional = additional_count * self.data["additional_standard_deduction"]["married"]

        return base + additional

    def _compute_itemized_total(
        self, itemized: "ItemizedDeductions", agi: float, status: str
    ) -> float:
        """Compute total itemized deductions with limits applied."""
        from ciphertax.tax.forms import ItemizedDeductions

        # Medical: only amount exceeding 7.5% of AGI
        medical_threshold = agi * self.data["medical_agi_threshold"]
        medical_deduction = max(0, itemized.medical_dental_expenses - medical_threshold)

        # SALT cap: $10,000 ($5,000 MFS)
        salt_cap = 5_000 if status == "married_separate" else self.data["salt_cap"]
        salt = min(
            salt_cap,
            max(itemized.state_local_income_tax, itemized.state_local_sales_tax)
            + itemized.real_estate_taxes
            + itemized.personal_property_taxes,
        )

        # Mortgage interest (simplified — assumes under $750K)
        mortgage = itemized.home_mortgage_interest

        # Charitable (simplified — check AGI limits)
        charitable = min(
            itemized.charitable_cash,
            agi * self.data["charitable"]["cash_agi_limit"],
        ) + min(
            itemized.charitable_noncash,
            agi * self.data["charitable"]["property_agi_limit"],
        )

        total = (
            medical_deduction
            + salt
            + mortgage
            + itemized.investment_interest
            + charitable
            + itemized.casualty_loss
            + itemized.gambling_losses
            + itemized.other_deductions
        )
        return round(total, 2)

    def _compute_student_loan_deduction(
        self, tax_input: TaxInput, gross_income: float, status: str
    ) -> float:
        """Compute student loan interest deduction with phaseout."""
        if tax_input.student_loan_interest <= 0:
            return 0.0

        max_deduction = min(tax_input.student_loan_interest,
                           self.data["student_loan_interest_max"])

        phaseout_key = status if status != "head_of_household" else "single"
        if phaseout_key == "married_separate":
            return 0.0  # MFS cannot take this deduction

        phaseout = self.data["student_loan_interest_phaseout"].get(phaseout_key)
        if phaseout:
            return self._apply_phaseout(max_deduction, gross_income, phaseout[0], phaseout[1])
        return max_deduction

    def _compute_qbi_deduction(
        self, tax_input: TaxInput, agi: float, status: str
    ) -> float:
        """Compute Qualified Business Income (QBI) deduction — Section 199A."""
        qbi = sum(sc.net_profit for sc in tax_input.schedule_cs if sc.net_profit > 0)
        qbi += sum(f.nonemployee_compensation for f in tax_input.f1099_necs)
        qbi += sum(k.ordinary_income for k in tax_input.k1s if k.ordinary_income > 0)

        if qbi <= 0:
            return 0.0

        deduction = qbi * self.data["qbi"]["deduction_rate"]

        # Taxable income limit: QBI deduction can't exceed 20% of taxable income
        # (before QBI deduction)
        taxable_before_qbi = agi - (
            self.data["standard_deduction"][status]
            if not tax_input.force_itemize
            else 0
        )
        deduction = min(deduction, max(0, taxable_before_qbi) * 0.20)

        # Simplified: no phaseout for specified service trades below threshold
        threshold_key = "single" if status != "married_joint" else "married_joint"
        threshold = self.data["qbi"]["taxable_income_threshold"].get(threshold_key, 191_950)

        if taxable_before_qbi > threshold:
            # Above threshold — simplified: reduce proportionally
            phaseout_range = self.data["qbi"]["phaseout_range"].get(threshold_key, 50_000)
            excess = taxable_before_qbi - threshold
            if excess >= phaseout_range:
                deduction = 0.0
            else:
                deduction *= (1 - excess / phaseout_range)

        return round(max(0, deduction), 2)

    # =========================================================================
    # CREDITS
    # =========================================================================

    def _compute_child_tax_credit(
        self, tax_input: TaxInput, agi: float, status: str
    ) -> float:
        """Compute Child Tax Credit."""
        ctc_data = self.data["child_tax_credit"]
        num_children = tax_input.num_qualifying_children
        num_other = tax_input.num_other_dependents

        if num_children == 0 and num_other == 0:
            return 0.0

        total_credit = (
            num_children * ctc_data["amount_per_child"]
            + num_other * ctc_data["other_dependent_credit"]
        )

        # Phaseout
        phaseout_start = ctc_data["phaseout_start"].get(status, 200_000)
        if agi > phaseout_start:
            excess = agi - phaseout_start
            reduction = (excess // 1_000) * (ctc_data["phaseout_rate"] * 1_000)
            total_credit = max(0, total_credit - reduction)

        return round(total_credit, 2)

    # =========================================================================
    # SELF-EMPLOYMENT TAX
    # =========================================================================

    def _compute_se_tax(self, se_income: float) -> float:
        """Compute self-employment tax (Schedule SE)."""
        if se_income <= 0:
            return 0.0

        taxable_se = se_income * self.data["se_tax_deductible_fraction"]

        ss_data = self.data["social_security"]
        med_data = self.data["medicare"]

        # Social Security portion (capped at wage base)
        ss_taxable = min(taxable_se, ss_data["wage_base"])
        ss_tax = ss_taxable * ss_data["rate_self_employed"]

        # Medicare portion (no cap)
        med_tax = taxable_se * med_data["rate_self_employed"]

        return round(ss_tax + med_tax, 2)

    def _compute_additional_medicare(self, tax_input: TaxInput, status: str) -> float:
        """Compute Additional Medicare Tax (0.9% above threshold)."""
        threshold = self.data["additional_medicare"]["threshold"].get(status, 200_000)
        total_medicare_wages = (
            sum(w.medicare_wages for w in tax_input.w2s)
            + sum(sc.net_profit for sc in tax_input.schedule_cs if sc.net_profit > 0)
            + sum(f.nonemployee_compensation for f in tax_input.f1099_necs)
        )
        if total_medicare_wages > threshold:
            return round((total_medicare_wages - threshold) * self.data["additional_medicare"]["rate"], 2)
        return 0.0

    def _compute_niit(self, tax_input: TaxInput, agi: float, status: str) -> float:
        """Compute Net Investment Income Tax (3.8%)."""
        threshold = self.data["niit_threshold"].get(status, 200_000)
        if agi <= threshold:
            return 0.0

        # Net investment income
        nii = (
            sum(f.interest_income for f in tax_input.f1099_ints)
            + sum(f.ordinary_dividends for f in tax_input.f1099_divs)
            + max(0, sum(
                (f.proceeds - f.cost_basis) for f in tax_input.f1099_bs
            ))
            + sum(r.net_income for r in tax_input.rental_properties if r.net_income > 0)
        )

        taxable = min(nii, agi - threshold)
        return round(max(0, taxable) * self.data["niit_rate"], 2)

    # =========================================================================
    # SOCIAL SECURITY
    # =========================================================================

    def _compute_ss_taxable(self, benefits: float, status: str, result: TaxResult) -> float:
        """Compute taxable portion of Social Security benefits (simplified)."""
        if benefits <= 0:
            return 0.0

        provisional = (
            result.total_wages + result.total_interest + result.total_dividends
            + result.total_business_income + result.total_rental_income
            + result.total_retirement_income + benefits * 0.5
        )

        if status == "married_joint":
            base1, base2 = 32_000, 44_000
        elif status == "married_separate":
            base1, base2 = 0, 0
        else:
            base1, base2 = 25_000, 34_000

        if provisional <= base1:
            return 0.0
        elif provisional <= base2:
            return min(0.5 * (provisional - base1), 0.5 * benefits)
        else:
            amount1 = min(0.5 * (base2 - base1), 0.5 * benefits)
            amount2 = 0.85 * (provisional - base2)
            return min(amount1 + amount2, 0.85 * benefits)

    # =========================================================================
    # UTILITY
    # =========================================================================

    @staticmethod
    def _apply_phaseout(
        amount: float, income: float, start: float, end: float
    ) -> float:
        """Apply a linear phaseout to an amount based on income."""
        if income <= start:
            return amount
        if income >= end:
            return 0.0
        ratio = (income - start) / (end - start)
        return round(amount * (1 - ratio), 2)
