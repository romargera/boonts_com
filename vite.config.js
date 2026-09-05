import { defineConfig } from 'vite';
import { resolve } from 'path';
import { readFileSync } from 'node:fs';

const pages = JSON.parse(readFileSync(new URL('./seo/pages.json', import.meta.url), 'utf8'));

export default defineConfig({
  root: 'src',
  publicDir: '../public',
  base: '/',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: Object.fromEntries(pages.filter(page => page.source.startsWith('src/'))
        .map((page, index) => [`page_${index}`, resolve(__dirname, page.source)])),
    },
  },
});
