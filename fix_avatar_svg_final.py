filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''      <div class="review-avatar">
        {% if review.user and review.user.avatar %}
          <img src="{{ review.user.avatar.url }}" alt="" loading="lazy">
        {% endif %}
        <div class="review-avatar-letter">
          {% if review.user %}{{ review.user.first_name|first|default:review.user.email|first|upper }}{% else %}{{ review.author_name|first|default:"?"|upper }}{% endif %}
        </div>
      </div>'''

new = '''      <div class="review-avatar">
        {% if review.user and review.user.avatar %}
          <img src="{{ review.user.avatar.url }}" alt="" loading="lazy">
        {% else %}
        <div class="review-avatar-letter">
          <svg height="100%" preserveAspectRatio="xMinYMid meet" viewBox="0 0 500 75" width="100%" xmlns="http://www.w3.org/2000/svg">
            <text dominant-baseline="central" fill="black" font-size="240" text-anchor="middle" x="50%" y="50%">{% if review.user %}{{ review.user.first_name|first|default:review.user.email|first|upper }}{% else %}{{ review.author_name|first|default:"?"|upper }}{% endif %}</text>
          </svg>
        </div>
        {% endif %}
      </div>'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('review-avatar')
    print(content[max(0,idx-50):idx+300])
