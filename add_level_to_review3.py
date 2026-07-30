filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''        <p class="review-name">{% if review.user %}{{ review.user.first_name|default:review.user.email }}{% else %}{{ review.author_name|default:"Аноним" }}{% endif %}</p>'''

new = '''        <p class="review-name">{% if review.user %}{{ review.user.first_name|default:review.user.email }}{% else %}{{ review.author_name|default:"Аноним" }}{% endif %}{% if review.user %}{% with level=review.user.get_level %}<span class="review-level" style="color:{{ level.color }};font-size:11px;font-weight:500;margin-left:6px;vertical-align:middle;">{{ level.name }}</span>{% endwith %}{% endif %}</p>'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('review-name')
    print(repr(content[max(0,idx-20):idx+200]))
