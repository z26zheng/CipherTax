"""Tax form data models — structured representations of IRS forms.

These dataclasses model the input data from tax documents (W-2, 1099s, etc.)
and the computed output forms (1040, Schedule C, D, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class FilingStatus(str, Enum):
    """IRS filing status."""
    SINGLE = "single"
    MARRIED_JOINT = "married_joint"
    MARRIED_SEPARATE = "married_separate"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "married_joint"  # Same brackets as MFJ


# ============================================================================
# INPUT FORMS — Data extracted from tax documents
# ============================================================================

@dataclass
class W2Income:
    """Data from Form W-2 (Wage and Tax Statement)."""
    employer_name: str = ""
    wages: float = 0.0                    # Box 1
    federal_tax_withheld: float = 0.0     # Box 2
    ss_wages: float = 0.0                 # Box 3
    ss_tax_withheld: float = 0.0          # Box 4
    medicare_wages: float = 0.0           # Box 5
    medicare_tax_withheld: float = 0.0    # Box 6
    state: str = ""                       # Box 15
    state_wages: float = 0.0             # Box 16
    state_tax_withheld: float = 0.0      # Box 17
    retirement_plan: bool = False         # Box 13 (covered by employer plan)
    # Boxes 12a-12d codes
    traditional_401k: float = 0.0         # Code D
    roth_401k: float = 0.0               # Code AA
    hsa_employer: float = 0.0            # Code W
    dependent_care: float = 0.0          # Code 10


@dataclass
class F1099Int:
    """Data from Form 1099-INT (Interest Income)."""
    payer_name: str = ""
    interest_income: float = 0.0          # Box 1
    early_withdrawal_penalty: float = 0.0  # Box 2
    us_savings_bond_interest: float = 0.0  # Box 3
    federal_tax_withheld: float = 0.0     # Box 4
    tax_exempt_interest: float = 0.0      # Box 8


@dataclass
class F1099Div:
    """Data from Form 1099-DIV (Dividends and Distributions)."""
    payer_name: str = ""
    ordinary_dividends: float = 0.0       # Box 1a
    qualified_dividends: float = 0.0      # Box 1b
    capital_gain_distributions: float = 0.0  # Box 2a
    section_199a_dividends: float = 0.0   # Box 5
    federal_tax_withheld: float = 0.0     # Box 4
    foreign_tax_paid: float = 0.0         # Box 7


@dataclass
class F1099B:
    """Data from Form 1099-B (Proceeds From Broker Transactions)."""
    description: str = ""
    date_acquired: str = ""
    date_sold: str = ""
    proceeds: float = 0.0                 # Box 1d
    cost_basis: float = 0.0              # Box 1e
    gain_loss: float = 0.0               # Computed
    is_long_term: bool = False
    basis_reported_to_irs: bool = True
    wash_sale_loss_disallowed: float = 0.0


@dataclass
class F1099Nec:
    """Data from Form 1099-NEC (Nonemployee Compensation)."""
    payer_name: str = ""
    nonemployee_compensation: float = 0.0  # Box 1
    federal_tax_withheld: float = 0.0     # Box 4


@dataclass
class F1099R:
    """Data from Form 1099-R (Retirement Distributions)."""
    payer_name: str = ""
    gross_distribution: float = 0.0       # Box 1
    taxable_amount: float = 0.0          # Box 2a
    federal_tax_withheld: float = 0.0    # Box 4
    distribution_code: str = ""          # Box 7 (1=early, 7=normal, etc.)
    is_roth: bool = False


@dataclass
class K1Income:
    """Data from Schedule K-1 (Partner's/Shareholder's Share)."""
    entity_name: str = ""
    entity_type: str = ""  # "partnership" or "s_corp"
    ordinary_income: float = 0.0          # Box 1
    rental_income: float = 0.0           # Box 2
    interest_income: float = 0.0         # Box 5
    dividend_income: float = 0.0         # Box 6a
    qualified_dividends: float = 0.0     # Box 6b
    short_term_capital_gain: float = 0.0  # Box 8
    long_term_capital_gain: float = 0.0  # Box 9a
    section_179_deduction: float = 0.0   # Box 12
    self_employment_income: float = 0.0  # Box 14
    guaranteed_payments: float = 0.0


@dataclass
class F1099Ssa:
    """Data from SSA-1099 (Social Security Benefits)."""
    total_benefits: float = 0.0          # Box 5
    benefits_repaid: float = 0.0         # Box 4
    federal_tax_withheld: float = 0.0    # Box 6


# ============================================================================
# BUSINESS INCOME (Schedule C)
# ============================================================================

@dataclass
class ScheduleCData:
    """Data for Schedule C (Profit or Loss From Business)."""
    business_name: str = ""
    business_code: str = ""  # NAICS code
    accounting_method: str = "cash"  # cash, accrual, or other

    # Income
    gross_receipts: float = 0.0
    returns_and_allowances: float = 0.0
    other_income: float = 0.0
    cost_of_goods_sold: float = 0.0

    # Expenses
    advertising: float = 0.0
    car_and_truck: float = 0.0
    commissions_and_fees: float = 0.0
    contract_labor: float = 0.0
    depreciation: float = 0.0
    employee_benefit_programs: float = 0.0
    insurance: float = 0.0
    interest_mortgage: float = 0.0
    interest_other: float = 0.0
    legal_and_professional: float = 0.0
    office_expense: float = 0.0
    pension_profit_sharing: float = 0.0
    rent_lease_vehicles: float = 0.0
    rent_lease_other: float = 0.0
    repairs_maintenance: float = 0.0
    supplies: float = 0.0
    taxes_licenses: float = 0.0
    travel: float = 0.0
    meals: float = 0.0  # 50% deductible for most business meals
    utilities: float = 0.0
    wages: float = 0.0
    other_expenses: float = 0.0

    # Home office
    home_office_sqft: float = 0.0
    home_total_sqft: float = 0.0
    use_simplified_method: bool = True

    # Vehicle
    business_miles: float = 0.0
    use_standard_mileage: bool = True

    @property
    def gross_income(self) -> float:
        return (self.gross_receipts - self.returns_and_allowances
                - self.cost_of_goods_sold + self.other_income)

    @property
    def total_expenses(self) -> float:
        return sum([
            self.advertising, self.car_and_truck, self.commissions_and_fees,
            self.contract_labor, self.depreciation, self.employee_benefit_programs,
            self.insurance, self.interest_mortgage, self.interest_other,
            self.legal_and_professional, self.office_expense,
            self.pension_profit_sharing, self.rent_lease_vehicles,
            self.rent_lease_other, self.repairs_maintenance, self.supplies,
            self.taxes_licenses, self.travel, self.meals * 0.5,
            self.utilities, self.wages, self.other_expenses,
        ])

    @property
    def net_profit(self) -> float:
        return self.gross_income - self.total_expenses


# ============================================================================
# RENTAL INCOME (Schedule E)
# ============================================================================

@dataclass
class RentalProperty:
    """Data for Schedule E rental property."""
    property_address: str = ""
    property_type: str = ""  # single_family, multi_family, commercial
    days_rented: int = 0
    personal_use_days: int = 0

    # Income
    rents_received: float = 0.0
    other_income: float = 0.0

    # Expenses
    advertising: float = 0.0
    auto_travel: float = 0.0
    cleaning_maintenance: float = 0.0
    commissions: float = 0.0
    insurance: float = 0.0
    legal_professional: float = 0.0
    management_fees: float = 0.0
    mortgage_interest: float = 0.0
    other_interest: float = 0.0
    repairs: float = 0.0
    supplies: float = 0.0
    taxes: float = 0.0
    utilities: float = 0.0
    depreciation: float = 0.0
    other_expenses: float = 0.0

    @property
    def total_expenses(self) -> float:
        return sum([
            self.advertising, self.auto_travel, self.cleaning_maintenance,
            self.commissions, self.insurance, self.legal_professional,
            self.management_fees, self.mortgage_interest, self.other_interest,
            self.repairs, self.supplies, self.taxes, self.utilities,
            self.depreciation, self.other_expenses,
        ])

    @property
    def net_income(self) -> float:
        return self.rents_received + self.other_income - self.total_expenses


# ============================================================================
# ITEMIZED DEDUCTIONS (Schedule A)
# ============================================================================

@dataclass
class ItemizedDeductions:
    """Data for Schedule A (Itemized Deductions)."""
    # Medical and dental
    medical_dental_expenses: float = 0.0

    # Taxes paid
    state_local_income_tax: float = 0.0
    state_local_sales_tax: float = 0.0  # Alternative to income tax
    real_estate_taxes: float = 0.0
    personal_property_taxes: float = 0.0

    # Interest paid
    home_mortgage_interest: float = 0.0
    investment_interest: float = 0.0

    # Charitable contributions
    charitable_cash: float = 0.0
    charitable_noncash: float = 0.0

    # Casualty and theft losses (federally declared disaster only)
    casualty_loss: float = 0.0

    # Other deductions
    gambling_losses: float = 0.0  # Limited to gambling income
    other_deductions: float = 0.0


# ============================================================================
# COMPREHENSIVE TAX INPUT — All data needed for a complete return
# ============================================================================

@dataclass
class TaxInput:
    """Complete tax input data for computing a return.

    This is the master data structure that holds all information
    needed to compute Form 1040 and all supporting schedules.
    """
    # Filing info
    tax_year: int = 2024
    filing_status: FilingStatus = FilingStatus.SINGLE
    age: int = 30
    spouse_age: int = 0
    is_blind: bool = False
    spouse_is_blind: bool = False
    can_be_claimed_as_dependent: bool = False

    # Dependents
    num_qualifying_children: int = 0      # Under 17 for CTC
    num_other_dependents: int = 0

    # Income sources
    w2s: list[W2Income] = field(default_factory=list)
    f1099_ints: list[F1099Int] = field(default_factory=list)
    f1099_divs: list[F1099Div] = field(default_factory=list)
    f1099_bs: list[F1099B] = field(default_factory=list)
    f1099_necs: list[F1099Nec] = field(default_factory=list)
    f1099_rs: list[F1099R] = field(default_factory=list)
    k1s: list[K1Income] = field(default_factory=list)
    ssa_1099: Optional[F1099Ssa] = None

    # Business income
    schedule_cs: list[ScheduleCData] = field(default_factory=list)

    # Rental income
    rental_properties: list[RentalProperty] = field(default_factory=list)

    # Other income
    alimony_received: float = 0.0  # Pre-2019 agreements only
    unemployment_compensation: float = 0.0
    gambling_income: float = 0.0
    other_income: float = 0.0

    # Above-the-line deductions
    educator_expenses: float = 0.0  # Max $300
    hsa_deduction: float = 0.0
    self_employed_health_insurance: float = 0.0
    student_loan_interest: float = 0.0
    traditional_ira_contribution: float = 0.0
    sep_ira_contribution: float = 0.0
    alimony_paid: float = 0.0  # Pre-2019 agreements only

    # Itemized deductions (if itemizing)
    itemized_deductions: Optional[ItemizedDeductions] = None
    force_itemize: bool = False  # Override standard deduction

    # Payments and withholding
    estimated_tax_payments: float = 0.0
    extension_payment: float = 0.0
    prior_year_overpayment_applied: float = 0.0

    # Prior year data (for safe harbor, carryovers)
    prior_year_tax: float = 0.0
    prior_year_agi: float = 0.0
    capital_loss_carryover: float = 0.0  # From prior years


# ============================================================================
# TAX RESULT — Computed output
# ============================================================================

@dataclass
class TaxResult:
    """Computed tax return result."""
    # Income
    total_wages: float = 0.0
    total_interest: float = 0.0
    total_dividends: float = 0.0
    qualified_dividends: float = 0.0
    total_business_income: float = 0.0
    total_capital_gains: float = 0.0
    net_short_term_gain: float = 0.0
    net_long_term_gain: float = 0.0
    total_rental_income: float = 0.0
    total_retirement_income: float = 0.0
    social_security_taxable: float = 0.0
    total_other_income: float = 0.0
    gross_income: float = 0.0

    # Adjustments
    total_adjustments: float = 0.0
    agi: float = 0.0

    # Deductions
    standard_deduction: float = 0.0
    itemized_deduction_total: float = 0.0
    deduction_used: float = 0.0
    deduction_type: str = "standard"  # "standard" or "itemized"
    qbi_deduction: float = 0.0

    # Tax computation
    taxable_income: float = 0.0
    ordinary_tax: float = 0.0
    capital_gains_tax: float = 0.0
    total_tax_before_credits: float = 0.0

    # Credits
    child_tax_credit: float = 0.0
    other_credits: float = 0.0
    total_credits: float = 0.0

    # Other taxes
    self_employment_tax: float = 0.0
    additional_medicare_tax: float = 0.0
    niit: float = 0.0
    total_other_taxes: float = 0.0

    # Total tax
    total_tax: float = 0.0

    # Payments
    total_withholding: float = 0.0
    estimated_payments: float = 0.0
    refundable_credits: float = 0.0
    total_payments: float = 0.0

    # Result
    refund: float = 0.0
    amount_owed: float = 0.0

    # Effective rates
    effective_tax_rate: float = 0.0
    marginal_tax_rate: float = 0.0

    # Breakdown details
    details: dict = field(default_factory=dict)
