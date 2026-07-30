filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

# Add city field after phone field
old = '    phone = models.CharField('
new = '''    city = models.CharField("Город", max_length=200, blank=True)
    phone = models.CharField('''

if old in content and 'city = models.CharField' not in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND or ALREADY EXISTS')
