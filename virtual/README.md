# Virtual

Alpha One Labs' virtual world — a Three.js environment where users browse activities and join the virtual classroom, built as plain TypeScript with no frontend framework.

## Stack

- TypeScript + [Three.js](https://threejs.org/), no framework
- [Vite](https://vitejs.dev/) for dev/build
- [Cloudflare Workers (static assets)](https://developers.cloudflare.com/workers/static-assets/) for hosting

## Development

```bash
npm install
npm run dev
```

## Build & deploy

```bash
npx wrangler login
npm run deploy
```

`npm run deploy` runs the build automatically. Set `VITE_LEARN_API_BASE` (defaults to `https://learn.alphaonelabs.com`) if the app should talk to a different Learn API instance.
