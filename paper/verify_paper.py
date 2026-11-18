import re

with open('paper/updatedpdf.tex') as f:
    text = f.read()

# 1. Brace and Dollar balance
open_b = 0
close_b = 0
open_dollar = 0
for line in text.split('\n'):
    stripped = line.strip()
    if stripped.startswith('%'):
        continue
    c_idx = line.find('%')
    if c_idx != -1 and not (c_idx > 0 and line[c_idx-1] == '\\'):
        line = line[:c_idx]
    open_b += line.count('{')
    close_b += line.count('}')
    i = 0
    while i < len(line):
        if line[i] == '$' and (i == 0 or line[i-1] != '\\'):
            open_dollar += 1
        i += 1

print(f'Braces: open={open_b}, close={close_b}, diff={open_b - close_b}')
print(f'Dollars: total={open_dollar}, odd={open_dollar % 2}')

# 2. AI Words Scan
ai_words = ['delve', 'testament', 'revolutionize', 'pivotal', 'beacon', 'seamlessly', 'harnessing', 'furthermore', 'moreover', 'in conclusion', 'tapestry', 'multifaceted', 'underscores', 'paramount', 'intricate', 'realm', 'landscape', 'paradigm', 'game-changer', 'spearhead', 'ubiquitous', 'bespoke']
found_ai = {w: text.lower().count(w) for w in ai_words if text.lower().count(w) > 0}
print('AI words found:', found_ai)

# 3. SQL Words Scan
sql_words = ['sqlite', 'sql', 'postgres']
found_sql = {w: text.lower().count(w) for w in sql_words if text.lower().count(w) > 0}
print('SQL words found:', found_sql)

# 4. Tables and Figures
tables = re.findall(r'\\begin\{(?:table|table\*)\}', text)
figures = re.findall(r'\\begin\{(?:figure|figure\*)\}', text)
print(f'Total Tables: {len(tables)}, Total Figures: {len(figures)}')

captions = re.findall(r'\\caption\{([^}]+)\}', text)
print(f'Total Captions: {len(captions)}')
for i, c in enumerate(captions, 1):
    print(f'  {i}. {c[:65]}...')

print(f'Total lines: {len(text.splitlines())}')

matches = list(re.finditer(r'\\begin\{(?:table|table\*)\}(.*?)\\end\{(?:table|table\*)\}', text, re.DOTALL))
print(f'Inspecting {len(matches)} tables:')
for i, m in enumerate(matches, 1):
    table_block = m.group(0)
    caption_m = re.search(r'\\caption\{([^}]+)\}', table_block)
    label_m = re.search(r'\\label\{([^}]+)\}', table_block)
    has_toprule = '\\toprule' in table_block
    has_midrule = '\\midrule' in table_block
    has_bottomrule = '\\bottomrule' in table_block
    lbl = label_m.group(1) if label_m else "None"
    cap = caption_m.group(1)[:45] if caption_m else "None"
    print(f'  Table {i:2d} | Label: {lbl:15s} | Rules: T={has_toprule} M={has_midrule} B={has_bottomrule} | Cap: {cap}...')

print("\n--- Detailed Table Width Diagnostics ---")
for i, m in enumerate(matches, 1):
    table_block = m.group(0)
    caption_m = re.search(r'\\caption\{([^}]+)\}', table_block)
    is_star = '\\begin{table*}' in table_block
    lines = table_block.split('\n')
    max_line = ""
    for l in lines:
        if '&' in l:
            clean = re.sub(r'\\[a-zA-Z]+', '', l)
            clean = re.sub(r'[{}$]', '', clean)
            if len(clean) > len(max_line):
                max_line = clean
    cap = caption_m.group(1)[:35] if caption_m else "None"
    print(f"Table {i:2d} (star={is_star}) | Max line len: {len(max_line):3d} chars | {cap}...")
    print(f"   Sample row: {max_line.strip()[:65]}")
