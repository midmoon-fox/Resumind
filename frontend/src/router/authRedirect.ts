export function authRedirect(value: unknown): string | undefined {
  if (
    typeof value === 'string' &&
    value.startsWith('/') &&
    !value.startsWith('//') &&
    !value.includes('\\') &&
    !/^\/(?:login|register)?(?:[/?#]|$)/i.test(value)
  ) {
    return value;
  }
}
