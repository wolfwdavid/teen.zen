# Teen Zen PWA Setup Guide

## Files to add to your `frontend/public/` folder:

```
frontend/public/
├── manifest.json        ← NEW (copy from this package)
├── sw.js                ← NEW (copy from this package)
├── icons/
│   ├── icon-192.png     ← NEW
│   ├── icon-512.png     ← NEW
│   └── favicon.png      ← NEW (optional, replace existing favicon)
└── index.html           ← EDIT (add the lines below)
```

## Step 1: Copy files
Copy `manifest.json`, `sw.js`, and the `icons/` folder into:
```
/Users/admin/Documents/hello_world/teen.zen/chatbot-rag/frontend/public/
```

## Step 2: Edit `public/index.html`

Add these lines inside the `<head>` tag:

```html
<!-- PWA Meta Tags -->
<link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
<meta name="theme-color" content="#4f46e5" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="apple-mobile-web-app-title" content="Teen Zen" />
<link rel="apple-touch-icon" href="%PUBLIC_URL%/icons/icon-192.png" />

<!-- Viewport (make sure this exists) -->
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
```

Add this script just before `</body>`:

```html
<!-- Service Worker Registration -->
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('%PUBLIC_URL%/sw.js')
        .then(reg => console.log('✅ SW registered:', reg.scope))
        .catch(err => console.log('❌ SW failed:', err));
    });
  }
</script>
```

## Step 3: Build & Deploy

```bash
cd frontend
npm run build
```

Then push to GitHub Pages as usual.

## Step 4: Install on Phone

### iPhone (Safari):
1. Open https://wolfwdavid.github.io/teen.zen/ in Safari
2. Tap the Share button (box with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Tap "Add"

### Android (Chrome):
1. Open https://wolfwdavid.github.io/teen.zen/ in Chrome
2. Tap the 3-dot menu
3. Tap "Install app" or "Add to Home Screen"
4. Tap "Install"

The app will appear on your home screen with the 禅 icon and launch in full-screen mode (no browser chrome).
