with open(static/css/mobile_app.css, r) as f:
    c = f.read()

# Fix 1: Hide hamburger when mobile menu opens
c = c.replace(#header.open-menu .app-header-burger { display: flex !important; }, #header.open-menu .app-header-burger { display: none !important; })

# Fix 2: Fix search backdrop z-index to not block
c = c.replace(z-index: 180 !important;\n cursor: pointer;\n pointer-events: auto;\n animation: fadeInBackdrop 0.2s ease forwards;\n /*, z-index: 179 !important;\n cursor: pointer;\n pointer-events: auto;\n animation: fadeInBackdrop 0.2s ease forwards;\n /*)

# Fix 3: Increase padding for sub-menu items (line 551)
c = c.replace(padding: 8px 20px !important;\n font-size: 14px, padding: 12px 20px !important;\n font-size: 14px)

# Fix 4: Increase padding for contact block (line 592)
c = c.replace(padding: 10px 20px 14px !important;\n border-top, padding: 20px 20px 24px !important;\n border-top)

# Fix 5: Increase padding for auth block (line 615)
c = c.replace(padding: 10px 20px !important;\n z-index: 189, padding: 16px 20px !important;\n z-index: 189)

# Fix 6: Increase padding for city selector (line 572)
c = c.replace(padding: 16px 20px !important;\n border-top: 1px solid rgba(0,0,0,0.06), padding: 20px 20px !important;\n border-top: 1px solid rgba(0,0,0,0.06))

with open(static/css/mobile_app.css, w) as f:
    f.write(c)

print(All fixes applied successfully)
