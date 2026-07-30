with open(static/css/mobile_app.css, r) as f:
    c = f.read()
c = c.replace(#header.open-menu .app-header-burger { display: flex !important; }, #header.open-menu .app-header-burger { display: none !important; })
c = c.replace(z-index: 180 !important;, z-index: 179 !important;)
with open(static/css/mobile_app.css, w) as f:
    f.write(c)
print(Done)
