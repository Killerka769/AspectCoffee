filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''      <div class="review-meta">
        <p class="review-name">{% if review.user %}{{ review.user.first_name|default:review.user.email }}{% else %}{{ review.author_name|default:"Аноним" }}{% endif %}</p>
        {% if review.user %}{% with level=review.user.get_level %}<p class="review-level" style="color:{{ level.color }};font-size:12px;font-weight:500;margin:2px 0 0 0;width:100%;">{{ level.name }}</p>{% endwith %}{% endif %}
        <p class="review-date">{{ review.created_at|date:"d E Y" }}</p>
      </div>'''

new = '''      <div class="review-meta">
        <div style="display:flex;justify-content:space-between;align-items:baseline;width:100%;">
          <p class="review-name" style="margin:0;">{% if review.user %}{{ review.user.first_name|default:review.user.email }}{% else %}{{ review.author_name|default:"Аноним" }}{% endif %}</p>
          <p class="review-date" style="margin:0;white-space:nowrap;">{{ review.created_at|date:"d E Y" }}</p>
        </div>
        {% if review.user %}{% with level=review.user.get_level %}<p class="review-level" style="color:{{ level.color }};font-size:12px;font-weight:500;margin:4px 0 0 0;">{{ level.name }}</p>{% endwith %}{% endif %}
      </div>'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('review-meta')
    print(repr(content[max(0,idx-10):idx+500]))
