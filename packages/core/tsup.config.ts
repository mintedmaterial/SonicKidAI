import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  treeshake: true,
  minify: false,
  external: [
    'ethers',
    'events'
  ],
  esbuildOptions(options) {
    options.banner = {
      js: '"use strict";',
    }
  }
})
