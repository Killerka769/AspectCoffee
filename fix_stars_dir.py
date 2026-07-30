filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

old = 'style="display:flex;gap:4px;">'
new = 'style="display:flex;gap:4px;direction:rtl;">'

content = content.replace(old, new)

with open(filepath, 'w') as f:
    f.write(content)
print('OK')
