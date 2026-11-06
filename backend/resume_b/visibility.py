"""One visibility rule shared by rendering and export completeness checks."""
def rich_has_content(node):
    return bool(node.get('text', '').strip()) or any(rich_has_content(child) for child in node.get('content', []))

def item_has_content(item):
    return bool(item['title'].strip() or item['subtitle'].strip() or rich_has_content(item['description']))

def section_has_content(section, profile):
    if not section['visible']:
        return False
    if section['type'] == 'EDUCATION':
        return any(any(str(entry.get(key) or '').strip() for key in ('school','major','degree')) for entry in profile['education'])
    if section['type'] == 'SKILLS':
        return any(skill.strip() for skill in profile['skills'])
    if section['type'] == 'CHARTS':
        return any((datum.get('label') or '').strip() for datum in (section.get('chartData') or []))
    if section['type'] == 'SOCIAL_LINKS':
        return any((link.get('platform') or '').strip() for link in (section.get('links') or []))
    if section['type'] == 'TEXT':
        return rich_has_content(section.get('text') or {})
    return any(item_has_content(item) for item in section['items'])
