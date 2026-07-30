filepath = '/app/apps/catalog/models.py'
with open(filepath, 'r') as f:
    content = f.read()

old = '''    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="reviews", verbose_name="Товар",
    )'''
new = '''    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="reviews", verbose_name="Товар",
    )'''

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
