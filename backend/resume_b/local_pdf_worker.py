"""Private renderer entrypoint: stdin data, isolated browser, no requests or user scripts."""
import base64
import json
import os
import sys


def main():
    try:
        from playwright.sync_api import sync_playwright
        payload = sys.stdin.buffer.read(4 * 1024 * 1024 + 1)
        if len(payload) > 4 * 1024 * 1024:
            raise ValueError('render input exceeds bound')
        value = json.loads(payload)
        with sync_playwright() as playwright:
            options = {"headless": True, "timeout": 15000}
            if os.environ.get('RESUME_BROWSER_EXECUTABLE'):
                options['executable_path'] = os.environ['RESUME_BROWSER_EXECUTABLE']
            browser = playwright.chromium.launch(**options)
            try:
                context = browser.new_context(java_script_enabled=False, service_workers='block')
                context.route('**/*', lambda route: route.abort())
                page = context.new_page()
                page.set_default_timeout(15000)
                page.emulate_media(media='print')
                source = value['html']
                if 'class="sheet sidebar"' in source or 'class="sheet ribbon"' in source:
                    # Decorative templates own the whole A4 sheet. Keep text insets
                    # inside the layout instead of shrinking it with print margins.
                    print_css = '''
                      @page { size: A4; margin: 0; }
                      html, body { margin: 0; padding: 0; }
                      .sheet.sidebar { width: 210mm; min-height: 297mm; padding: 0;
                        border-bottom-width: 4mm; }
                      .sidebar-columns { display: flow-root; min-height: 279mm; }
                      .profile-sidebar { float: left; width: 30%; padding: 11mm 6mm; }
                      .profile-sidebar h2 { margin-inline: -6mm; padding-inline: 6mm; }
                      .sidebar-main { margin-left: 30%; min-height: 279mm;
                        padding: 6mm 7mm 10mm; }
                      .sheet.ribbon { width: 210mm; min-height: 297mm; padding: 10mm 0 14mm; }
                      .ribbon-masthead { padding: 0 15mm 6mm; }
                      .ribbon-content { margin: 0 13mm 0 15mm; }
                    '''
                    source = source.replace('</head>', '<style>' + print_css + '</style></head>', 1)
                page.set_content(source, wait_until='load')
                page.evaluate('() => document.fonts.ready')
                overflow = page.evaluate('() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1')
                if overflow:
                    raise ValueError('horizontal content overflow')
                data = page.pdf(format='A4', print_background=True, prefer_css_page_size=True)
            finally:
                browser.close()
        output = {"pdf": base64.b64encode(data).decode('ascii')}
    except Exception:
        output = {"error": "RENDER_UNAVAILABLE"}
    sys.stdout.buffer.write(json.dumps(output).encode('utf-8'))


if __name__ == '__main__':
    main()
