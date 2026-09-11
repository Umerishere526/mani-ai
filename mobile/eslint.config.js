// ABOUTME: ESLint flat config for the Expo mobile app.
// ABOUTME: Extends eslint-config-expo and ignores build output.

const { defineConfig } = require("eslint/config");
const expoConfig = require("eslint-config-expo/flat");

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ["dist/*", ".expo/*", "node_modules/*"],
  },
]);
