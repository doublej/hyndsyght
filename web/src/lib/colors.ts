/** Category colour follows the category's position in the rules file, never its rank,
 *  so a category keeps its colour when the day's totals reorder. Past eight → muted. */
export function categoryColor(category: string, order: string[]): string {
  const slot = order.indexOf(category);
  return slot >= 0 && slot < 8 ? `var(--series-${slot + 1})` : "var(--muted)";
}
