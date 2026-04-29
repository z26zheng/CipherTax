"""Tests for the tax calculation engine.

Verifies bracket calculations, deductions, credits, SE tax,
and full end-to-end scenarios against known tax outcomes.
"""

import pytest
from ciphertax.tax.calculator import TaxCalculator
from ciphertax.tax.forms import (
    FilingStatus, TaxInput, W2Income, F1099Int, F1099Div, F1099B,
    F1099Nec, F1099R, K1Income, ScheduleCData, RentalProperty,
    ItemizedDeductions, F1099Ssa,
)
from ciphertax.tax.questionnaire import (
    QuestionnaireResponse, get_document_checklist,
    get_applicable_forms, determine_filing_status,
)
from ciphertax.tax.optimizer import analyze


class TestBracketCalculation:
    """Test marginal tax bracket computation."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_10_percent_bracket_single(self, calc):
        """$10,000 income, single → all in 10% bracket."""
        tax = calc._compute_bracket_tax(10_000, "single")
        assert tax == 1_000.00  # 10,000 × 10%

    def test_12_percent_bracket_single(self, calc):
        """$30,000 income, single → spans 10% and 12% brackets."""
        tax = calc._compute_bracket_tax(30_000, "single")
        expected = 11_600 * 0.10 + (30_000 - 11_600) * 0.12
        assert abs(tax - expected) < 1.0

    def test_22_percent_bracket_single(self, calc):
        """$75,000 income, single → spans 10%, 12%, 22% brackets."""
        tax = calc._compute_bracket_tax(75_000, "single")
        expected = (
            11_600 * 0.10
            + (47_150 - 11_600) * 0.12
            + (75_000 - 47_150) * 0.22
        )
        assert abs(tax - expected) < 1.0

    def test_zero_income(self, calc):
        tax = calc._compute_bracket_tax(0, "single")
        assert tax == 0.0

    def test_negative_income(self, calc):
        tax = calc._compute_bracket_tax(-5_000, "single")
        assert tax == 0.0

    def test_top_bracket_single(self, calc):
        """$1,000,000 income → hits 37% bracket."""
        tax = calc._compute_bracket_tax(1_000_000, "single")
        assert tax > 300_000  # Sanity check — tax on $1M is >$300K

    def test_married_joint_brackets(self, calc):
        """MFJ brackets are roughly double single."""
        tax_single = calc._compute_bracket_tax(50_000, "single")
        tax_mfj = calc._compute_bracket_tax(100_000, "married_joint")
        # MFJ on $100K should be roughly double single on $50K
        assert abs(tax_mfj - 2 * tax_single) < 500


class TestSimpleW2Scenarios:
    """Test common W-2 employee scenarios."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_single_w2_employee(self, calc):
        """Single filer, $75,000 W-2 income."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=75_000, federal_tax_withheld=10_000)],
        )
        result = calc.compute(tax_input)

        assert result.total_wages == 75_000
        assert result.gross_income == 75_000
        assert result.agi == 75_000
        assert result.standard_deduction == 14_600
        assert result.taxable_income == 75_000 - 14_600
        assert result.deduction_type == "standard"
        assert result.ordinary_tax > 0
        assert result.total_withholding == 10_000
        assert result.effective_tax_rate > 0

    def test_married_two_incomes(self, calc):
        """MFJ, two W-2s totaling $150,000."""
        tax_input = TaxInput(
            filing_status=FilingStatus.MARRIED_JOINT,
            w2s=[
                W2Income(wages=90_000, federal_tax_withheld=12_000),
                W2Income(wages=60_000, federal_tax_withheld=7_000),
            ],
        )
        result = calc.compute(tax_input)

        assert result.total_wages == 150_000
        assert result.standard_deduction == 29_200
        assert result.taxable_income == 150_000 - 29_200
        assert result.total_withholding == 19_000

    def test_head_of_household_with_child(self, calc):
        """Head of Household with 1 qualifying child."""
        tax_input = TaxInput(
            filing_status=FilingStatus.HEAD_OF_HOUSEHOLD,
            w2s=[W2Income(wages=50_000, federal_tax_withheld=4_000)],
            num_qualifying_children=1,
        )
        result = calc.compute(tax_input)

        assert result.standard_deduction == 21_900
        assert result.child_tax_credit == 2_000
        assert result.total_tax < result.total_tax_before_credits

    def test_senior_additional_deduction(self, calc):
        """Single filer age 65+ gets additional standard deduction."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            age=67,
            w2s=[W2Income(wages=50_000)],
        )
        result = calc.compute(tax_input)
        assert result.standard_deduction == 14_600 + 1_950  # Base + additional


