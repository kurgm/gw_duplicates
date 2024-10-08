/** @type {import('eslint').Linter.Config} */
module.exports = {
    env: {
        browser: true,
        es6: true,
    },
    parser: "@typescript-eslint/parser",
    parserOptions: {
        projectService: true,
        sourceType: "module",
        tsconfigRootDir: __dirname,
    },
    plugins: [
        "@typescript-eslint",
    ],
    extends: [
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended-type-checked",
        "plugin:@typescript-eslint/stylistic-type-checked",
        "plugin:react/recommended",
        "plugin:react-hooks/recommended",
    ],
    rules: {
        "@typescript-eslint/explicit-function-return-type": "off",
        "@typescript-eslint/no-explicit-any": "off",
    },
    settings: {
        react: {
            version: "detect",
        },
    },
};
