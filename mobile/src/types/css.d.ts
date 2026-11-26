// ABOUTME: Lets TypeScript accept the side-effect import of global.css in the root layout.
// ABOUTME: Expo declares this in the generated expo-env.d.ts, which is gitignored and absent until `expo start`.

declare module '*.css';
