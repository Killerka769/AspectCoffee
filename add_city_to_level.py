filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''        {% if review.user %}{% with level=review.user.get_level %}<p class="review-level" style="color:{{ level.color }};font-size:12px;font-weight:500;margin:4px 0 0 0;">{{ level.name }}</p>{% endwith %}{% endif %}'''

new = '''        {% if review.user %}{% with level=review.user.get_level %}<p class="review-level" style="color:{{ level.color }};font-size:12px;font-weight:500;margin:4px 0 0 0;">{{ level.name }}{% if review.user.city %}, {{ review.user.city }}{% endif %}</p>{% endwith %}{% endif %}'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
