filepath = '/app/apps/users/models.py'
with open(filepath, 'r') as f:
    content = f.read()

# Change icon field from max_length=10 to max_length=500 for icons8 URLs
old = "    icon = models.CharField(\"Иконка\", max_length=10, blank=True, help_text=\"Эмодзи или текст\")"
new = "    icon = models.CharField(\"Иконка (URL)\", max_length=500, blank=True, help_text=\"URL иконки с icons8 или другой\" )"

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('UPDATED')
else:
    print('NOT FOUND')
    idx = content.find('icon =')
    if idx >= 0:
        print(repr(content[idx:idx+150]))
