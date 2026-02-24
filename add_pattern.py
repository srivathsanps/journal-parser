# Quick fix to add BIM 360 pattern
import re

# Read the file
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the location to insert
pattern_to_find = "        # Pattern 1: Cloud models (BIM 360/ACC) - most reliable"

# New pattern to insert
new_pattern = """        # Pattern 0: BIM 360/ACC cloud paths - extract the actual model name
        for m in re.finditer(r'BIM 360://[^/]+/([^"]+\\.rvt)', content, re.IGNORECASE):
            model_name = m.group(1)
            if model_name and not self._is_temp_file(model_name):
                models.add(model_name)
                model_matches.append((m.start(), model_name))
        
"""

# Replace
content = content.replace(pattern_to_find, new_pattern + pattern_to_find)

# Write back
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("BIM 360 pattern added successfully!")
