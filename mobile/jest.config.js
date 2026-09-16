// ABOUTME: Jest config for mobile/ — jest-expo preset handles the RN/Expo transform.
// ABOUTME: Kept minimal: no RNTL/MSW setup yet, since nothing here mocks the network.

module.exports = {
  preset: 'jest-expo',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};
