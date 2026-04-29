"""CipherTax Tax Module — US federal tax calculation and filing assistance.

Provides tax constants, calculation engine, form data models,
and optimization tools for comprehensive US tax filing.
"""

from ciphertax.tax.calculator import TaxCalculator
from ciphertax.tax.forms import FilingStatus

__all__ = ["TaxCalculator", "FilingStatus"]
