---
name: pnpm-workspace
description: Understand and build on the pnpm monorepo template. Use when working on workspace structure, TypeScript project references, dependency management, artifact routing, shared libraries, or cross-package changes.
---

# pnpm workspace skill

## Structure

```text
artifacts-monorepo/
├── artifacts/              # Deployable applications
├── lib/                    # Shared libraries
├── scripts/                # Utility scripts (single workspace package)
├── pnpm-workspace.yaml     # Workspace package discovery, catalog pins, overrides
├── tsconfig.base.json      # Shared strict TS defaults for packages that can extend it
├── tsconfig.json           # Root TS solution config for composite libs only
└── package.json            # Root task orchestration and shared dev tooling
```

## TypeScript

Default model:

- `lib/*` packages are composite and emit declarations via `tsc --build`.
- `artifacts/*` and `scripts` are leaf workspace packages checked with `tsc --noEmit`. They should never import from each other, if you need to share functionality (encouraged) you must create a new lib.
- Root `tsconfig.json` is a solution file for libs only, used by `tsc --build`.
- `tsconfig.base.json` contains shared strict defaults. Not all packages extend it (e.g. Expo apps will use its own base).

Root commands:

- `pnpm run typecheck:libs` runs `tsc --build` for the composite libs.
- `pnpm run typecheck` is the canonical full check: builds libs first, then runs leaf workspace package typechecks.
- Prefer the root `typecheck` result over editor/LSP state when they disagree.

Adding a new lib:

- Add `composite`, `declarationMap`, and `emitDeclarationOnly` to its `tsconfig.json`.
- Add it to the root `tsconfig.json` `references` array.
- If it imports another lib, add that lib to its own `references`.

Adding a new artifact:

- Should be usually handled via the `artifacts` skill unless no artifact template satisfies the user's requirements.
- Do **not** add it to the root `tsconfig.json` references.

Project references:

- When one lib imports another lib, the importing lib must declare it in `references` so `tsc --build` can order and rebuild correctly.
- Root `tsconfig.json` should list the lib packages, not every workspace package.
- Artifact `references` to libs are optional but useful for:
  - explicit documentation of direct workspace dependencies
  - better editor/tsserver project awareness
  - standalone `tsc -b artifacts/<name>` style workflows

## Server & API contracts

For backend-backed apps, define the contract in OpenAPI first, then generate helpers from it.

Codegen command:

- `pnpm --filter @workspace/api-spec run codegen`

This generates files such as React Query hooks and Zod schemas. It is strongly recommended that you use them. The server should use Zod schemas to validate inputs and outputs, and clients should use the available hooks.

## Logging

The API server uses `pino` for structured JSON logging. **Never use `console.log` or `console.error` in server code.** Inside route handlers and middleware, use `req.log` (the request-scoped child logger from `pino-http`) so logs automatically include the request ID. Use the singleton `logger` from `artifacts/api-server/src/lib/logger.ts` only for non-request code (startup, shutdown, background tasks). See `references/server.md` for full details and examples.

**Older workspaces** created before the structured-logging stack update may not have `pino-http` middleware in `app.ts` or `artifacts/api-server/src/lib/logger.ts`. Before using `req.log` or importing the singleton `logger`, check whether these exist. If they are missing, add them first:

```bash
pnpm --filter @workspace/api-server add pino pino-http
pnpm --filter @workspace/api-server add -D pino-pretty
```

Then create `artifacts/api-server/src/lib/logger.ts` and add the canonical `pinoHttp` middleware in `app.ts` before the routes — see `references/server.md` for the full canonical content of both.

## References

- `references/openapi.md` — Setting up OpenAPI spec and code generation in this contract-first repo.
- `references/server.md` — Important information about adding routes and general tips.
- `references/db.md` — Adding new database schemas and running migrations.

## `scripts` (`@workspace/scripts`)

Put shared utility scripts in `./scripts`.

- Each script lives in `scripts/src/`
- Add a matching npm script in `scripts/package.json`
- `scripts` is treated like a leaf workspace package and typechecked with `tsc --noEmit`

## Proxy & service routing

A global reverse proxy routes traffic by path using each artifact's `.replit-artifact/artifact.toml`.

Example:

```toml
[[services]]
localPort = 8080
name = "API Server"
paths = ["/api"]
```

**Rules for accessing services:**

- For ad hoc requests, such as `curl`, always go through the shared proxy at `localhost:80`. Never call service ports directly.
  - Correct: `localhost:80/api/healthz`
  - Wrong: `localhost:8080/api/healthz`
