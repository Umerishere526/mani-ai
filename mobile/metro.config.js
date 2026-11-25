// ABOUTME: Metro bundler config — Expo's defaults wrapped by NativeWind so Tailwind
// ABOUTME: classes in src/global.css compile into React Native styles.

const { getDefaultConfig } = require("expo/metro-config");
const { withNativewind } = require("nativewind/metro");

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

module.exports = withNativewind(config);
