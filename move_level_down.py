filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''        <p class="review-name">{% if review.user %}{{ review.user.first_name|default:review.user.email }}{% else %}{{ review.author_name|default:"Аноним" }}{% endif %}{% if review.user %}{% with level=review.user.get_level %}<span class="review-level" style="color:{{ level.color }};font-size:11px;font-weight:500;margin-left:6px;vertical-align:middle;">{{ level.name }}</span>{% endwith %}{% endif %}</p>
        <p class="review-date">{{ review.created_at|date:"d E Y" }}</p>'''

new = '''        <p class="review-name">{% if review.user %}{{ review.user.first_name|default:review.user.email }}{% else %}{{ review.author_name|default:"Аноним" }}{% endif %}</p>
        {% if review.user %}{% with level=review.user.get_level %}<p class="review-level" style="color:{{ level.color }};font-size:12px;font-weight:500;margin:2px 0 0 0;">{{ level.name }}</p>{% endwith %}{% endif %}
        <p class="review-date">{{ review.created_at|date:"d E Y" }}</p>'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
