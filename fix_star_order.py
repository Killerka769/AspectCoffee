filepath = '/app/apps/pages/templates/pages/reviews.html'
with open(filepath, 'r') as f:
    content = f.read()

# Fix star order: 5,4,3,2,1 -> 1,2,3,4,5
for old_block in ['<span class="star" data-value="5">&#9733;</span>\n                <span class="star" data-value="4">&#9733;</span>\n                <span class="star" data-value="3">&#9733;</span>\n                <span class="star" data-value="2">&#9733;</span>\n                <span class="star" data-value="1">&#9733;</span>',
                  '<span class="star" data-value="5">&#9733;</span>\n              <span class="star" data-value="4">&#9733;</span>\n              <span class="star" data-value="3">&#9733;</span>\n              <span class="star" data-value="2">&#9733;</span>\n              <span class="star" data-value="1">&#9733;</span>']:
    new_block = old_block.replace('data-value="5"', 'data-value="1"').replace('data-value="4"', 'data-value="2"').replace('data-value="3"', 'data-value="3"').replace('data-value="2"', 'data-value="4"').replace('data-value="1"', 'data-value="5"')
    content = content.replace(old_block, new_block)

# Also try single-line replacements
content = content.replace('''                <span class="star" data-value="5">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="3">&#9733;</span>
                <span class="star" data-value="2">&#9733;</span>
                <span class="star" data-value="1">&#9733;</span>''',
'''                <span class="star" data-value="1">&#9733;</span>
                <span class="star" data-value="2">&#9733;</span>
                <span class="star" data-value="3">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="5">&#9733;</span>''')

with open(filepath, 'w') as f:
    f.write(content)
print('OK')
