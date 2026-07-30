with open(static/css/mobile_app.css, r) as f:
    content = f.read()

# Fix 1: Hide hamburger when mobile menu opens
content = content.replace(
    #header.open-menu .app-header-burger { display: flex !important; },
    #header.open-menu .app-header-burger { display: none !important; }
)

# Fix 2: Fix search backdrop z-index to not block
content = content.replace(
    z-index: 180 !important;\n cursor: pointer;\n pointer-events: auto;\n animation: fadeInBackdrop 0.2s ease forwards;\n /*,
    z-index: 179 !important;\n cursor: pointer;\n pointer-events: auto;\n animation: fadeInBackdrop 0.2s ease forwards;\n /*
)

with open(static/css/mobile_app.css, w) as f:
    f.write(content)

print(Fixes applied)
