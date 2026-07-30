import os

path = '/app/apps/pages/templates/pages/reviews.html'
with open(path, 'r') as f:
    content = f.read()

# 1. Add moderation notice div right after the form wrapper closing div
old_after_form = """      {% endwith %}{% endwith %}
      {% else %}
      <div class="leave-review-bar" onclick="window.location.href='/login/?next=/reviews/'">"""

new_after_form = """      {% endwith %}{% endwith %}
      <div id="moderation-notice" style="display:none;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px;margin-bottom:16px;text-align:center;">
        <p style="margin:0;font-size:14px;font-weight:500;color:#166534;">Спасибо! Ваш отзыв отправлен на модерацию.</p>
      </div>
      {% else %}
      <div class="leave-review-bar" onclick="window.location.href='/login/?next=/reviews/'">"""

count = 0
if old_after_form in content:
    content = content.replace(old_after_form, new_after_form)
    count += 1
    print("Added moderation notice div")
else:
    print("ERROR: moderation notice insertion point not found")

# 2. Update submitReview JS to show the notice instead of reloading reviews
old_js = """          if (data.success) {
            fetch('/reviews/ajax/?' + new URLSearchParams(window.location.search), {
              headers: {'X-Requested-With': 'XMLHttpRequest'}
            }).then(function(r) { return r.text(); }).then(function(html) {
              document.getElementById('reviews-list').innerHTML = html;
              form.reset();
              document.querySelectorAll('.star').forEach(function(s) { s.classList.remove('active'); });
              document.getElementById('rating-input').value = '0';
              document.getElementById('delivery-rating-input').value = '';
              document.getElementById('review-form-wrap').style.display = 'none';
              document.getElementById('review-bar').style.display = 'flex';
            });"""

new_js = """          if (data.success) {
              form.reset();
              document.querySelectorAll('.star').forEach(function(s) { s.classList.remove('active'); });
              document.getElementById('rating-input').value = '0';
              document.getElementById('delivery-rating-input').value = '';
              document.getElementById('review-form-wrap').style.display = 'none';
              document.getElementById('review-bar').style.display = 'none';
              document.getElementById('moderation-notice').style.display = 'block';
              setTimeout(function() {
                document.getElementById('moderation-notice').style.display = 'none';
                document.getElementById('review-bar').style.display = 'flex';
              }, 4000);"""

if old_js in content:
    content = content.replace(old_js, new_js)
    count += 1
    print("Updated submitReview JS")
else:
    print("ERROR: JS block not found")

if count > 0:
    with open(path, 'w') as f:
        f.write(content)
    print(f"Done - {count} changes")
else:
    print("Nothing changed!")
