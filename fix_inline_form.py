filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

# Find the leave-review section and replace it with the inline form
old_start = '      {# Leave review #}'
old_end = '      {# Reviews list #}'

idx_start = content.find(old_start)
idx_end = content.find(old_end)

if idx_start >= 0 and idx_end >= 0:
    old_section = content[idx_start:idx_end]
    
    new_section = '''      {# Leave review form #}
      {% if request.user.is_authenticated %}
      {% with level=request.user.get_level %}{% with city=request.user.get_city %}
      <div style="background:#fff;border-radius:16px;padding:16px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
          <span style="display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:50%;background:#000;color:#fff;font-size:14px;font-weight:bold;flex-shrink:0;">{{ request.user.first_name|first|upper|default:request.user.email|first|upper }}</span>
          <div>
            <p style="font-size:14px;font-weight:500;margin:0;">{{ request.user.first_name|default:request.user.email }}</p>
            <p style="font-size:12px;color:{{ level.color|default:'#999' }};margin:0;">{{ level.name }}{% if city %}, {{ city }}{% endif %}</p>
          </div>
        </div>
        <form id="review-form" onsubmit="submitReview(event)" style="display:flex;flex-direction:column;gap:16px;">
          {% csrf_token %}
          <div>
            <p style="font-size:14px;font-weight:500;margin:0 0 8px 0;">Магазин</p>
            <div class="shop-stars" id="shop-stars" style="display:flex;gap:4px;">
              <span class="star" data-value="5">&#9733;</span>
              <span class="star" data-value="4">&#9733;</span>
              <span class="star" data-value="3">&#9733;</span>
              <span class="star" data-value="2">&#9733;</span>
              <span class="star" data-value="1">&#9733;</span>
            </div>
            <input type="hidden" name="rating" id="rating-input" value="0">
            <textarea name="text" placeholder="Отзыв о магазине" rows="3" style="width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:8px;font-size:14px;resize:none;margin-top:8px;box-sizing:border-box;"></textarea>
          </div>
          <div>
            <p style="font-size:14px;font-weight:500;margin:0 0 8px 0;">Доставка</p>
            <div class="delivery-stars" id="delivery-stars" style="display:flex;gap:4px;">
              <span class="star" data-value="5">&#9733;</span>
              <span class="star" data-value="4">&#9733;</span>
              <span class="star" data-value="3">&#9733;</span>
              <span class="star" data-value="2">&#9733;</span>
              <span class="star" data-value="1">&#9733;</span>
            </div>
            <input type="hidden" name="delivery_rating" id="delivery-rating-input" value="">
            <select name="delivery_operator" style="width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:8px;font-size:14px;margin-top:8px;box-sizing:border-box;">
              <option value="">Укажите доставку</option>
              <option value="СДЭК">СДЭК</option>
              <option value="Почта России">Почта России</option>
              <option value="Boxberry">Boxberry</option>
              <option value="Яндекс Доставка">Яндекс Доставка</option>
            </select>
            <textarea name="delivery_text" placeholder="Отзыв о доставке" rows="3" style="width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:8px;font-size:14px;resize:none;margin-top:8px;box-sizing:border-box;"></textarea>
          </div>
          <div>
            <p style="font-size:14px;font-weight:500;margin:0 0 8px 0;">Комментарий</p>
            <textarea name="comment" placeholder="Расскажите о своих впечатлениях" rows="3" style="width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:8px;font-size:14px;resize:none;box-sizing:border-box;"></textarea>
          </div>
          <button type="submit" style="width:100%;padding:12px;background:#000;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:bold;cursor:pointer;">ОТПРАВИТЬ</button>
        </form>
      </div>
      {% endwith %}{% endwith %}
      {% else %}
      <div class="leave-review-bar" onclick="window.location.href='/login/?next=/reviews/'">
        <div class="leave-review-avatar" style="background:var(--black-4);color:var(--black-50);">?</div>
        <p class="leave-review-placeholder" style="margin:0;">Чтобы оставить отзыв, необходимо <a href="/login/?next=/reviews/">войти</a> или <a href="/register/?next=/reviews/">зарегистрироваться</a>.</p>
      </div>
      {% endif %}

      <style>
        .star { cursor:pointer; color:#ddd; font-size:28px; transition:color 0.15s; }
        .star.active, .star:hover { color:#f59e0b; }
      </style>

      <script>
      function initStars(containerId, inputId) {
        var container = document.getElementById(containerId);
        if (!container) return;
        var stars = container.querySelectorAll('.star');
        stars.forEach(function(star) {
          star.addEventListener('click', function() {
            var val = parseInt(this.dataset.value);
            document.getElementById(inputId).value = val;
            stars.forEach(function(s) {
              s.classList.toggle('active', parseInt(s.dataset.value) <= val);
            });
          });
          star.addEventListener('mouseenter', function() {
            var val = parseInt(this.dataset.value);
            stars.forEach(function(s) {
              s.classList.toggle('active', parseInt(s.dataset.value) <= val);
            });
          });
          star.addEventListener('mouseleave', function() {
            var current = parseInt(document.getElementById(inputId).value);
            stars.forEach(function(s) {
              s.classList.toggle('active', parseInt(s.dataset.value) <= current);
            });
          });
        });
      }
      initStars('shop-stars', 'rating-input');
      initStars('delivery-stars', 'delivery-rating-input');

      function submitReview(e) {
        e.preventDefault();
        var form = e.target;
        var formData = new FormData(form);
        fetch('{% url "pages:reviews_create" %}', {
          method: 'POST',
          body: formData,
          headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function(r) { return r.json(); }).then(function(data) {
          if (data.success) {
            fetch('/reviews/ajax/?' + new URLSearchParams(window.location.search), {
              headers: {'X-Requested-With': 'XMLHttpRequest'}
            }).then(function(r) { return r.text(); }).then(function(html) {
              document.getElementById('reviews-list').innerHTML = html;
              form.reset();
              document.querySelectorAll('.star').forEach(function(s) { s.classList.remove('active'); });
              document.getElementById('rating-input').value = '0';
              document.getElementById('delivery-rating-input').value = '';
            });
          } else {
            alert(Object.values(data.errors).join('\\n'));
          }
        });
      }
      </script>

      {# Reviews list #}
'''
    content = content[:idx_start] + new_section + content[idx_end:]
    
    # Remove the old modal and its styles/scripts
    content = content.replace('''      <style>
        #review-modal .modal-backdrop { position:fixed; inset:0; z-index:50; background:rgba(0,0,0,0.4); display:flex; align-items:flex-end; justify-content:center; }
        #review-modal .modal-box { background:#fff; border-radius:16px 16px 0 0; padding:16px; width:100%; max-width:480px; max-height:90vh; overflow:auto; }
        #review-modal .star { cursor:pointer; color:#ddd; font-size:24px; }
        #review-modal .star.active { color:#f59e0b; }
        #review-modal .shop-stars, #review-modal .delivery-stars { display:flex; gap:4px; }
        #review-modal textarea, #review-modal select { width:100%; padding:12px; border:1px solid #e5e7eb; border-radius:8px; font-size:14px; resize:none; }
        #review-modal .btn-submit { width:100%; padding:12px; background:#000; color:#fff; border:none; border-radius:8px; font-size:14px; cursor:pointer; }
        #review-modal .btn-cancel { width:100%; padding:12px; border:1px solid #e5e7eb; border-radius:8px; font-size:14px; cursor:pointer; background:#fff; }
        @media(min-width:768px) { #review-modal .modal-backdrop { align-items:center; } }
      </style>''', '')
    
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
