"""Venture SDK: a business as a validated object."""

```python
from venture_sdk import load
v = load(".openbot/ventures/media-api/venture.yaml")   # raises VentureError if unworkable
v.gross_margin_per_unit, v.payback_months              # derived, not asserted
```

```sh
python -m venture_sdk validate .openbot/ventures       # every venture, one line each
```

The loader refuses: a price of zero, a COGS of zero (guessed economics), an `auto_spend_usd`
above zero before revenue (D4), a kill criterion with no number in it, a channel-less venture
(nobody will find it), an unknown status, and a plan that cannot reach the declared target margin.
