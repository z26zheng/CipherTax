#!/usr/bin/env python3
"""CipherTax Demo — End-to-end tax filing preparation.

Demonstrates:
1. Tax calculation with realistic scenarios
2. PII redaction pipeline on a mock W-2 PDF
3. Tax optimization suggestions
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def print_header(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_section(title: str) -> None:
    print(f"\n--- {title} ---\n")


# ============================================================================
# SCENARIO 1: Single W-2 Employee
# ============================================================================
def demo_simple_w2():
    from ciphertax.tax.calculator import TaxCalculator
    from ciphertax.tax.forms import FilingStatus, TaxInput, W2Income
    from ciphertax.tax.optimizer import analyze

    print_header("SCENARIO 1: Single W-2 Employee ($75,000)")

    calc = TaxCalculator(tax_year=2024)
    tax_input = TaxInput(
        filing_status=FilingStatus.SINGLE,
        age=30,
        w2s=[W2Income(
            employer_name="Acme Corp",
            wages=75_000,
            federal_tax_withheld=10_500,
            ss_wages=75_000,
            ss_tax_withheld=4_650,
            medicare_wages=75_000,
            medicare_tax_withheld=1_087.50,
            state="CA",
            state_wages=75_000,
            state_tax_withheld=3_200,
            traditional_401k=6_000,
        )],
        student_loan_interest=1_800,
    )

    result = calc.compute(tax_input)

    print(f"  Filing Status:          Single")
    print(f"  Total Wages:            ${result.total_wages:>12,.2f}")
    print(f"  Gross Income:           ${result.gross_income:>12,.2f}")
    print(f"  Adjustments:            ${result.total_adjustments:>12,.2f}")
    print(f"  AGI:                    ${result.agi:>12,.2f}")
    print(f"  Deduction ({result.deduction_type:>8}):  ${result.deduction_used:>12,.2f}")
    print(f"  QBI Deduction:          ${result.qbi_deduction:>12,.2f}")
    print(f"  Taxable Income:         ${result.taxable_income:>12,.2f}")
    print()
    print(f"  Ordinary Tax:           ${result.ordinary_tax:>12,.2f}")
    print(f"  Capital Gains Tax:      ${result.capital_gains_tax:>12,.2f}")
    print(f"  Credits:               -${result.total_credits:>12,.2f}")
    print(f"  SE Tax:                 ${result.self_employment_tax:>12,.2f}")
    print(f"  NIIT:                   ${result.niit:>12,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  TOTAL TAX:              ${result.total_tax:>12,.2f}")
    print()
    print(f"  Federal Withholding:    ${result.total_withholding:>12,.2f}")
    print(f"  Estimated Payments:     ${result.estimated_payments:>12,.2f}")
    print(f"  Total Payments:         ${result.total_payments:>12,.2f}")
    print()
    if result.refund > 0:
        print(f"  ✅ REFUND:              ${result.refund:>12,.2f}")
    else:
        print(f"  ❌ AMOUNT OWED:         ${result.amount_owed:>12,.2f}")
    print()
    print(f"  Effective Tax Rate:     {result.effective_tax_rate:>11.1%}")
    print(f"  Marginal Tax Rate:      {result.marginal_tax_rate:>11.0%}")

    # Optimization suggestions
    print_section("Tax Optimization Suggestions")
    suggestions = analyze(tax_input, result)
    for i, s in enumerate(suggestions[:5], 1):
        print(f"  {i}. [{s.priority.upper()}] {s.title}")
        print(f"     {s.description[:100]}...")
        if s.potential_savings > 0:
            print(f"     Potential savings: ${s.potential_savings:,.0f}")
        print()


# ============================================================================
# SCENARIO 2: Married with Kids, Freelance + W-2
# ============================================================================
def demo_complex_scenario():
    from ciphertax.tax.calculator import TaxCalculator
    from ciphertax.tax.forms import (
        FilingStatus, TaxInput, W2Income, F1099Nec, F1099Int,
        F1099Div, F1099B, RentalProperty, ItemizedDeductions,
    )
    from ciphertax.tax.optimizer import analyze

    print_header("SCENARIO 2: MFJ, 2 Kids, W-2 + Freelance + Investments + Rental")

    calc = TaxCalculator(tax_year=2024)
    tax_input = TaxInput(
        filing_status=FilingStatus.MARRIED_JOINT,
        age=42,
        spouse_age=40,
        num_qualifying_children=2,
        w2s=[W2Income(
            employer_name="BigTech Inc",
            wages=135_000,
            federal_tax_withheld=22_000,
            ss_wages=135_000,
            medicare_wages=135_000,
            traditional_401k=18_000,
            retirement_plan=True,
        )],
        f1099_necs=[F1099Nec(
            payer_name="Freelance Client A",
            nonemployee_compensation=35_000,
        )],
        f1099_ints=[F1099Int(
            payer_name="Big Bank",
            interest_income=2_200,
        )],
        f1099_divs=[F1099Div(
            payer_name="Vanguard",
            ordinary_dividends=4_500,
            qualified_dividends=3_800,
            capital_gain_distributions=1_200,
        )],
        f1099_bs=[
            F1099B(description="AAPL", proceeds=25_000, cost_basis=18_000, is_long_term=True),
            F1099B(description="TSLA", proceeds=8_000, cost_basis=12_000, is_long_term=True),
            F1099B(description="NVDA", proceeds=15_000, cost_basis=10_000, is_long_term=False),
        ],
        rental_properties=[RentalProperty(
            property_address="123 Rental Ave",
            rents_received=28_800,
            mortgage_interest=9_600,
            taxes=3_200,
            insurance=1_400,
            repairs=2_500,
            depreciation=6_000,
            management_fees=2_880,
        )],
        itemized_deductions=ItemizedDeductions(
            state_local_income_tax=12_000,
            real_estate_taxes=6_500,
            home_mortgage_interest=14_000,
            charitable_cash=5_000,
            charitable_noncash=2_000,
        ),
        student_loan_interest=2_500,
        estimated_tax_payments=8_000,
    )

    result = calc.compute(tax_input)

    print(f"  Filing Status:          Married Filing Jointly")
    print(f"  Dependents:             2 qualifying children")
    print()
    print_section("Income Summary")
    print(f"  W-2 Wages:              ${result.total_wages:>12,.2f}")
    print(f"  Self-Employment:        ${result.total_business_income:>12,.2f}")
    print(f"  Interest:               ${result.total_interest:>12,.2f}")
    print(f"  Dividends:              ${result.total_dividends:>12,.2f}")
    print(f"    (Qualified:           ${result.qualified_dividends:>12,.2f})")
    print(f"  Capital Gains:          ${result.total_capital_gains:>12,.2f}")
    print(f"    (Long-term net:       ${result.net_long_term_gain:>12,.2f})")
    print(f"    (Short-term net:      ${result.net_short_term_gain:>12,.2f})")
    print(f"  Rental Income:          ${result.total_rental_income:>12,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  GROSS INCOME:           ${result.gross_income:>12,.2f}")

    print_section("Deductions & Taxable Income")
    print(f"  Adjustments (above-line): ${result.total_adjustments:>10,.2f}")
    print(f"  AGI:                    ${result.agi:>12,.2f}")
    print(f"  Deduction ({result.deduction_type:>8}):  ${result.deduction_used:>12,.2f}")
    print(f"  QBI Deduction:          ${result.qbi_deduction:>12,.2f}")
    print(f"  TAXABLE INCOME:         ${result.taxable_income:>12,.2f}")

    print_section("Tax Computation")
    print(f"  Ordinary Tax:           ${result.ordinary_tax:>12,.2f}")
    print(f"  Capital Gains Tax:      ${result.capital_gains_tax:>12,.2f}")
    print(f"  Tax Before Credits:     ${result.total_tax_before_credits:>12,.2f}")
    print(f"  Child Tax Credit:      -${result.child_tax_credit:>12,.2f}")
    print(f"  Other Credits:         -${result.other_credits:>12,.2f}")
    print(f"  Self-Employment Tax:    ${result.self_employment_tax:>12,.2f}")
    print(f"  Additional Medicare:    ${result.additional_medicare_tax:>12,.2f}")
    print(f"  NIIT (3.8%):            ${result.niit:>12,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  TOTAL TAX:              ${result.total_tax:>12,.2f}")

    print_section("Payments & Result")
    print(f"  Federal Withholding:    ${result.total_withholding:>12,.2f}")
    print(f"  Estimated Payments:     ${result.estimated_payments:>12,.2f}")
    print(f"  Total Payments:         ${result.total_payments:>12,.2f}")
    print()
    if result.refund > 0:
        print(f"  ✅ REFUND:              ${result.refund:>12,.2f}")
    else:
        print(f"  ❌ AMOUNT OWED:         ${result.amount_owed:>12,.2f}")
    print()
    print(f"  Effective Tax Rate:     {result.effective_tax_rate:>11.1%}")
    print(f"  Marginal Tax Rate:      {result.marginal_tax_rate:>11.0%}")

    # Optimization
    print_section("Tax Optimization Suggestions")
    suggestions = analyze(tax_input, result)
    for i, s in enumerate(suggestions[:5], 1):
        print(f"  {i}. [{s.priority.upper()}] {s.title}")
        print(f"     {s.description[:120]}...")
        if s.potential_savings > 0:
            print(f"     💰 Potential savings: ${s.potential_savings:,.0f}")
        for action in s.action_items[:2]:
            print(f"     → {action}")
        print()


# ============================================================================
# SCENARIO 3: PII Redaction Pipeline on Mock W-2 PDF
# ============================================================================
def demo_pii_pipeline():
    print_header("SCENARIO 3: PII Redaction Pipeline (Mock W-2 PDF)")

    # Generate fixture if needed
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    w2_pdf = fixtures_dir / "mock_w2.pdf"
    if not w2_pdf.exists():
        from tests.fixtures.generate_fixtures import generate_w2_pdf
        generate_w2_pdf()

    from ciphertax.pipeline import CipherTaxPipeline
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pipeline = CipherTaxPipeline(
            vault_password="demo-password",
            vault_dir=Path(tmp) / "vault",
        )
        result = pipeline.process(w2_pdf, skip_ai=True)

    print(f"  Source: {result.source_file}")
    print(f"  Pages: {result.pages_extracted}")
    print(f"  Extraction: {', '.join(result.extraction_methods)}")
    print(f"  PII Found: {result.pii_entities_found}")
    print(f"  PII Redacted: {result.pii_entities_redacted}")
    print(f"  Entity Types: {', '.join(result.entity_types)}")

    print_section("Token Mapping (PII → Tokens)")
    for token, value in sorted(result.token_mapping.items()):
        masked = value[:4] + "***" if len(value) > 4 else "***"
        print(f"    {token:20s} ← {masked}")

    print_section("Original Text (first 400 chars)")
    print(f"    {result.original_text[:400]}...")

    print_section("Redacted Text (first 400 chars) — THIS is what goes to AI")
    print(f"    {result.redacted_text[:400]}...")

    # Verify no PII leaked
    print_section("PII Leak Check")
    known_pii = ["234-56-7890", "Maria Elena Rodriguez", "45-6789012",
                  "maria.rodriguez@example.com", "(555) 867-5309"]
    all_clean = True
    for pii in known_pii:
        if pii in result.redacted_text:
            print(f"    ❌ LEAKED: {pii}")
            all_clean = False
        else:
            print(f"    ✅ Safe: {pii[:20]}*** not in redacted text")
    if all_clean:
        print(f"\n    🔐 ALL PII SUCCESSFULLY REDACTED — Safe to send to AI!")


# ============================================================================
# SCENARIO 4: CPA Questionnaire
# ============================================================================
def demo_questionnaire():
    from ciphertax.tax.questionnaire import (
        QuestionnaireResponse, get_document_checklist,
        get_applicable_forms, determine_filing_status,
    )

    print_header("SCENARIO 4: CPA-Style Tax Intake Questionnaire")

    response = QuestionnaireResponse(
        has_w2_income=True,
        has_self_employment=True,
        has_interest_income=True,
        has_dividend_income=True,
        has_capital_gains=True,
        has_rental_income=True,
        has_mortgage=True,
        has_charitable_contributions=True,
        has_student_loans=True,
        has_hsa=True,
        num_dependents_under_17=2,
    )

    print_section("Filing Status Options")
    options = determine_filing_status(is_married=True)
    for opt in options:
        best = " ⭐ RECOMMENDED" if opt["typically_best"] else ""
        print(f"    • {opt['name']}{best}")
        print(f"      {opt['description'][:80]}")
        print()

    print_section("Required Documents Checklist")
    checklist = get_document_checklist(response)
    for item in checklist:
        req = "✅" if item["required"] else "📋"
        print(f"    {req} {item['document']}")
        print(f"       {item['description']}")

    print_section("Applicable IRS Forms")
    forms = get_applicable_forms(response)
    for form in forms:
        print(f"    📄 {form}")


if __name__ == "__main__":
    demo_simple_w2()
    demo_complex_scenario()
    demo_pii_pipeline()
    demo_questionnaire()