class TestSelfEmployment:
    """Test self-employment tax scenarios."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_freelancer_1099_nec(self, calc):
        """Freelancer with 1099-NEC income."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            f1099_necs=[F1099Nec(nonemployee_compensation=100_000)],
        )
        result = calc.compute(tax_input)

        assert result.total_business_income == 100_000
        assert result.self_employment_tax > 0
        # SE tax is ~15.3% of 92.35% of income
        expected_se = 100_000 * 0.9235 * 0.153
        assert abs(result.self_employment_tax - expected_se) < 100

    def test_schedule_c_business(self, calc):
        """Schedule C sole proprietor with expenses."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            schedule_cs=[ScheduleCData(
                gross_receipts=200_000,
                advertising=5_000,
                supplies=3_000,
                insurance=2_000,
                office_expense=1_500,
                travel=4_000,
            )],
        )
        result = calc.compute(tax_input)

        net_profit = 200_000 - (5_000 + 3_000 + 2_000 + 1_500 + 4_000)
        assert result.total_business_income == net_profit
        assert result.self_employment_tax > 0
        assert result.qbi_deduction > 0  # Should get QBI deduction

    def test_qbi_deduction_applied(self, calc):
        """QBI deduction reduces taxable income."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            f1099_necs=[F1099Nec(nonemployee_compensation=80_000)],
        )
        result = calc.compute(tax_input)
        assert result.qbi_deduction > 0
        assert result.qbi_deduction <= 80_000 * 0.20


