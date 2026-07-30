filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''      {# Leave review #}
      {% if request.user.is_authenticated %}
      <div class="leave-review-bar" onclick="document.getElementById('review-modal').classList.remove('hidden')">
        {% with level=request.user.get_level %}{% with city=request.user.get_city %}
        <div class="mr-2.5">
          <span class="flex items-center justify-center w-10 h-10 rounded-full bg-black text-white text-sm font-bold flex-shrink-0">{{ request.user.first_name|first|upper|default:request.user.email|first|upper }}</span>
        </div>
        <div>
          <p class="text-sm font-medium">{{ request.user.first_name|default:request.user.email }}</p>
          <p class="text-xs text-gray-500" style="color:{{ level.color|default:'#999' }};">{{ level.name }}{% if city %}, {{ city }}{% endif %}</p>
        </div>
        {% endwith %}{% endwith %}
      </div>'''

new = '''      {# Leave review #}
      {% if request.user.is_authenticated %}
      <div class="leave-review-bar" onclick="document.getElementById('review-modal').classList.remove('hidden')" style="cursor:pointer;">
        <div class="leave-review-avatar" style="background:#000;color:#fff;">{{ request.user.first_name|first|upper|default:request.user.email|first|upper }}</div>
        <input type="text" placeholder="Оставить отзыв" class="leave-review-placeholder" readonly>
      </div>'''

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
