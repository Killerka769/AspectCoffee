filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = "font-size:14px;font-weight:500;margin:4px 0 0 0;"
new = "font-size:16px;font-weight:500;margin:4px 0 0 0;"

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
