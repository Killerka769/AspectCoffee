filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

old = '''.review-avatar-letter {
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

new = '''.review-avatar-letter {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
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
