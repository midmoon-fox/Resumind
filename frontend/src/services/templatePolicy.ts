type TemplatePolicy = { id: string; version: string; stylePolicy: { colors: readonly string[] } };

export function latestTemplate<T extends TemplatePolicy>(templates: readonly T[], id: string): T | undefined {
  return templates.filter((template) => template.id === id).reduce<T | undefined>((latest, template) => {
    if (!latest) return template;
    const left = template.version.split('.').map(Number);
    const right = latest.version.split('.').map(Number);
    for (let i = 0; i < 3; i++) {
      if (left[i] !== right[i]) return left[i]! > right[i]! ? template : latest;
    }
    return latest;
  }, undefined);
}

export function supportsTheme(template: TemplatePolicy | undefined, color: string): boolean {
  return template?.stylePolicy.colors.includes(color) ?? false;
}
