# Migration recipes

Read this when the same kind of error repeats across many files.

## Contents

- noImplicitAny
- strictNullChecks
- strictPropertyInitialization
- useUnknownInCatchVariables
- noUncheckedIndexedAccess
- exactOptionalPropertyTypes
- Boundary parsing with a schema

## noImplicitAny

Error: parameter implicitly has an `any` type. Fix by stating the type from the call sites, not by writing `any`. For callbacks passed to typed APIs, the type is inferred and the error disappears once the outer call is typed. For untyped third-party packages, install their `@types/` package or write a minimal declaration for only the functions used.

## strictNullChecks

Typical shapes:

- `Object is possibly undefined`: narrow with an early return, `if (x === undefined) throw ...`, or optional chaining with a default, `x?.y ?? fallback`.
- A function returning `T | undefined` used as `T`: change the caller to handle absence, or change the function to throw when absence is a bug.
- A field assigned later: make it `T | undefined` and handle it, or restructure so the object is built complete.
- `Array.prototype.find` and `Map.get` results: both return `undefined`; handle it where the lookup happens.

Resist `!` unless an earlier line proves the value exists and the compiler cannot see it, and say why in a comment.

## strictPropertyInitialization

A class field not set in the constructor. Initialise it, make it optional, or use the definite assignment marker `field!: T` only when a framework sets it before use.

## useUnknownInCatchVariables

`catch (e)` becomes `unknown`. Narrow with `e instanceof Error` before reading `e.message`.

## noUncheckedIndexedAccess

`arr[i]` and `record[key]` become `T | undefined`. Fix loops by iterating with `for...of` or `.map` instead of indexing; handle genuine lookups explicitly. A fixed-length tuple type keeps precise indexing.

## exactOptionalPropertyTypes

`{ a?: string }` no longer accepts an explicit `undefined`. Either widen the type to `a?: string | undefined` where `undefined` is meaningful, or stop assigning `undefined` and omit the key.

## Boundary parsing with a schema

```ts
const User = z.object({ id: z.string(), email: z.string().email() });
type User = z.infer<typeof User>;
const user = User.parse(await res.json());
```

Use the validator's non-throwing form where the caller must recover. Do the same for `process.env`: parse once at start-up into a typed config object and import that, not the raw variables.
