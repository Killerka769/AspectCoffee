filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '<input type="text" placeholder="Оставить отзыв" class="leave-review-placeholder" readonly>'
new = '<input type="text" placeholder="Оставить отзыв" class="leave-review-placeholder" readonly onclick="document.getElementById(\'review-modal\').style.display=\'flex\'">'

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
