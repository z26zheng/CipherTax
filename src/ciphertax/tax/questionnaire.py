"""CPA-style tax intake questionnaire.

Guides users through the information gathering process,
determines filing status, identifies applicable forms,
and generates a document checklist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from ciphertax.tax.forms import FilingStatus


@dataclass
class QuestionnaireResponse:
    """Collected answers from the intake questionnaire."""
    # Personal
    filing_status: FilingStatus = FilingStatus.SINGLE
    age: int = 30
    spouse_age: int = 0
    is_blind: bool = False
    spouse_is_blind: bool = False
    num_dependents_under_17: int = 0
    num_other_dependents: int = 0

    # Income types (yes/no — determines which forms to collect)
    has_w2_income: bool = False
    has_self_employment: bool = False
    has_interest_income: bool = False
    has_dividend_income: bool = False
    has_capital_gains: bool = False
    has_rental_income: bool = False
    has_retirement_income: bool = False
    has_social_security: bool = False
    has_k1_income: bool = False
    has_unemployment: bool = False
    has_gambling_income: bool = False
    has_crypto_transactions: bool = False

    # Deductions
    has_student_loans: bool = False
    has_mortgage: bool = False
    has_charitable_contributions: bool = False
    has_medical_expenses: bool = False
    has_state_local_taxes: bool = False
    has_hsa: bool = False
    has_ira_contributions: bool = False
    has_educator_expenses: bool = False

    # Life events
    got_married: bool = False
    had_baby: bool = False
    bought_home: bool = False
    sold_home: bool = False
    started_business: bool = False
    changed_jobs: bool = False
    retired: bool = False


def get_document_checklist(response: QuestionnaireResponse) -> list[dict]:
    """Generate a document checklist based on questionnaire responses.

    Returns list of dicts: [{"document": "W-2", "description": "...", "required": True}, ...]
    """
    checklist = []

    # Always needed
    checklist.append({
        "document": "Government-issued photo ID",
        "description": "Driver's license, passport, or state ID",
        "required": True,
    })
    checklist.append({
        "document": "Prior year tax return",
        "description": "Last year's Form 1040 (for AGI, carryovers)",
        "required": True,
    })

    # Income documents
    if response.has_w2_income:
        checklist.append({
            "document": "Form W-2",
            "description": "Wage and Tax Statement from each employer",
            "required": True,
        })

    if response.has_self_employment:
        checklist.extend([
            {"document": "Form 1099-NEC", "description": "Nonemployee compensation", "required": True},
            {"document": "Business income/expense records", "description": "Revenue, receipts, bank statements", "required": True},
            {"document": "Home office measurements", "description": "Square footage of office and total home (if applicable)", "required": False},
            {"document": "Vehicle mileage log", "description": "Business miles driven (if applicable)", "required": False},
        ])

    if response.has_interest_income:
        checklist.append({"document": "Form 1099-INT", "description": "Interest income from banks/bonds", "required": True})

    if response.has_dividend_income:
        checklist.append({"document": "Form 1099-DIV", "description": "Dividend income from investments", "required": True})

    if response.has_capital_gains or response.has_crypto_transactions:
        checklist.append({"document": "Form 1099-B", "description": "Broker proceeds from stock/crypto sales", "required": True})

    if response.has_rental_income:
        checklist.extend([
            {"document": "Rental income records", "description": "Rents received, tenant payments", "required": True},
            {"document": "Rental expense records", "description": "Mortgage interest, repairs, insurance, taxes, depreciation", "required": True},
        ])

    if response.has_retirement_income:
        checklist.append({"document": "Form 1099-R", "description": "Retirement distributions (IRA, 401k, pension)", "required": True})

    if response.has_social_security:
        checklist.append({"document": "Form SSA-1099", "description": "Social Security benefit statement", "required": True})

    if response.has_k1_income:
        checklist.append({"document": "Schedule K-1", "description": "Partner/shareholder income from partnerships or S-corps", "required": True})

    if response.has_unemployment:
        checklist.append({"document": "Form 1099-G", "description": "Unemployment compensation", "required": True})

    # Deduction documents
    if response.has_student_loans:
        checklist.append({"document": "Form 1098-E", "description": "Student loan interest paid", "required": True})

    if response.has_mortgage:
        checklist.append({"document": "Form 1098", "description": "Mortgage interest and property tax statement", "required": True})

    if response.has_charitable_contributions:
        checklist.append({"document": "Charitable contribution receipts", "description": "Donation receipts and acknowledgment letters", "required": True})

    if response.has_medical_expenses:
        checklist.append({"document": "Medical expense records", "description": "Bills, insurance statements, prescription costs", "required": True})

    if response.has_hsa:
        checklist.extend([
            {"document": "Form 1099-SA", "description": "HSA distributions", "required": True},
            {"document": "Form 5498-SA", "description": "HSA contributions", "required": True},
        ])

    if response.has_ira_contributions:
        checklist.append({"document": "Form 5498", "description": "IRA contribution statement", "required": True})

    # Bank info for direct deposit
    checklist.append({
        "document": "Bank routing and account numbers",
        "description": "For direct deposit of refund",
        "required": False,
    })

    return checklist


def get_applicable_forms(response: QuestionnaireResponse) -> list[str]:
    """Determine which IRS forms and schedules are needed.

    Returns list of form names that apply to this taxpayer.
    """
    forms = ["Form 1040"]

    has_schedule_1 = False
    has_schedule_2 = False

    if response.has_self_employment:
        forms.extend(["Schedule C", "Schedule SE"])
        has_schedule_1 = True
        has_schedule_2 = True

    if response.has_capital_gains or response.has_crypto_transactions:
        forms.extend(["Schedule D", "Form 8949"])
        has_schedule_1 = True

    if response.has_rental_income or response.has_k1_income:
        forms.append("Schedule E")
        has_schedule_1 = True

    if response.has_interest_income or response.has_dividend_income:
        forms.append("Schedule B")

    # Itemized deductions check
    might_itemize = (
        response.has_mortgage
        or response.has_charitable_contributions
        or response.has_medical_expenses
        or response.has_state_local_taxes
    )
    if might_itemize:
        forms.append("Schedule A")

    if response.has_student_loans or response.has_ira_contributions or response.has_hsa:
        has_schedule_1 = True

    if response.has_hsa:
        forms.append("Form 8889 (HSA)")

    if response.num_dependents_under_17 > 0:
        forms.append("Schedule 8812 (Child Tax Credit)")

    if has_schedule_1:
        forms.append("Schedule 1")
    if has_schedule_2:
        forms.append("Schedule 2")

    # Always include Schedule 3 if there are credits beyond CTC
    forms.append("Schedule 3")

    return sorted(set(forms))


def determine_filing_status(
    is_married: bool,
    is_legally_separated: bool = False,
    spouse_died_this_year: bool = False,
    spouse_died_last_year: bool = False,
    has_dependents: bool = False,
    paid_over_half_home_costs: bool = False,
    lived_apart_last_6_months: bool = False,
) -> list[dict]:
    """Determine eligible filing statuses based on personal situation.

    Returns list of eligible statuses with explanations, ordered by
    typically most beneficial first.
    """
    options = []

    if is_married and not is_legally_separated:
        options.append({
            "status": FilingStatus.MARRIED_JOINT,
            "name": "Married Filing Jointly",
            "description": "Usually the most beneficial for married couples. "
                          "Both spouses report all income and deductions together.",
            "typically_best": True,
        })
        options.append({
            "status": FilingStatus.MARRIED_SEPARATE,
            "name": "Married Filing Separately",
            "description": "Each spouse files their own return. Usually results in higher "
                          "tax but may be beneficial in specific situations (e.g., "
                          "liability protection, income-driven loan repayment).",
            "typically_best": False,
        })
        # HoH exception for married
        if has_dependents and paid_over_half_home_costs and lived_apart_last_6_months:
            options.append({
                "status": FilingStatus.HEAD_OF_HOUSEHOLD,
                "name": "Head of Household",
                "description": "Available even though married, because you lived apart "
                              "from spouse for last 6 months and maintain a home for dependents.",
                "typically_best": False,
            })
    elif spouse_died_this_year:
        options.append({
            "status": FilingStatus.MARRIED_JOINT,
            "name": "Married Filing Jointly",
            "description": "You can still file jointly for the year your spouse died.",
            "typically_best": True,
        })
    elif spouse_died_last_year and has_dependents:
        options.append({
            "status": FilingStatus.QUALIFYING_SURVIVING_SPOUSE,
            "name": "Qualifying Surviving Spouse",
            "description": "Available for 2 years after spouse's death if you have "
                          "a dependent child. Uses MFJ tax brackets and standard deduction.",
            "typically_best": True,
        })
    else:
        # Single or legally separated
        if has_dependents and paid_over_half_home_costs:
            options.append({
                "status": FilingStatus.HEAD_OF_HOUSEHOLD,
                "name": "Head of Household",
                "description": "Better tax brackets and higher standard deduction than Single. "
                              "Requires maintaining a home for a qualifying dependent.",
                "typically_best": True,
            })
        options.append({
            "status": FilingStatus.SINGLE,
            "name": "Single",
            "description": "Default status for unmarried taxpayers without dependents.",
            "typically_best": not has_dependents,
        })

    return options
