# Fix all indentation in the crash detection section
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 1678-1683 (0-indexed as 1677-1682)
lines[1677] = '                \'line\': line_num,\n'
lines[1678] = '                \'timestamp\': timestamp,\n'
lines[1679] = '                \'type\': \'crash\',\n'
lines[1680] = '                \'description\': \'Fatal Error\',\n'
lines[1681] = '                \'text\': m.group(0)[:100]\n'
lines[1682] = '            })\n'

with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("All indentation fixed!")
