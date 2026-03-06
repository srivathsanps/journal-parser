# Fix indentation error
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 1677 - remove extra indentation
lines[1676] = '            timeline.append({\n'  # Line 1677 (0-indexed as 1676)

with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Indentation fixed!")
