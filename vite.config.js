import { defineConfig } from 'vite';

export default defineConfig({
  root: 'src',
  publicDir: '../public',
  base: '/me/',
  build: {
    outDir: '../dist/me',
    emptyOutDir: true,
  },
});
