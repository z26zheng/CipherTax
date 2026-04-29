"""Federal tax constants for tax year 2024.

All values sourced from IRS Revenue Procedure 2023-34 and IRS publications.
Brackets represent the UPPER boundary of each bracket (income up to that amount).
The last bracket has no upper limit (infinity).

Reference: UsTaxes project (github.com/ustaxes/UsTaxes) for cross-validation.
"""

from __future__ import annotations

FEDERAL_2024 = {
    "tax_year": 2024,

    # =========================================================================
    # ORDINARY INCOME TAX BRACKETS
    # Rates apply to income WITHIN each bracket (marginal rates)
    # "brackets" = upper boundary of each bracket; last rate applies above last bracket
    # =========================================================================
    "ordinary_rates": [0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37],

    "ordinary_brackets": {
        "single":            [11_600, 47_150, 100_525, 191_950, 243_725, 609_350],
        "married_joint":     [23_200, 94_300, 201_050, 383_900, 487_450, 731_200],
        "married_separate":  [11_600, 47_150, 100_525, 191_950, 243_725, 365_600],
        "head_of_household": [16_550, 63_100, 100_500, 191_950, 243_700, 609_350],
    },

    # =========================================================================
    # STANDARD DEDUCTION
    # =========================================================================
    "standard_deduction": {
        "single": 14_600,
        "married_joint": 29_200,
        "married_separate": 14_600,
        "head_of_household": 21_900,
    },
    "additional_standard_deduction": {
        # Per qualifying individual (age 65+ or blind)
        "single": 1_950,           # Also applies to HoH
        "married": 1_550,          # Per spouse, applies to MFJ/MFS
    },

    # =========================================================================
    # LONG-TERM CAPITAL GAINS BRACKETS
    # Based on TAXABLE INCOME (not just capital gains)
    # =========================================================================
    "ltcg_rates": [0.00, 0.15, 0.20],

    "ltcg_brackets": {
        "single":            [47_025, 518_900],
        "married_joint":     [94_050, 583_750],
        "married_separate":  [47_025, 291_850],
        "head_of_household": [63_000, 551_350],
    },

    # Collectibles (art, coins, etc.) max rate
    "collectibles_rate": 0.28,
    # Unrecaptured Section 1250 gain (depreciation recapture on real estate)
    "section_1250_rate": 0.25,

    # =========================================================================
    # NET INVESTMENT INCOME TAX (NIIT) — 3.8%
    # =========================================================================
    "niit_rate": 0.038,
    "niit_threshold": {
        "single": 200_000,
        "married_joint": 250_000,
        "married_separate": 125_000,
        "head_of_household": 200_000,
    },

    # =========================================================================
    # FICA / SELF-EMPLOYMENT TAX
    # =========================================================================
    "social_security": {
        "rate_employee": 0.062,        # 6.2% employee share
        "rate_employer": 0.062,        # 6.2% employer share
        "rate_self_employed": 0.124,   # 12.4% combined
        "wage_base": 168_600,          # Maximum taxable earnings
    },
    "medicare": {
        "rate_employee": 0.0145,       # 1.45% employee share
        "rate_employer": 0.0145,       # 1.45% employer share
        "rate_self_employed": 0.029,   # 2.9% combined
        # No wage base limit for regular Medicare
    },
    "additional_medicare": {
        "rate": 0.009,                 # 0.9% additional
        "threshold": {
            "single": 200_000,
            "married_joint": 250_000,
            "married_separate": 125_000,
            "head_of_household": 200_000,
        },
    },
    "se_tax_deductible_fraction": 0.9235,  # 92.35% of net SE income is taxable

    # =========================================================================
    # ALTERNATIVE MINIMUM TAX (AMT)
    # =========================================================================
    "amt": {
        "exemption": {
            "single": 85_700,
            "married_joint": 133_300,
            "married_separate": 66_650,
            "head_of_household": 85_700,
        },
        "phaseout_start": {
            "single": 609_350,
            "married_joint": 1_218_700,
            "married_separate": 609_350,
            "head_of_household": 609_350,
        },
        "rates": [0.26, 0.28],
        "bracket": {
            "single": 232_600,
            "married_joint": 232_600,
            "married_separate": 116_300,
            "head_of_household": 232_600,
        },
    },

    # =========================================================================
    # CHILD TAX CREDIT
    # =========================================================================
    "child_tax_credit": {
        "amount_per_child": 2_000,      # Per qualifying child under 17
        "other_dependent_credit": 500,   # Per other dependent
        "refundable_max": 1_700,         # Max additional child tax credit (refundable)
        "earned_income_threshold": 2_500,  # For refundable portion
        "phaseout_start": {
            "single": 200_000,
            "married_joint": 400_000,
            "married_separate": 200_000,
            "head_of_household": 200_000,
        },
        "phaseout_rate": 0.05,  # $50 reduction per $1,000 over threshold
    },

    # =========================================================================
    # EARNED INCOME TAX CREDIT (EITC) — 2024
    # =========================================================================
    "eitc": {
        "max_credit": {
            0: 632,       # No qualifying children
            1: 3_995,     # 1 child
            2: 6_604,     # 2 children
            3: 7_430,     # 3+ children
        },
        "earned_income_limit": {
            "single": {0: 18_591, 1: 49_084, 2: 55_768, 3: 59_899},
            "married_joint": {0: 25_511, 1: 56_004, 2: 62_688, 3: 66_819},
        },
        "investment_income_limit": 11_600,
    },

    # =========================================================================
    # EDUCATION CREDITS
    # =========================================================================
    "american_opportunity_credit": {
        "max_credit": 2_500,
        "refundable_portion": 0.40,  # 40% refundable = $1,000 max
        "expense_limit": 4_000,
        "phaseout": {
            "single": (80_000, 90_000),
            "married_joint": (160_000, 180_000),
        },
    },
    "lifetime_learning_credit": {
        "max_credit": 2_000,
        "rate": 0.20,
        "expense_limit": 10_000,
        "phaseout": {
            "single": (80_000, 90_000),
            "married_joint": (160_000, 180_000),
        },
    },

    # =========================================================================
    # RETIREMENT CONTRIBUTION LIMITS
    # =========================================================================
    "retirement": {
        "401k_limit": 23_000,
        "401k_catch_up": 7_500,           # Age 50+
        "ira_limit": 7_000,
        "ira_catch_up": 1_000,            # Age 50+
        "sep_ira_limit": 69_000,
        "sep_ira_rate": 0.25,             # 25% of compensation (20% for SE)
        "simple_ira_limit": 16_000,
        "simple_ira_catch_up": 3_500,
        "solo_401k_employee_limit": 23_000,
        "solo_401k_total_limit": 69_000,

        # Traditional IRA deduction phaseout (if covered by employer plan)
        "ira_deduction_phaseout": {
            "single": (77_000, 87_000),
            "married_joint_covered": (123_000, 143_000),
            "married_joint_spouse_covered": (230_000, 240_000),
            "married_separate": (0, 10_000),
        },
        # Roth IRA contribution phaseout
        "roth_ira_phaseout": {
            "single": (146_000, 161_000),
            "married_joint": (230_000, 240_000),
            "married_separate": (0, 10_000),
        },
    },

    # =========================================================================
    # QUALIFIED BUSINESS INCOME (QBI) DEDUCTION — Section 199A
    # =========================================================================
    "qbi": {
        "deduction_rate": 0.20,  # 20% of QBI
        "taxable_income_threshold": {
            "single": 191_950,
            "married_joint": 383_900,
        },
        "phaseout_range": {
            "single": 50_000,        # Full phaseout over $50K above threshold
            "married_joint": 100_000,
        },
    },

    # =========================================================================
    # ITEMIZED DEDUCTION LIMITS
    # =========================================================================
    "salt_cap": 10_000,  # State and local tax deduction cap ($5,000 MFS)
    "mortgage_interest_limit": 750_000,  # Mortgage debt limit for interest deduction
    "charitable": {
        "cash_agi_limit": 0.60,    # 60% of AGI for cash contributions
        "property_agi_limit": 0.30, # 30% of AGI for appreciated property
    },
    "medical_agi_threshold": 0.075,  # Medical expenses deductible above 7.5% of AGI

    # =========================================================================
    # OTHER LIMITS AND THRESHOLDS
    # =========================================================================
    "capital_loss_deduction_limit": 3_000,  # $1,500 for MFS
    "student_loan_interest_max": 2_500,
    "student_loan_interest_phaseout": {
        "single": (80_000, 95_000),
        "married_joint": (165_000, 195_000),
    },
    "health_savings_account": {
        "self_only": 4_150,
        "family": 8_300,
        "catch_up": 1_000,  # Age 55+
    },

    # Vehicle mileage rates (2024)
    "mileage_rates": {
        "business": 0.67,
        "medical_moving": 0.21,
        "charitable": 0.14,
    },

    # Home office simplified deduction
    "home_office_simplified_rate": 5.00,  # $5 per sq ft
    "home_office_simplified_max_sqft": 300,

    # Section 179 expensing
    "section_179_limit": 1_220_000,
    "section_179_phaseout_start": 3_050_000,

    # Estimated tax penalty safe harbor
    "estimated_tax_safe_harbor": {
        "current_year_pct": 0.90,      # 90% of current year tax
        "prior_year_pct": 1.00,        # 100% of prior year tax
        "prior_year_pct_high_income": 1.10,  # 110% if AGI > $150K ($75K MFS)
        "high_income_threshold": 150_000,
    },
}
