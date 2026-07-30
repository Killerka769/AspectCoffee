filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('direction:rtl;', '')

with open(filepath, 'w') as f:
    f.write(content)
print('OK')
