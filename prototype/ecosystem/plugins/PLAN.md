# Ecosystem & Adoption Tools Plan

To drive adoption, we need "drop-in" solutions for popular stacks. The goal is to make AIO support a <5 minute task for developers.

## 1. Node.js (Express Middleware)
**Goal:** Enable any Express app to serve AIO content with 2 lines of code.
**Features:**
- Automatic `robots.txt` injection
- Serves `ai-manifest.json`
- Routes `/ai-content.aio` to a generator function provided by the dev

## 2. WordPress Plugin (PHP)
**Goal:** Zero-config AIO for the 43% of the web running WP.
**Features:**
- Hooks into `wp_head` to add discovery links
- Hooks into `robots_txt` to add directives
- Automatically generates AIO content from Posts/Pages
- Endpoint `/ai-content.aio` serves the JSON

## 3. PHP Library (Generic)
**Goal:** Simple class for any PHP (Laravel, etc.) project.
**Features:**
- `AIOBuilder` class to construct the JSON structure
- validation method

## 4. React / Next.js
**Goal:** Component/Hook for SPA/SSG AIO compatibility.
**Features:**
- `<AIOHead />` component for discovery tags
- Helper to structure data from page props
