import os

path = '/app/apps/pages/templates/pages/reviews.html'
with open(path, 'r') as f:
    content = f.read()

letter_avatar = '<span style="display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:50%;background:#000;color:#fff;font-size:14px;font-weight:bold;flex-shrink:0;">{{ request.user.first_name|first|upper|default:request.user.email|first|upper }}</span>'

img_avatar = """{% if request.user.avatar %}<img src="{{ request.user.avatar.url }}" alt="" style="width:40px;height:40px;border-radius:50%;object-fit:cover;flex-shrink:0;">{% else %}<span style="display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:50%;background:#000;color:#fff;font-size:14px;font-weight:bold;flex-shrink:0;">{{ request.user.first_name|first|upper|default:request.user.email|first|upper }}</span>{% endif %}"""

count = content.count(letter_avatar)
print(f"Found {count} avatar spans to replace")

content = content.replace(letter_avatar, img_avatar)

with open(path, 'w') as f:
    f.write(content)
print("Done")
