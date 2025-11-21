export default {
  "preset": "ts-jest",
  "testEnvironment": "node",
  "testMatch": [
    "**/__tests__/**/*.test.ts",
    "**/?(*.)+(spec|test).ts"
  ],
  "collectCoverageFrom": [
    "src/**/*.ts",
    "!src/**/*.d.ts",
    "!src/types/**/*",
    "!src/**/*.test.ts"
  ],
  "coverageDirectory": "coverage",
  "coverageReporters": [
    "text",
    "lcov",
    "html"
  ],
  "coverageThreshold": {
    "global": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    }
  },
  "setupFilesAfterEnv": [
    "<rootDir>/test/setup.ts"
  ],
  "moduleFileExtensions": [
    "ts",
    "tsx",
    "js",
    "jsx",
    "json"
  ],
  "transform": {
    "^.+\\.ts$": "ts-jest"
  },
  "testTimeout": 30000,
  "verbose": true,
  "bail": false,
  "forceExit": true,
  "detectOpenHandles": true
};
