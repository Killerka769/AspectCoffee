import os

path = '/app/apps/pages/templates/pages/reviews.html'
with open(path, 'r') as f:
    content = f.read()

old = '<div style="background:#fff;border-radius:16px;overflow:hidden;">'
new = '<div style="background:#fff;border-radius:16px;overflow:hidden;margin-bottom:16px;">'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - added margin-bottom:16px to form wrapper")
else:
    print("Block not found!")
