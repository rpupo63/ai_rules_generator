"""
Configuration constants and mappings for AI rules generator.
"""

# Mapping of languages to their available frameworks in rules-new
# This includes all languages and frameworks found in awesome-cursorrules
LANGUAGE_FRAMEWORK_MAP = {
    "python": {
        "frameworks": ["fastapi", "django", "flask", "temporal"],
        "rule_file": "python.mdc",
        "additional": ["database", "codequality", "clean-code"]
    },
    "typescript": {
        "frameworks": ["nextjs", "react", "vue", "svelte", "sveltekit", "node-express", "tailwind", 
                      "angular", "astro", "nestjs", "supabase", "redux", "shadcn", "solidjs", 
                      "tauri", "vercel", "cloudflare", "vite", "axios", "zod", "nuxt", "expo", 
                      "react-native", "jest", "detox", "clasp", "symfony"],
        "rule_file": "typescript.mdc",
        "additional": ["codequality", "clean-code"]
    },
    "javascript": {
        "frameworks": ["react", "vue", "nextjs", "node-express", "tailwind", "astro"],
        "rule_file": None,  # Use TypeScript rules as reference
        "additional": ["codequality", "clean-code"]
    },
    "rust": {
        "frameworks": [],
        "rule_file": "rust.mdc",
        "additional": ["codequality", "clean-code"]
    },
    "cpp": {
        "frameworks": [],
        "rule_file": "cpp.mdc",
        "additional": ["codequality", "clean-code"]
    },
    "java": {
        "frameworks": ["springboot"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "go": {
        "frameworks": ["htmx", "temporal"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "kotlin": {
        "frameworks": ["ktor", "springboot"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "swift": {
        "frameworks": ["uikit", "swiftui"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "elixir": {
        "frameworks": ["phoenix"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "php": {
        "frameworks": ["laravel", "wordpress"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "ruby": {
        "frameworks": ["rails"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "scala": {
        "frameworks": [],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "r": {
        "frameworks": [],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "solidity": {
        "frameworks": ["foundry", "hardhat"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "html": {
        "frameworks": ["tailwind"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "css": {
        "frameworks": ["tailwind", "material-ui"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    # Add JavaScript aliases
    "js": {
        "frameworks": ["react", "vue", "nextjs", "node-express", "tailwind", "astro"],
        "rule_file": None,
        "additional": ["codequality", "clean-code"]
    },
    "ts": {
        "frameworks": ["nextjs", "react", "vue", "svelte", "sveltekit", "node-express", "tailwind",
                      "angular", "nestjs", "supabase", "redux", "shadcn"],
        "rule_file": "typescript.mdc",
        "additional": ["codequality", "clean-code"]
    },
}

# Additional rule files that can be added regardless of language
UNIVERSAL_RULES = ["codequality", "clean-code", "database", "gitflow"]

# File patterns that indicate a technology stack
TECHNOLOGY_INDICATORS = {
    "python": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "poetry.lock"],
    "typescript": ["tsconfig.json", "package.json"],  # Will check package.json for TypeScript
    "javascript": ["package.json", "package-lock.json", "yarn.lock"],
    "rust": ["Cargo.toml", "Cargo.lock"],
    "go": ["go.mod", "go.sum"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "cpp": ["CMakeLists.txt", "Makefile", ".cpp", ".hpp"],
}

# Common monorepo package directory patterns
MONOREPO_PACKAGE_DIRS = ["packages", "apps", "services", "libs", "modules"]

# Security rules template (always applied in monorepos)
SECURITY_RULES_TEMPLATE = """---
description: Security rules - always applied
globs:
  - "**/*"
alwaysApply: true
---

# Security Rules

## Critical Security Guidelines

- NEVER commit API keys, passwords, tokens, or .env files
- NEVER use `eval()`, `Function()`, or dynamic code execution with user input
- ALWAYS validate ALL user input using schema validation (Zod, Pydantic, etc.)
- ALWAYS use parameterized queries for database operations - never string concatenation
- ALWAYS hash passwords with bcrypt (minimum 10 rounds) or equivalent secure hashing
- ALWAYS apply Content-Security-Policy headers in web applications
- ALWAYS use HTTPS in production environments
- ALWAYS implement proper CORS policies
- ALWAYS sanitize user inputs before rendering or storing
- ALWAYS use secure session management practices
- ALWAYS implement proper rate limiting for APIs
- ALWAYS log security-relevant events appropriately

## Code Review Checklist

Before committing code, verify:
- No hardcoded secrets or credentials
- All user inputs are validated
- Database queries use parameterization
- Authentication/authorization is properly implemented
- Error messages don't leak sensitive information
"""

