import os

path = '/app/apps/pages/templates/pages/reviews.html'
with open(path, 'r') as f:
    content = f.read()

# Fix shop-stars block
old_shop = '''              <div id="shop-stars" style="display:flex;gap:4px;">
                <span class="star" data-value="5">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="3">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="5">&#9733;</span>
              </div>'''

new_shop = '''              <div id="shop-stars" style="display:flex;gap:4px;">
                <span class="star" data-value="1">&#9733;</span>
                <span class="star" data-value="2">&#9733;</span>
                <span class="star" data-value="3">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="5">&#9733;</span>
              </div>'''

# Fix delivery-stars block
old_delivery = '''              <div id="delivery-stars" style="display:flex;gap:4px;">
                <span class="star" data-value="5">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="3">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="5">&#9733;</span>
              </div>'''

new_delivery = '''              <div id="delivery-stars" style="display:flex;gap:4px;">
                <span class="star" data-value="1">&#9733;</span>
                <span class="star" data-value="2">&#9733;</span>
                <span class="star" data-value="3">&#9733;</span>
                <span class="star" data-value="4">&#9733;</span>
                <span class="star" data-value="5">&#9733;</span>
              </div>'''

count = 0
if old_shop in content:
    content = content.replace(old_shop, new_shop)
    count += 1
    print("Fixed shop-stars")
else:
    print("shop-stars block not found!")

if old_delivery in content:
    content = content.replace(old_delivery, new_delivery)
    count += 1
    print("Fixed delivery-stars")
else:
    print("delivery-stars block not found!")

if count > 0:
    with open(path, 'w') as f:
        f.write(content)
    print(f"Done - fixed {count} blocks")
else:
    print("Nothing to fix!")
