filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''.review-avatar {
  width: 60px;
  height: 60px;
  min-width: 60px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  background: #f5f5f7;
}
@media(min-width:758px){ .review-avatar { width: 48px; height: 48px; } }

.review-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  display: block;
}

.review-avatar-letter {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 1rem;
  background: rgba(0,0,0,0.04);
  border-radius: 50%;
}'''

new = '''.review-avatar {
  width: 60px;
  height: 60px;
  min-width: 60px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  flex-shrink: 0;
  background: #f5f5f7;
}
@media(min-width:758px){ .review-avatar { width: 48px; height: 48px; } }

.review-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  position: absolute;
  top: 0;
  left: 0;
}

.review-avatar-letter {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 1rem;
  background: rgba(0,0,0,0.04);
  border-radius: 50%;
}'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
    idx = content.find('.review-avatar')
    print('Found at:', idx)
    print(content[idx:idx+600])
