---
description: "Use when working on the Vue 3 frontend. Covers Composition API patterns, TypeScript strict mode, Tailwind CSS, Pinia state management, and component conventions."
applyTo: "frontend/**"
---
# Vue / TypeScript / Tailwind Guidelines

## Vue 3 Composition API
- Always use `<script setup lang="ts">` syntax
- Prefer `ref()` and `computed()` over Options API
- Use composables (`use*.ts`) for reusable stateful logic
- Components must have multi-word PascalCase names (e.g., `EmailBrowser.vue`)

## TypeScript
- Strict mode enabled (`strict: true` in tsconfig)
- Define explicit interfaces for API response types in `types/` directory
- No `any` — use `unknown` and narrow with type guards when needed
- Use `enum` sparingly; prefer `as const` union types

## Tailwind CSS
- Use utility classes exclusively; avoid custom CSS unless truly necessary
- Use Tailwind's design tokens for spacing, colors, typography
- Extract repeated utility patterns into Vue components, not CSS classes

## State Management (Pinia)
- One store per domain: `useEmailStore`, `useTopicStore`, `useTaskStore`, etc.
- Keep stores thin — business logic in composables, stores hold state
- Use `defineStore` with setup function syntax

## API Communication
- Centralize API calls in `api/` directory with typed functions
- Use `fetch` or a thin wrapper; avoid heavy HTTP libraries
- Handle loading/error states consistently across components

## Routing
- Vue Router with lazy-loaded route components
- Route names in kebab-case: `email-browser`, `topic-explorer`
- Use route guards for auth checks (when auth is implemented)
