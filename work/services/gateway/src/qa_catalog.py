"""First-party owned sample catalog. Never load a caller-supplied module or command."""

SOURCE = '''def discounted_total(unit_cents, quantity, discount_percent=0):
    """Integer-cent invoice example.

    >>> discounted_total(1250, 2, 10)
    2250
    >>> discounted_total(999, 1, 100)
    0
    """
    if any(type(value) is not int for value in (unit_cents, quantity, discount_percent)):
        raise TypeError("integer minor units required")
    if unit_cents < 0 or quantity < 0 or not 0 <= discount_percent <= 100:
        raise ValueError("amount, quantity or discount out of range")
    return unit_cents * quantity * (100 - discount_percent) // 100
'''
FIXTURES = {
    "invoice-good-v1": SOURCE,
    "invoice-discount-defect-v1": SOURCE.replace("(100 - discount_percent)", "100"),
    "invoice-docs-defect-v1": SOURCE.replace("    2250\n", "    2500\n"),
}
CASE_NAMES = (
    "OwnedTests.test_discount",
    "OwnedTests.test_free",
    "OwnedTests.test_no_discount",
    "OwnedTests.test_reject_negative",
    "OwnedTests.test_reject_float",
    "OwnedTests.test_reject_bool",
    "owned_example",
)