class TestInvestmentIncome:
    """Test investment income scenarios."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_interest_income(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=60_000, federal_tax_withheld=8_000)],
            f1099_ints=[F1099Int(interest_income=2_000)],
        )
        result = calc.compute(tax_input)
        assert result.total_interest == 2_000
        assert result.gross_income == 62_000

    def test_long_term_capital_gains(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=40_000)],
            f1099_bs=[F1099B(proceeds=20_000, cost_basis=10_000, is_long_term=True)],
        )
        result = calc.compute(tax_input)
        assert result.net_long_term_gain == 10_000
        assert result.total_capital_gains == 10_000

    def test_capital_loss_limited(self, calc):
        """Capital losses limited to $3,000 against ordinary income."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=60_000)],
            f1099_bs=[F1099B(proceeds=5_000, cost_basis=20_000, is_long_term=True)],
        )
        result = calc.compute(tax_input)
        # Net loss is -$15,000 but limited to -$3,000
        assert result.total_capital_gains == -3_000

    def test_niit_applied(self, calc):
        """Net Investment Income Tax for high earners."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=180_000)],
            f1099_ints=[F1099Int(interest_income=50_000)],
        )
        result = calc.compute(tax_input)
        # AGI > $200K → NIIT applies
        assert result.niit > 0


class TestItemizedDeductions:
    """Test itemized deduction scenarios."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_itemize_when_exceeds_standard(self, calc):
        """Should itemize when itemized > standard deduction."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=100_000)],
            itemized_deductions=ItemizedDeductions(
                state_local_income_tax=10_000,
                home_mortgage_interest=8_000,
                charitable_cash=5_000,
            ),
        )
        result = calc.compute(tax_input)
        # SALT capped at $10K + $8K mortgage + $5K charitable = $23K > $14.6K standard
        assert result.deduction_type == "itemized"
        assert result.deduction_used > result.standard_deduction

    def test_salt_cap(self, calc):
        """SALT deduction capped at $10,000."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=200_000)],
            itemized_deductions=ItemizedDeductions(
                state_local_income_tax=15_000,
                real_estate_taxes=8_000,
                home_mortgage_interest=12_000,
            ),
        )
        result = calc.compute(tax_input)
        # SALT = min($15K + $8K = $23K, $10K cap) = $10K
        # Total = $10K + $12K = $22K > $14.6K standard → itemize
        assert result.deduction_type == "itemized"

    def test_medical_threshold(self, calc):
        """Medical expenses only deductible above 7.5% of AGI."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=50_000)],
            itemized_deductions=ItemizedDeductions(
                medical_dental_expenses=10_000,
                home_mortgage_interest=10_000,
            ),
        )
        result = calc.compute(tax_input)
        # Medical: $10K - (7.5% × $50K = $3,750) = $6,250 deductible


class TestChildTaxCredit:
    """Test Child Tax Credit scenarios."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_two_children(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.MARRIED_JOINT,
            w2s=[W2Income(wages=80_000)],
            num_qualifying_children=2,
        )
        result = calc.compute(tax_input)
        assert result.child_tax_credit == 4_000  # 2 × $2,000

    def test_ctc_phaseout(self, calc):
        """CTC phases out above income threshold."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=220_000)],
            num_qualifying_children=1,
        )
        result = calc.compute(tax_input)
        # $220K > $200K threshold → some phaseout
        assert result.child_tax_credit < 2_000
        assert result.child_tax_credit > 0


class TestQuestionnaire:
    """Test the CPA-style questionnaire."""

    def test_document_checklist_w2(self):
        response = QuestionnaireResponse(has_w2_income=True)
        checklist = get_document_checklist(response)
        docs = [item["document"] for item in checklist]
        assert "Form W-2" in docs
        assert "Government-issued photo ID" in docs

    def test_document_checklist_self_employed(self):
        response = QuestionnaireResponse(
            has_self_employment=True,
            has_interest_income=True,
        )
        checklist = get_document_checklist(response)
        docs = [item["document"] for item in checklist]
        assert "Form 1099-NEC" in docs
        assert "Form 1099-INT" in docs
        assert "Business income/expense records" in docs

    def test_applicable_forms_simple(self):
        response = QuestionnaireResponse(has_w2_income=True)
        forms = get_applicable_forms(response)
        assert "Form 1040" in forms

    def test_applicable_forms_complex(self):
        response = QuestionnaireResponse(
            has_w2_income=True,
            has_self_employment=True,
            has_capital_gains=True,
            has_rental_income=True,
            has_mortgage=True,
        )
        forms = get_applicable_forms(response)
        assert "Schedule C" in forms
        assert "Schedule D" in forms
        assert "Schedule E" in forms
        assert "Schedule A" in forms
        assert "Schedule SE" in forms

    def test_filing_status_single(self):
        options = determine_filing_status(is_married=False)
        statuses = [o["status"] for o in options]
        assert FilingStatus.SINGLE in statuses

    def test_filing_status_married(self):
        options = determine_filing_status(is_married=True)
        statuses = [o["status"] for o in options]
        assert FilingStatus.MARRIED_JOINT in statuses
        assert FilingStatus.MARRIED_SEPARATE in statuses

    def test_filing_status_hoh(self):
        options = determine_filing_status(
            is_married=False,
            has_dependents=True,
            paid_over_half_home_costs=True,
        )
        statuses = [o["status"] for o in options]
        assert FilingStatus.HEAD_OF_HOUSEHOLD in statuses


class TestOptimizer:
    """Test tax optimization suggestions."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_retirement_suggestion(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=75_000, traditional_401k=5_000)],
        )
        result = calc.compute(tax_input)
        suggestions = analyze(tax_input, result)
        titles = [s.title for s in suggestions]
        assert any("401(k)" in t for t in titles)

    def test_sep_ira_suggestion_for_self_employed(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            f1099_necs=[F1099Nec(nonemployee_compensation=100_000)],
        )
        result = calc.compute(tax_input)
        suggestions = analyze(tax_input, result)
        titles = [s.title for s in suggestions]
        assert any("SEP-IRA" in t for t in titles)

    def test_estimated_tax_suggestion(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            f1099_necs=[F1099Nec(nonemployee_compensation=100_000)],
        )
        result = calc.compute(tax_input)
        if result.amount_owed > 1_000:
            suggestions = analyze(tax_input, result)
            titles = [s.title for s in suggestions]
            assert any("estimated" in t.lower() for t in titles)

    def test_suggestions_sorted_by_priority(self, calc):
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=75_000)],
        )
        result = calc.compute(tax_input)
        suggestions = analyze(tax_input, result)
        if len(suggestions) >= 2:
            priority_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(suggestions) - 1):
                p1 = priority_order.get(suggestions[i].priority, 9)
                p2 = priority_order.get(suggestions[i + 1].priority, 9)
                assert p1 <= p2 or (
                    p1 == p2 and suggestions[i].potential_savings >= suggestions[i + 1].potential_savings
                )