- Paths are not rewritten. Services must handle their full base path themselves.
- The only exception is the EXPO artifact. If one exists, use $REPLIT_EXPO_DEV_DOMAIN to access it locally.
- In application code, prefer relative URLs when possible. For user-facing access, both development previews and published production domains already route through the shared proxy automatically. Published apps are exposed over HTTPS on the domains listed in `$REPLIT_DOMAINS` (comma-separated).
- Do NOT add Vite proxy configs or custom base URLs to reach other services; the shared proxy already handles cross-service routing.
- Routes across artifacts are matched most-specific-first, so a service on `/api` won't conflict with one on `/`.

## Package management

Workspace package rules:

- Workspace package names should use the `@workspace/` prefix.
- Each package must declare its own dependencies; dependencies are not shared implicitly across workspace packages.
- Root dependencies are for repo-level tooling such as `typescript`, `prettier`, `eslint`, `vitest`, etc.
- Do not use `pnpm add --no-frozen-lockfile`. `pnpm add` will automatically use `catalog:` if the dependency already has a catalog entry.

### devDependencies vs dependencies

Prefer `devDependencies` over `dependencies` whenever possible to reduce deployed image size. Everything that is served statically (React apps, Vite-built frontends) or only needed at build time should be a `devDependency`. The deployment pipeline runs `pnpm prune --prod` via `postBuild` to strip them from the final container image.

Rules:

1. **Static/client-only artifacts** (e.g. Vite-built React apps): all packages should be `devDependencies` since nothing is `require`'d at runtime — the output is static files.
2. **Server artifacts**: packages imported at runtime (e.g. `express`, `drizzle-orm`, `pg`) stay in `dependencies`. Everything else — build tools (`esbuild`, `tsx`, `vite`), type definitions (`@types/*`), linters, and test frameworks — goes in `devDependencies`.
3. **Libraries**: runtime exports stay in `dependencies` (or `peerDependencies` for shared runtimes); codegen tools and type-only packages go in `devDependencies`.
4. When in doubt, check whether the package is imported in code that runs in production. If not, it is a `devDependency`.

### Dependency catalogs

`pnpm-workspace.yaml` uses `catalog:` entries to pin shared versions in one place.

Use the catalog when:

- a dependency is shared by a library and its consumers
- a dependency should stay aligned across multiple workspace packages

Rules:

1. If a dependency already exists in the catalog, use `"catalog:"`.
2. If a lib and its consumers both use a dependency, prefer adding it to the catalog and updating all relevant packages together.
3. Only hardcode versions when a package truly must diverge.

Example:

```json
{
  "dependencies": {
    "react": "catalog:",
    "zod": "catalog:"
  }
}
```

### Shared runtime dependencies

Be careful with shared runtime dependencies like `react`, `react-dom`, or `@tanstack/react-query`.

- If a workspace lib and its consumers resolve different copies, you get duplicate runtime instances or type identity problems (e.g. broken hooks/context, confusing TypeScript errors).
- Libraries should declare shared runtimes as `peerDependencies`; apps install the concrete version.
- Use the catalog-pinned version by default. Avoid introducing separate versions casually.

## Codegen Outputs

After running `pnpm --filter @workspace/api-spec run codegen`, Orval writes the generated client to fixed paths:

- `lib/api-client-react/src/generated/api.ts`
- `lib/api-client-react/src/generated/api.schemas.ts`
- `lib/api-zod/src/generated/api.ts`

The workspace barrels re-export those fixed filenames:

- `lib/api-client-react/src/index.ts`
- `lib/api-zod/src/index.ts`

The Orval config forces the OpenAPI title to `Api`, so do not try to control generated filenames via `info.title`. If you touch the codegen config or scaffolded barrel files, keep them aligned with the fixed `generated/api*` filenames.

## Common pitfalls

- Do not introduce an all-composite setup for leaf workspace packages. Declaration emit from apps causes type portability issues (TS2742) when multiple versions of `@types/*` packages exist across workspace packages.
- Do not add leaf workspace packages to the root `tsconfig.json` references; that solution file is for buildable libs only.
- Prefer root commands with `--filter` when targeting a specific package:
  - `pnpm --filter @workspace/api-server run build`
- If the editor and CLI disagree on cross-package types, trust `pnpm run typecheck`.
- If you change Orval output paths or the barrel exports, generated imports may break.

## Artifact Lifecycle

If you are creating or updating an artifact, follow the `artifacts` skill for the artifact callback lifecycle (`createArtifact`, `verifyAndReplaceArtifactToml`, `presentArtifact`, and `suggestDeploy()`) instead of redefining it here.
