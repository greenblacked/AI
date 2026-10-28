# Publishing and configuration reference

Read this when you publish a library, when types and runtime disagree, or when Jest or a bundler is the loader.

## Contents

- exports map shapes
- TypeScript configuration table
- Publish checks
- Jest and bundler notes

## exports map shapes

ESM only (the default recommendation):

```json
{
  "type": "module",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "default": "./dist/index.js"
    }
  },
  "engines": { "node": ">=20.19" }
}
```

Dual, only when a consumer needs it. Each format needs its own declaration file, and `types` comes first inside each condition because resolution takes the first match:

```json
{
  "exports": {
    ".": {
      "import": { "types": "./dist/index.d.mts", "default": "./dist/index.mjs" },
      "require": { "types": "./dist/index.d.cts", "default": "./dist/index.cjs" }
    }
  }
}
```

Anything not listed in `exports` cannot be imported, which is what produces `ERR_PACKAGE_PATH_NOT_EXPORTED`. List every subpath you intend consumers to use, and `./package.json` if tools read it.

## TypeScript configuration table

| Runtime that runs the output | `module` | `moduleResolution` |
| --- | --- | --- |
| Node directly | `node16` or `nodenext` | same value |
| A bundler (webpack, esbuild, Vite, Rollup) | `esnext` or `preserve` | `bundler` |
| Jest transforming to CommonJS | `commonjs` | `node10` (or `node16` for both settings) |

Under `node16` and `nodenext`, relative imports in ESM files need the `.js` extension in the source, and the file's module type follows `package.json` `type`.

## Publish checks

1. `npm pack` produces the tarball consumers get; inspect its file list for missing `dist` files.
2. `npx publint@0.3.25` checks the manifest against what the files are.
3. `npx --package=@arethetypeswrong/cli@0.18.5 attw --pack .` checks each resolution mode. Cells show whether types and runtime resolve, whether a CommonJS consumer sees an ESM-only file, and whether the masquerading format problem exists (a declaration claiming one format for a file of another).
4. Install the tarball in an empty directory and import it from a CommonJS file, an ESM file and a TypeScript file under both resolution modes.

## Jest and bundler notes

Jest runs CommonJS by default. Native ESM needs `node --experimental-vm-modules` and `"type": "module"` or `.mjs` test files; an ESM-only dependency that Jest cannot transform fails with `Cannot use import statement outside a module`. The options are to run Jest in ESM mode or add the dependency to `transformIgnorePatterns` exceptions so it is transformed. Bundlers choose conditions by their own list (`import`, `module`, `browser`, `default`), so a package that works in Node can resolve a different file in a bundle; print the resolved path from the bundler's resolver, not from Node.