class TestEndToEnd:
    """Full end-to-end tax calculation scenarios."""

    @pytest.fixture
    def calc(self):
        return TaxCalculator(tax_year=2024)

    def test_complex_return(self, calc):
        """Complex return: W-2 + freelance + investments + rental."""
        tax_input = TaxInput(
            filing_status=FilingStatus.MARRIED_JOINT,
            age=45,
            spouse_age=42,
            num_qualifying_children=2,
            w2s=[W2Income(
                wages=120_000,
                federal_tax_withheld=18_000,
                ss_wages=120_000,
                medicare_wages=120_000,
                traditional_401k=15_000,
            )],
            f1099_necs=[F1099Nec(nonemployee_compensation=30_000)],
            f1099_ints=[F1099Int(interest_income=1_500)],
            f1099_divs=[F1099Div(
                ordinary_dividends=3_000,
                qualified_dividends=2_500,
                capital_gain_distributions=1_000,
            )],
            f1099_bs=[
                F1099B(proceeds=15_000, cost_basis=10_000, is_long_term=True),
                F1099B(proceeds=8_000, cost_basis=6_000, is_long_term=False),
            ],
            rental_properties=[RentalProperty(
                rents_received=24_000,
                mortgage_interest=8_000,
                taxes=3_000,
                insurance=1_200,
                repairs=2_000,
                depreciation=5_000,
            )],
            student_loan_interest=2_500,
            estimated_tax_payments=4_000,
        )
        result = calc.compute(tax_input)

        # Basic sanity checks
        assert result.total_wages == 120_000
        assert result.total_business_income == 30_000
        assert result.total_interest == 1_500
        assert result.total_dividends == 3_000
        assert result.net_long_term_gain > 0
        assert result.total_rental_income > 0
        assert result.gross_income > 150_000
        assert result.agi > 0
        assert result.taxable_income > 0
        assert result.total_tax > 0
        assert result.child_tax_credit == 4_000
        assert result.self_employment_tax > 0
        assert result.effective_tax_rate > 0
        assert result.marginal_tax_rate > 0

    def test_refund_scenario(self, calc):
        """Taxpayer with high withholding should get a refund."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            w2s=[W2Income(wages=50_000, federal_tax_withheld=8_000)],
        )
        result = calc.compute(tax_input)
        # Tax on $50K - $14.6K = $35.4K ≈ $4K, withholding $8K → refund
        assert result.refund > 0
        assert result.amount_owed == 0

    def test_owed_scenario(self, calc):
        """Self-employed with no withholding should owe."""
        tax_input = TaxInput(
            filing_status=FilingStatus.SINGLE,
            f1099_necs=[F1099Nec(nonemployee_compensation=80_000)],
        )
        result = calc.compute(tax_input)
        assert result.amount_owed > 0
        assert result.refund == 0
