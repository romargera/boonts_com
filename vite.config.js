import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: 'src',
  publicDir: '../public',
  base: '/',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/index.html'),
        shesafe: resolve(__dirname, 'src/shesafe/index.html'),
        insights_ru: resolve(__dirname, 'src/insights/ru/roman-vs-experts.html'),
        insights_en: resolve(__dirname, 'src/insights/en/roman-vs-experts.html'),
      },
    },
  },
});
