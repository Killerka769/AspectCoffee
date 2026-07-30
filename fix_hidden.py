filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

# Fix modal: replace class="hidden" with style="display:none"
old = '<div id="review-modal" class="hidden fixed inset-0 z-50 bg-black/40 flex items-end md:items-center justify-center" style="display:none;"'
new = '<div id="review-modal" class="fixed inset-0 z-50 flex items-end md:items-center justify-center" style="display:none;background:rgba(0,0,0,0.4);"'

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND 1')

# Fix onclick to use display instead of class
old2 = "document.getElementById('review-modal').classList.remove('hidden')"
new2 = "document.getElementById('review-modal').style.display='flex'"

content = content.replace(old2, new2)

old3 = "this.classList.add('hidden')"
new3 = "this.style.display='none'"

content = content.replace(old3, new3)

# Fix all close buttons
old4 = "document.getElementById('review-modal').classList.add('hidden')"
new4 = "document.getElementById('review-modal').style.display='none'"

content = content.replace(old4, new4)

with open(filepath, 'w') as f:
    f.write(content)
print('DONE')
