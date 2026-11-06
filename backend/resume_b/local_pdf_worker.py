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
                page.set_content(value['html'], wait_until='load')
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
