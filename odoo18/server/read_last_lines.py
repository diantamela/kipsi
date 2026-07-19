with open('odoo.log', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    last_chunk = content[-200000:]
    import re
    for m in re.finditer(r'(FAIL:|ERROR:|AssertionError)', last_chunk):
        start = max(0, m.start() - 500)
        end = min(len(last_chunk), m.end() + 1500)
        print("MATCH FOUND:")
        print(last_chunk[start:end])
        print("="*80)
