interface CreateDraft {
  title: string;
  direction: string;
  profile: { name: string; email: string; phone: string };
}
export function validateCreateStep(step: number, draft: CreateDraft): Record<string, string> {
  const errors: Record<string, string> = {};
  if (step === 0) {
    if (!draft.title.trim()) errors.title = '请填写简历名称';
    if (!draft.direction.trim()) errors.direction = '请填写求职方向';
  }
  if (step === 1) {
    if (!draft.profile.name.trim()) errors.name = '请填写姓名';
    if (!draft.direction.trim()) errors.direction = '请填写求职方向';
    const email = draft.profile.email.trim(),
      phone = draft.profile.phone.trim();
    if (!email && !phone) {
      errors.email = '邮箱和手机号至少填写一项';
      errors.phone = '邮箱和手机号至少填写一项';
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      errors.email = '请填写有效的邮箱，例如 name@example.com';
    if (phone && !/^\+?[0-9 ()-]{6,30}$/.test(phone)) errors.phone = '请填写有效的联系电话';
  }
  return errors;
}
