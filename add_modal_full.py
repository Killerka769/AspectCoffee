filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''      {# Leave review #}
      {% if request.user.is_authenticated %}
      <div class="leave-review-bar">
        <div class="leave-review-avatar" style="background:#000;color:#fff;">
          {{ request.user.first_name|first|upper|default:request.user.email|first|upper }}
        </div>
        <input type="text" placeholder="Оставить отзыв" class="leave-review-placeholder" readonly>
      </div>
      {% else %}
      <div class="leave-review-bar">
        <div class="leave-review-avatar" style="background:var(--black-4);color:var(--black-50);">?</div>
        <p class="leave-review-placeholder" style="margin:0;">Чтобы оставить отзыв, необходимо <a href="/login/?next=/reviews/">войти</a> или <a href="/register/?next=/reviews/">зарегистрироваться</a>.</p>
      </div>
      {% endif %}'''

new = '''      {# Leave review #}
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
      </div>
      {% else %}
      <div class="leave-review-bar" onclick="window.location.href='/login/?next=/reviews/'">
        <div class="leave-review-avatar" style="background:var(--black-4);color:var(--black-50);">?</div>
        <p class="leave-review-placeholder" style="margin:0;">Чтобы оставить отзыв, необходимо <a href="/login/?next=/reviews/">войти</a> или <a href="/register/?next=/reviews/">зарегистрироваться</a>.</p>
      </div>
      {% endif %}

      {# Review modal #}
      <div id="review-modal" class="hidden fixed inset-0 z-50 bg-black/40 flex items-end md:items-center justify-center" style="display:none;" onclick="if(event.target===this)this.classList.add('hidden')">
        <div class="w-full bg-white rounded-t-2xl md:rounded-2xl p-4 md:p-6 max-w-lg max-h-[90vh] overflow-auto" onclick="event.stopPropagation()">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-2xl font-bold md:hidden">Оставить отзыв</h2>
            <button type="button" onclick="document.getElementById('review-modal').classList.add('hidden')" class="ml-auto text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          
          {% with level=request.user.get_level %}{% with city=request.user.get_city %}
          <div class="flex items-center gap-2.5 mb-4">
            <span class="flex items-center justify-center w-10 h-10 rounded-full bg-black text-white text-sm font-bold flex-shrink-0">{{ request.user.first_name|first|upper|default:request.user.email|first|upper }}</span>
            <div>
              <p class="text-sm font-medium">{{ request.user.first_name|default:request.user.email }}</p>
              <p class="text-xs" style="color:{{ level.color|default:'#999' }};">{{ level.name }}{% if city %}, {{ city }}{% endif %}</p>
            </div>
          </div>
          {% endwith %}{% endwith %}

          <form id="review-form" method="post" action="{% url 'pages:reviews_create' %}">
            {% csrf_token %}
            <div class="space-y-4">
              <div>
                <p class="text-sm font-medium mb-1">Магазин</p>
                <div class="flex gap-1 text-2xl" id="shop-stars" data-input="rating">
                  <span class="cursor-pointer star" data-value="1">☆</span>
                  <span class="cursor-pointer star" data-value="2">☆</span>
                  <span class="cursor-pointer star" data-value="3">☆</span>
                  <span class="cursor-pointer star" data-value="4">☆</span>
                  <span class="cursor-pointer star" data-value="5">☆</span>
                </div>
                <input type="hidden" name="rating" id="rating-input" value="0">
                <textarea name="text" placeholder="Отзыв о магазине" rows="3" class="w-full mt-2 p-3 border border-gray-200 rounded-lg resize-none text-sm"></textarea>
              </div>

              <div>
                <p class="text-sm font-medium mb-1">Доставка</p>
                <div class="flex gap-1 text-2xl" id="delivery-stars" data-input="delivery_rating">
                  <span class="cursor-pointer star" data-value="1">☆</span>
                  <span class="cursor-pointer star" data-value="2">☆</span>
                  <span class="cursor-pointer star" data-value="3">☆</span>
                  <span class="cursor-pointer star" data-value="4">☆</span>
                  <span class="cursor-pointer star" data-value="5">☆</span>
                </div>
                <input type="hidden" name="delivery_rating" id="delivery-rating-input" value="">
                <select name="delivery_operator" class="w-full mt-2 p-3 border border-gray-200 rounded-lg text-sm">
                  <option value="">Укажите доставку</option>
                  <option value="СДЭК">СДЭК</option>
                  <option value="Почта России">Почта России</option>
                  <option value="Boxberry">Boxberry</option>
                  <option value="Яндекс Доставка">Яндекс Доставка</option>
                </select>
                <textarea name="delivery_text" placeholder="Отзыв о доставке" rows="3" class="w-full mt-2 p-3 border border-gray-200 rounded-lg resize-none text-sm"></textarea>
              </div>

              <div>
                <p class="text-sm font-medium mb-1">Комментарий</p>
                <textarea name="comment" placeholder="Расскажите о своих впечатлениях" rows="3" class="w-full p-3 border border-gray-200 rounded-lg resize-none text-sm"></textarea>
              </div>
            </div>

            <div class="mt-4 space-y-2">
              <button type="submit" class="w-full py-3 bg-black text-white rounded-lg font-medium text-sm hover:bg-gray-800">Отправить</button>
              <button type="button" onclick="document.getElementById('review-modal').classList.add('hidden')" class="w-full py-3 border border-gray-200 rounded-lg font-medium text-sm hover:bg-gray-50 md:hidden">Отменить</button>
            </div>
          </form>
        </div>
      </div>

      <style>
        .star.active { color: #f59e0b; }
        .star:hover, .star:hover ~ .star { color: #f59e0b; }
        #shop-stars, #delivery-stars { direction: rtl; }
        #shop-stars .star, #delivery-stars .star { color: #ddd; }
        #shop-stars .star.active, #shop-stars .star.active ~ .star,
        #delivery-stars .star.active, #delivery-stars .star.active ~ .star { color: #f59e0b; }
      </style>

      <script>
      document.querySelectorAll('#shop-stars .star, #delivery-stars .star').forEach(function(star) {
        star.addEventListener('click', function() {
          var container = this.parentElement;
          var value = parseInt(this.dataset.value);
          var inputId = container.dataset.input;
          document.getElementById(inputId + '-input').value = value;
          container.querySelectorAll('.star').forEach(function(s) {
            s.classList.toggle('active', parseInt(s.dataset.value) <= value);
          });
        });
        star.addEventListener('mouseenter', function() {
          var value = parseInt(this.dataset.value);
          this.parentElement.querySelectorAll('.star').forEach(function(s) {
            s.classList.toggle('active', parseInt(s.dataset.value) <= value);
          });
        });
        star.addEventListener('mouseleave', function() {
          var container = this.parentElement;
          var inputId = container.dataset.input;
          var currentVal = parseInt(document.getElementById(inputId + '-input').value);
          container.querySelectorAll('.star').forEach(function(s) {
            s.classList.toggle('active', parseInt(s.dataset.value) <= currentVal);
          });
        });
      });

      document.getElementById('review-form').addEventListener('submit', function(e) {
        e.preventDefault();
        var form = this;
        var formData = new FormData(form);
        fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function(r) { return r.json(); }).then(function(data) {
          if (data.success) {
            document.getElementById('review-modal').classList.add('hidden');
            form.reset();
            document.querySelectorAll('#shop-stars .star, #delivery-stars .star').forEach(function(s) { s.classList.remove('active'); });
            document.getElementById('rating-input').value = '0';
            document.getElementById('delivery-rating-input').value = '';
            fetch('/reviews/ajax/?' + new URLSearchParams(window.location.search), {
              headers: {'X-Requested-With': 'XMLHttpRequest'}
            }).then(function(r) { return r.text(); }).then(function(html) {
              document.getElementById('reviews-list').innerHTML = html;
            });
          } else {
            alert(Object.values(data.errors).join('\\n'));
          }
        });
      });
      </script>'''

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('Leave review')
    if idx >= 0:
        print(repr(content[idx:idx+300]))
    else:
        print('Not found at all')
