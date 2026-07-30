filepath = '/app/apps/pages/templates/pages/reviews_list_partial.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''      <div class="review-avatar">
        {% if review.user and review.user.avatar %}
          <img src="{{ review.user.avatar.url }}" alt="" loading="lazy">
        {% else %}'''

new = '''      <div class="review-avatar" style="border-radius:50%;overflow:hidden;width:60px;height:60px;min-width:60px;background:#f5f5f7;position:relative;flex-shrink:0;">
        {% if review.user and review.user.avatar %}
          <img src="{{ review.user.avatar.url }}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:50%;position:absolute;top:0;left:0;">
        {% else %}'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('review-avatar')
    print(repr(content[max(0,idx-10):idx+200]))
