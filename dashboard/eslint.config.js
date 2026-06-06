import reactPlugin from 'eslint-plugin-react';

const browserGlobals = {
  console: 'readonly',
  document: 'readonly',
  EventSource: 'readonly',
  fetch: 'readonly',
  setInterval: 'readonly',
  clearInterval: 'readonly',
  window: 'readonly',
  URLSearchParams: 'readonly',
};

export default [
  { ignores: ['dist', 'node_modules'] },
  {
    files: ['**/*.{js,jsx}'],
    plugins: { react: reactPlugin },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: browserGlobals,
    },
    rules: {
      'no-undef': 'error',
      'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-console': 'warn',
      'react/jsx-uses-react': 'error',
      'react/jsx-uses-vars': 'error',
    },
  },
];
