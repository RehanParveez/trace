from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP

_ONES = [
  "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
  "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
  "Seventeen", "Eighteen", "Nineteen",
]
_TENS = [
  "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety",
]

def _two_digits(n: int) -> str:
  if n < 20:
    return _ONES[n]
  tens, ones = divmod(n, 10)
  return (_TENS[tens] + (" " + _ONES[ones] if ones else "")).strip()

def _three_digits(n: int) -> str:
  hundreds, rest = divmod(n, 100)
  parts = []
  if hundreds:
    parts.append(f"{_ONES[hundreds]} Hundred")
  if rest:
    parts.append(_two_digits(rest))
  return " ".join(parts)


def _integer_to_words(n: int) -> str:
  if n == 0:
    return "Zero"

  crore, n = divmod(n, 10_000_000)
  lakh, n = divmod(n, 100_000)
  thousand, n = divmod(n, 1_000)
  hundred = n

  parts = []
  if crore:
    parts.append(f"{_integer_to_words(crore)} Crore")
  if lakh:
    parts.append(f"{_two_digits(lakh) if lakh < 100 else _three_digits(lakh)} Lakh")
  if thousand:
    parts.append(f"{_two_digits(thousand) if thousand < 100 else _three_digits(thousand)} Thousand")
  if hundred:
    parts.append(_three_digits(hundred))
  return " ".join(parts)

def rupees_in_words(amount: Decimal, currency_label: str = "Pakistani") -> str:
  rounded = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
  return f"{currency_label} {_integer_to_words(int(rounded))} Rupees Only."