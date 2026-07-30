filepath = '/app/apps/pages/urls.py'
with open(filepath, 'r') as f:
    content = f.read()

old = '    path("reviews/ajax/", views.reviews_ajax, name="reviews_ajax"),\n'
new = '    path("reviews/ajax/", views.reviews_ajax, name="reviews_ajax"),\n    path("reviews/create/", views.reviews_create, name="reviews_create"),\n'

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('reviews/ajax')
    if idx >= 0:
        print(repr(content[idx:idx+100]))
