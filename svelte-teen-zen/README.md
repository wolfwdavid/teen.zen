# Teen.zen Website - Svelte Version

A modern, responsive landing page for the Teen Zen mental health app built with Svelte.

## Features

- 🎨 Modern, gradient design
- 📱 Fully responsive (mobile, tablet, desktop)
- ⚡ Lightning-fast performance with Svelte
- 🚀 Optimized for GitHub Pages deployment
- ♿ Accessible and SEO-friendly

## Local Development

### Prerequisites
- Node.js 18+ installed

### Setup

1. Navigate to this directory:
```bash
cd teen-zen-website
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

The site will be available at `http://localhost:5173`

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` folder.

## Deploying to GitHub Pages

### Option 1: Manual Deployment

1. Build the project:
```bash
npm run build
```

2. Copy the `dist` folder contents to your repository's `docs` folder:
```bash
# From the project root
Remove-Item -Recurse -Force docs -ErrorAction SilentlyContinue
Copy-Item -Path "teen-zen-website/dist" -Destination "docs" -Recurse
```

3. Commit and push:
```bash
git add docs/
git commit -m "Deploy Svelte website to GitHub Pages"
git push origin master
```

4. Configure GitHub Pages:
   - Go to repository Settings → Pages
   - Source: `master` branch
   - Folder: `/docs`
   - Save

### Option 2: Automated with GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ master ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-js-version: '18'
      
      - name: Install dependencies
        working-directory: ./teen-zen-website
        run: npm ci
      
      - name: Build
        working-directory: ./teen-zen-website
        run: npm run build
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./teen-zen-website/dist
```

## Project Structure

```
teen-zen-website/
├── src/
│   ├── lib/
│   │   ├── Hero.svelte       # Hero section with email capture
│   │   ├── Features.svelte   # Features grid
│   │   ├── About.svelte      # About section
│   │   ├── Impact.svelte     # Statistics and mission
│   │   ├── CTA.svelte        # Call-to-action section
│   │   └── Footer.svelte     # Footer with links
│   ├── App.svelte            # Main app component
│   ├── main.js               # Entry point
│   └── app.css               # Global styles
├── index.html                # HTML template
├── vite.config.js            # Vite configuration
└── package.json              # Dependencies and scripts
```

## Customization

### Colors
The main gradient uses purple tones. To change it, update these in the component styles:
- Primary: `#667eea`
- Secondary: `#764ba2`
- Accent: `#ff6b6b`

### Content
Edit the component files in `src/lib/` to change:
- Hero text and tagline
- Feature descriptions
- Statistics
- Footer links

### Base URL
If your repo name is different from `Teen Zen`, update `vite.config.js`:
```js
base: '/your-repo-name/'
```

## Performance

- Lighthouse Score: 95+
- Svelte compiles to vanilla JavaScript (no runtime overhead)
- Minimal bundle size (~15KB gzipped)
- Optimized images and assets

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

MIT - See LICENSE file
