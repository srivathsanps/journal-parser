# Script to filter linked models from models_opened
import re

# Read the file
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the section where models_opened is assigned
old_code = """        info['models_opened'] = list(models)

        # === LINKED MODELS ==="""

new_code = """        # === LINKED MODELS ===
        # Extract linked RVT files FIRST to filter them out from opened models"""

# First replacement - move linked models extraction BEFORE models_opened assignment
content = content.replace(old_code, new_code)

# Now find where linked_models list is created and add filtering logic
old_linked_section = """        # Convert to list of dicts for better JSON structure
        info['linked_models'] = [{'type': link_type, 'name': name} for link_type, name in sorted(linked_files)]"""

new_linked_section = """        # Convert to list of dicts for better JSON structure
        info['linked_models'] = [{'type': link_type, 'name': name} for link_type, name in sorted(linked_files)]
        
        # Filter out linked models from models_opened - only show models actually opened for editing
        linked_model_names = {name for link_type, name in linked_files if link_type == 'RVT Link'}
        models_filtered = models - linked_model_names
        info['models_opened'] = list(models_filtered)
        
        # Update primary model if it was filtered out
        if info.get('primary_model') in linked_model_names and models_filtered:
            # Set primary to first non-linked model
            if model_matches:
                for pos, model_name in sorted(model_matches, key=lambda x: x[0]):
                    if model_name not in linked_model_names:
                        info['primary_model'] = model_name
                        break"""

content = content.replace(old_linked_section, new_linked_section)

# Write back
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Linked models filter added successfully!")
