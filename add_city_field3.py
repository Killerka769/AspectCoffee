filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

old = '    email = models.EmailField("Email", unique=True)\n    phone = models.CharField('
new = '    email = models.EmailField("Email", unique=True)\n    city = models.CharField("Город", max_length=200, blank=True)\n    phone = models.CharField('

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
