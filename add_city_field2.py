filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

# Add city after email
old = '''    email = models.EmailField("Email", unique=True)
    phone = models.CharField('''
new = '''    email = models.EmailField("Email", unique=True)
    city = models.CharField("Город", max_length=200, blank=True)
    phone = models.CharField('''

if old in content and 'city = models.CharField("Город"' not in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND or ALREADY EXISTS')
