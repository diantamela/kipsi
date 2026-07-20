import os

path = r'c:\odoo\odoo18\server\odoo\addons\web\static\src\views\kanban\kanban_arch_parser.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace my previous patch with a new one that prints the keys
old = 'if (!models[modelName].fields[node.getAttribute("name")]) { console.log("KANBAN CRASH DEBUG: model=", modelName, " missing field=", node.getAttribute("name")); }'
new = 'if (!models[modelName].fields[node.getAttribute("name")]) { console.log("KANBAN CRASH DEBUG: model=", modelName, " missing field=", node.getAttribute("name"), "available fields=", Object.keys(models[modelName].fields)); }'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated patch successfully!')
else:
    print('Previous patch string not found')
