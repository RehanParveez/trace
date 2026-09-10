export function formatBudgetAmount(value: number | string | null, currency = "PKR"): string {
  if (value === null) {
    return "—";
  }

  const numeric = typeof value === "string" ? Number(value) : value;

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(numeric);
}

export function sumCategoryAllocations(
  categories: { allocated_amount: number | string }[],
): number {
  return categories.reduce((total, category) => {
    const amount = Number(category.allocated_amount);
    return total + (Number.isFinite(amount) ? amount : 0);
  }, 0);
}