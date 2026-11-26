// ABOUTME: Fills {name} placeholders in a dictionary string, so translations can place
// ABOUTME: dynamic values (a message, a title) wherever their grammar needs them.

export function fillTemplate(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (placeholder, name: string) => values[name] ?? placeholder);
}
