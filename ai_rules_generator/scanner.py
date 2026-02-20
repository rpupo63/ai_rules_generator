"""
Recursive directory scanner that builds a tree-structured representation of
the project's file structure for inclusion in AI rules.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .ai_generator import call_ai_api
from .models import ProjectConfig

from .exclusions import (
    get_exclusion_context,
    should_skip_dir,
    should_skip_file,
    is_generated_file,
)


@dataclass
class FileInfo:
    """Information about a single file."""
    name: str
    role: str  # inferred role: "entry_point", "config", "test", "component", etc.
    description: str = "" # A concise, AI-generated summary of the file's purpose
    size_lines: int = 0
    exports: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class FolderInfo:
    """Structural information about a folder."""
    name: str
    path: str  # relative to project root
    purpose: str  # inferred purpose
    files: List[FileInfo] = field(default_factory=list)
    subfolders: List[str] = field(default_factory=list)  # child folder names (for compat)
    children: List['FolderInfo'] = field(default_factory=list)  # actual child FolderInfo objects
    file_count: int = 0
    has_tests: bool = False
    has_config: bool = False
    detected_patterns: List[str] = field(default_factory=list)
    readme_summary: str = ""
    public_api: List[str] = field(default_factory=list)
    key_dependencies: List[str] = field(default_factory=list)
    ai_folder_summary: str = ""  # LLM-generated folder-level summary


@dataclass
class ScanContext:
    """Complete scan result with multiple representations."""
    root: FolderInfo  # tree-structured root
    flat: List[FolderInfo] = field(default_factory=list)  # flat list of all folders
    by_path: Dict[str, FolderInfo] = field(default_factory=dict)  # path -> FolderInfo lookup
    prompt_text: str = ""  # pre-formatted text for AI prompts


# Go-specific folder name -> purpose mappings (higher priority)
GO_FOLDER_PURPOSE_MAP = {
    "api": "HTTP API endpoints and handlers",
    "cmd": "Command-line application entry points",
    "models": "GORM data models and database schemas",
    "database": "Data Access Layer (DAL) and GORM repositories",
    "services": "Core business logic services",
    "errs": "Centralized error handling definitions",
    "internal": "Internal application components and utilities",
    "seed": "Database seeding and test data generation",
    "bootstrap": "Application initialization and bootstrapping",
    "config": "Application configuration management",
    "docs": "Project documentation and guides",
    "server": "HTTP server setup and routing",
    "routes": "API route definitions",
    "handlers": "API request handlers",
    "repo": "Database repository interfaces and implementations",
    "repositories": "Database repository interfaces and implementations",
    "middleware": "HTTP middleware functions",
}

# Common folder name -> purpose mappings
FOLDER_PURPOSE_MAP = {
    # Source code
    "src": "main source code",
    "lib": "library/utility code",
    "app": "application entry points and routes",
    "pages": "page components or route handlers",
    "api": "HTTP API endpoints and handlers",
    "routes": "route definitions",
    "controllers": "request controllers",
    "handlers": "request/event handlers",
    # Components / UI
    "components": "reusable UI components",
    "ui": "base UI primitives",
    "layouts": "page layout components",
    "views": "view/page components",
    "templates": "template files",
    "widgets": "widget components",
    # Data / Logic
    "models": "GORM data models and database schemas",
    "schemas": "validation schemas",
    "types": "type definitions",
    "interfaces": "interface definitions",
    "entities": "domain entities",
    "services": "Core business logic services",
    "modules": "feature modules",
    "domain": "domain layer logic",
    # Data access
    "repositories": "data access layer",
    "database": "Data Access Layer (DAL) and GORM repositories",
    "db": "Data Access Layer (DAL) and GORM repositories",
    "migrations": "database migration files",
    "prisma": "Prisma ORM schema and configuration",
    # State / Hooks
    "store": "state management",
    "stores": "state management stores",
    "state": "application state",
    "hooks": "custom hooks",
    "composables": "Vue composable functions",
    # Utilities
    "utils": "utility/helper functions",
    "helpers": "helper functions",
    "common": "shared/common code",
    "shared": "code shared across modules",
    "core": "core framework/application code",
    "internal": "Internal application components and utilities",
    # Assets
    "assets": "static assets (images, fonts, etc.)",
    "public": "publicly served static files",
    "static": "static files",
    "media": "media files",
    "images": "image assets",
    "styles": "stylesheets",
    "css": "CSS stylesheets",
    # Config
    "config": "configuration files",
    "configs": "configuration files",
    "settings": "application settings",
    # Testing
    "tests": "test files",
    "test": "test files",
    "__tests__": "test files",
    "spec": "test specifications",
    "specs": "test specifications",
    "fixtures": "test fixtures and sample data",
    "mocks": "mock implementations for testing",
    "e2e": "end-to-end tests",
    "integration": "integration tests",
    # Docs
    "docs": "documentation",
    "doc": "documentation",
    # Scripts
    "scripts": "build/utility scripts",
    "bin": "executable scripts",
    "tools": "development tools and scripts",
    # CI/CD
    ".github": "GitHub workflows and configuration",
    # Deployment
    "deploy": "deployment configuration",
    "infra": "infrastructure configuration",
    "terraform": "Terraform IaC configuration",
    "k8s": "Kubernetes manifests",
    "docker": "Docker configuration",
    # Middleware
    "middleware": "middleware functions",
    "middlewares": "middleware functions",
    # Plugins / Extensions
    "plugins": "plugin implementations",
    "extensions": "extension modules",
    # i18n
    "locales": "internationalization/locale files",
    "i18n": "internationalization configuration",
    "translations": "translation files",
    # Workers
    "workers": "background worker/job processors",
    "jobs": "background job definitions",
    "tasks": "task definitions",
    "queues": "message queue handlers",
    # CLI / Packages
    "cmd": "Command-line application entry points",
    "pkg": "public library packages",
    # Errors
    "errs": "Centralized error handling definitions",
    "errors": "error definitions",
    "exceptions": "exception definitions",
    # Bootstrap
    "bootstrap": "Application initialization and bootstrapping",
}

# File name -> role mappings
FILE_ROLE_MAP = {
    # Entry points
    "index.ts": "barrel export / entry point",
    "index.js": "barrel export / entry point",
    "index.tsx": "entry point component",
    "index.jsx": "entry point component",
    "main.ts": "application entry point",
    "main.js": "application entry point",
    "main.py": "application entry point",
    "app.ts": "application setup",
    "app.js": "application setup",
    "app.py": "application setup",
    "server.ts": "server entry point",
    "server.js": "server entry point",
    "manage.py": "Django management script",
    "wsgi.py": "WSGI application entry",
    "asgi.py": "ASGI application entry",
    "mod.rs": "Rust module entry point",
    "lib.rs": "Rust library entry point",
    "main.rs": "Rust binary entry point",
    "main.go": "Go entry point",
    # Config
    "package.json": "Node.js project configuration",
    "tsconfig.json": "TypeScript compiler configuration",
    "pyproject.toml": "Python project configuration",
    "Cargo.toml": "Rust project configuration",
    "go.mod": "Go module configuration",
    "pom.xml": "Maven project configuration",
    "build.gradle": "Gradle build configuration",
    "docker-compose.yml": "Docker Compose configuration",
    "docker-compose.yaml": "Docker Compose configuration",
    "Dockerfile": "Docker image definition",
    ".env.example": "environment variable template",
    "tailwind.config.js": "Tailwind CSS configuration",
    "tailwind.config.ts": "Tailwind CSS configuration",
    "next.config.js": "Next.js configuration",
    "next.config.mjs": "Next.js configuration",
    "next.config.ts": "Next.js configuration",
    "vite.config.ts": "Vite build configuration",
    "vite.config.js": "Vite build configuration",
    "webpack.config.js": "Webpack build configuration",
    "jest.config.js": "Jest test configuration",
    "jest.config.ts": "Jest test configuration",
    "vitest.config.ts": "Vitest test configuration",
    "eslint.config.js": "ESLint linter configuration",
    ".eslintrc.js": "ESLint linter configuration",
    ".eslintrc.json": "ESLint linter configuration",
    ".prettierrc": "Prettier formatter configuration",
    "biome.json": "Biome linter/formatter configuration",
    "components.json": "shadcn/ui configuration",
    "drizzle.config.ts": "Drizzle ORM configuration",
    "prisma/schema.prisma": "Prisma database schema",
    "schema.prisma": "Prisma database schema",
    "alembic.ini": "Alembic migration configuration",
    "setup.py": "Python package setup",
    "setup.cfg": "Python package configuration",
    "Makefile": "build automation",
    "CMakeLists.txt": "CMake build configuration",
    "Justfile": "Just command runner configuration",
    "Taskfile.yml": "Task runner configuration",
    # Data / Schema
    "schema.graphql": "GraphQL schema definition",
    "schema.sql": "SQL schema definition",
    "openapi.yaml": "OpenAPI specification",
    "openapi.json": "OpenAPI specification",
    "swagger.yaml": "Swagger/OpenAPI specification",
    "swagger.json": "Swagger/OpenAPI specification",
}

# Regex patterns for extracting file signatures by language
_SIGNATURE_PATTERNS = {
    ".py": [
        re.compile(r'^(?:class|def)\s+(\w+)', re.MULTILINE),
    ],
    ".ts": [
        re.compile(r'^export\s+(?:default\s+)?(?:class|function|const|let|var|type|interface|enum)\s+(\w+)', re.MULTILINE),
        re.compile(r'^(?:export\s+)?(?:class|function)\s+(\w+)', re.MULTILINE),
    ],
    ".tsx": [
        re.compile(r'^export\s+(?:default\s+)?(?:class|function|const|let|var|type|interface|enum)\s+(\w+)', re.MULTILINE),
        re.compile(r'^(?:export\s+)?(?:class|function)\s+(\w+)', re.MULTILINE),
    ],
    ".js": [
        re.compile(r'^export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)', re.MULTILINE),
        re.compile(r'^(?:class|function)\s+(\w+)', re.MULTILINE),
    ],
    ".jsx": [
        re.compile(r'^export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)', re.MULTILINE),
        re.compile(r'^(?:class|function)\s+(\w+)', re.MULTILINE),
    ],
    ".go": [
        re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)', re.MULTILINE),
        re.compile(r'^type\s+(\w+)\s+(?:struct|interface)', re.MULTILINE),
    ],
    ".rs": [
        re.compile(r'^pub\s+(?:fn|struct|enum|trait|type)\s+(\w+)', re.MULTILINE),
    ],
}

# Barrel file names (files that re-export a folder's public API)
_BARREL_FILES = {"index.ts", "index.js", "index.tsx", "index.jsx", "__init__.py", "mod.rs", "lib.rs"}

# Architectural pattern indicators
_ARCH_PATTERN_INDICATORS = {
    "Redux store": [re.compile(r'createStore|configureStore|createSlice', re.MULTILINE)],
    "Zustand store": [re.compile(r'create\s*\(\s*\(set', re.MULTILINE)],
    "MobX store": [re.compile(r'@observable|makeObservable|makeAutoObservable', re.MULTILINE)],
    "file-based routing": [],  # detected by folder structure
    "Express middleware": [re.compile(r'app\.use\(|router\.use\(', re.MULTILINE)],
    "DI container": [re.compile(r'@Injectable|@Inject|Container\.bind|injector', re.MULTILINE)],
    "GraphQL": [re.compile(r'type\s+Query|type\s+Mutation|gql`', re.MULTILINE)],
    "REST API": [re.compile(r'@(Get|Post|Put|Delete|Patch)\(|app\.(get|post|put|delete)\(', re.MULTILINE)],
    "WebSocket": [re.compile(r'WebSocket|socket\.io|ws\.on\(', re.MULTILINE)],
    "ORM (Prisma)": [re.compile(r'prisma\.\w+\.(find|create|update|delete)', re.MULTILINE)],
    "ORM (SQLAlchemy)": [re.compile(r'Column\(|relationship\(|Base\.metadata', re.MULTILINE)],
    "ORM (Drizzle)": [re.compile(r'drizzle\(|pgTable\(|mysqlTable\(', re.MULTILINE)],
}

# Manifest files for dependency extraction
_MANIFEST_FILES = {
    "package.json": "node",
    "pyproject.toml": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "pom.xml": "java",
    "build.gradle": "java",
}


def _infer_file_role(file_path: Path) -> str:
    """Infer the role of a file from its name and extension."""
    name = file_path.name

    # Direct match
    if name in FILE_ROLE_MAP:
        return FILE_ROLE_MAP[name]

    # Pattern-based inference
    stem = file_path.stem.lower()
    suffix = file_path.suffix.lower()

    # Test files
    if stem.startswith("test_") or stem.endswith("_test"):
        return "test file"
    if stem.endswith(".test") or stem.endswith(".spec"):
        return "test file"
    if "test" in stem and suffix in (".ts", ".js", ".py", ".go", ".rs"):
        return "test file"
    if "spec" in stem and suffix in (".ts", ".js"):
        return "test file"

    # Middleware
    if "middleware" in stem:
        return "middleware"

    # Route/controller
    if "route" in stem or "router" in stem:
        return "route definitions"
    if "controller" in stem:
        return "request controller"

    # Model/schema
    if "model" in stem or "schema" in stem:
        return "data model/schema"
    if "entity" in stem:
        return "domain entity"

    # Error definitions (before "service" so errors.go doesn't match "service")
    if "error" in stem or stem in ("err", "errs") or stem.startswith("err_") or stem.endswith("_err"):
        return "error definitions"

    # Service
    if "service" in stem:
        return "service implementation"

    # Hook
    if stem.startswith("use") and suffix in (".ts", ".tsx", ".js", ".jsx"):
        return "custom hook"

    # Config files
    if name.endswith("rc") or name.endswith(".config.js") or name.endswith(".config.ts"):
        return "configuration"

    # Type definitions
    if name.endswith(".d.ts") or "types" in stem:
        return "type definitions"

    # By extension
    ext_roles = {
        ".md": "documentation",
        ".mdx": "MDX documentation/component",
        ".css": "stylesheet",
        ".scss": "SCSS stylesheet",
        ".less": "Less stylesheet",
        ".svg": "SVG asset",
        ".sql": "SQL query/migration",
        ".graphql": "GraphQL query/schema",
        ".gql": "GraphQL query/schema",
        ".proto": "Protocol Buffer definition",
        ".yaml": "configuration",
        ".yml": "configuration",
        ".toml": "configuration",
        ".json": "data/configuration",
        ".env": "environment variables",
    }
    if suffix in ext_roles:
        return ext_roles[suffix]

    return "source file"


def _infer_folder_purpose(folder_name: str, contents: List[str]) -> str:
    """Infer the purpose of a folder from its name and contents."""
    name_lower = folder_name.lower()

    # Go-specific direct match (higher priority)
    if name_lower in GO_FOLDER_PURPOSE_MAP:
        return GO_FOLDER_PURPOSE_MAP[name_lower]

    # Common direct match
    if name_lower in FOLDER_PURPOSE_MAP:
        return FOLDER_PURPOSE_MAP[name_lower]

    # Pattern matching
    if "test" in name_lower:
        return "test files"
    if "util" in name_lower or "helper" in name_lower:
        return "utility/helper functions"
    if "component" in name_lower:
        return "UI components"
    if "hook" in name_lower:
        return "custom hooks"
    if "service" in name_lower:
        return "service layer"
    if "model" in name_lower:
        return "data models"
    if "config" in name_lower:
        return "configuration"
    if "style" in name_lower or "css" in name_lower:
        return "stylesheets"
    if "asset" in name_lower or "static" in name_lower:
        return "static assets"
    if "script" in name_lower:
        return "scripts"
    if "migration" in name_lower:
        return "database migrations"
    if "type" in name_lower:
        return "type definitions"
    if "constant" in name_lower or "const" in name_lower:
        return "constants and enums"
    if "feature" in name_lower:
        return "feature module"
    if "page" in name_lower:
        return "page components"
    if "layout" in name_lower:
        return "layout components"
    if "guard" in name_lower or "auth" in name_lower:
        return "authentication/authorization"
    if "error" in name_lower or "exception" in name_lower:
        return "error handling"
    if "log" in name_lower:
        return "logging configuration"
    if "cache" in name_lower:
        return "caching logic"
    if "event" in name_lower:
        return "event handlers"

    return "project files"


def _count_file_lines(file_path: Path) -> int:
    """Count lines in a file, returning 0 on error."""
    try:
        return sum(1 for _ in open(file_path, "r", encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def _detect_folder_patterns(folder_path: Path, files: List[FileInfo]) -> List[str]:
    """Detect architectural patterns in a folder."""
    patterns = []
    file_names = {f.name.lower() for f in files}

    # Barrel exports
    if any(n in file_names for n in ("index.ts", "index.js", "index.tsx", "index.jsx", "__init__.py", "mod.rs")):
        patterns.append("barrel exports")

    # Tests co-located
    has_source = any(f.role == "source file" for f in files)
    has_tests = any(f.role == "test file" for f in files)
    if has_source and has_tests:
        patterns.append("co-located tests")

    # Feature modules (folder with components + hooks + services)
    subfolder_like_roles = {f.role for f in files}
    if "custom hook" in subfolder_like_roles and "source file" in subfolder_like_roles:
        patterns.append("feature module")

    return patterns


def extract_file_signatures(file_path: Path, max_lines: int = 200) -> List[Dict[str, str]]:
    """
    Extract top-level exports/declarations from a source file using regex.
    Returns a list of dictionaries with 'name' and 'code_snippet'.
    """
    suffix = file_path.suffix.lower()
    patterns_and_groups = {
        ".py": [
            (re.compile(r'^(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\)\s*->\s*.*?:(?:\s*#.*)?\s*\n\s*(?:"""[^"]*"""|\'\'\'[^\']*\'\'\'|\w)', re.DOTALL | re.MULTILINE), 1),
            (re.compile(r'^(?:class)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(.*\))?:(?:\s*#.*)?\s*\n\s*(?:"""[^"]*"""|\'\'\'[^\']*\'\'\'|\w)', re.DOTALL | re.MULTILINE), 1),
        ],
        ".ts": [
            (re.compile(r'^(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:[\s<({].*?|;)', re.DOTALL | re.MULTILINE), 1),
        ],
        ".tsx": [
            (re.compile(r'^(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:[\s<({].*?|;)', re.DOTALL | re.MULTILINE), 1),
        ],
        ".js": [
            (re.compile(r'^(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:[\s<({].*?|;)', re.DOTALL | re.MULTILINE), 1),
        ],
        ".jsx": [
            (re.compile(r'^(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:[\s<({].*?|;)', re.DOTALL | re.MULTILINE), 1),
        ],
        ".go": [
            (re.compile(r'^func\s+(?:\([a-zA-Z_][a-zA-Z0-9_]*\s+\*?[a-zA-Z_][a-zA-Z0-9_]*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\)\s*(?:[a-zA-Z_][a-zA-Z0-9_]*|\(.*?\))?\s*{', re.DOTALL | re.MULTILINE), 1), # Function declaration
            (re.compile(r'^type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:struct|interface|func|map|\[\]|chan|string|int|float|bool)', re.DOTALL | re.MULTILINE), 1), # Type declaration
        ],
        ".rs": [
            (re.compile(r'^pub\s+(?:async\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\)\s*(?:->\s*.*?)?\s*{', re.DOTALL | re.MULTILINE), 1), # Function declaration
            (re.compile(r'^pub\s+(?:struct|enum|trait)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:<.*?>)?\s*(?:where\s+.*?)?\s*{', re.DOTALL | re.MULTILINE), 1), # Type declaration
        ],
    }
    patterns = patterns_and_groups.get(suffix)
    if not patterns:
        return []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return []

    seen = set()
    signatures = []
    
    # Iterate through patterns and capture the match and a snippet of its definition
    for pattern, group_index in patterns:
        for match in pattern.finditer(content):
            name = match.group(group_index)
            if name not in seen and not name.startswith("_"):
                seen.add(name)
                # Capture the full line or a small snippet of the declaration
                start_index = match.start()
                end_index = content.find('\n', start_index)
                if end_index == -1: # Last line
                    end_index = len(content)
                snippet = content[start_index:end_index].strip()
                signatures.append({"name": name, "code_snippet": snippet})

    return signatures


def _read_readme_summary(folder_path: Path, max_lines: int = 5) -> str:
    """Read first N lines of README.md in a folder."""
    readme = folder_path / "README.md"
    if not readme.exists():
        return ""
    try:
        with open(readme, "r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    lines.append(stripped)
            return " ".join(lines)
    except OSError:
        return ""


def _extract_barrel_exports(folder_path: Path, files: List[FileInfo]) -> List[str]:
    """Extract public API from barrel files (index.ts, __init__.py, etc.)."""
    exports = []
    for f in files:
        if f.name in _BARREL_FILES:
            barrel_path = folder_path / f.name
            sigs = extract_file_signatures(barrel_path, max_lines=100)
            exports.extend(sigs)
            break
    return exports


def _extract_key_dependencies(folder_path: Path) -> List[str]:
    """Extract key dependencies from manifest files in a folder."""
    deps = []
    for manifest_name, manifest_type in _MANIFEST_FILES.items():
        manifest_path = folder_path / manifest_name
        if not manifest_path.exists():
            continue
        try:
            content = manifest_path.read_text(encoding="utf-8", errors="ignore")
            if manifest_type == "node":
                deps.extend(_parse_package_json_deps(content))
            elif manifest_type == "python":
                deps.extend(_parse_pyproject_deps(content))
        except OSError:
            pass
    return deps[:20]  # cap at 20


def _parse_package_json_deps(content: str) -> List[str]:
    """Extract key dependency names from package.json content."""
    import json
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps = []
    for key in ("dependencies", "devDependencies"):
        for dep_name in data.get(key, {}):
            # Skip type packages and trivial deps
            if dep_name.startswith("@types/"):
                continue
            deps.append(dep_name)
    return deps


def _parse_pyproject_deps(content: str) -> List[str]:
    """Extract dependency names from pyproject.toml content (basic parsing)."""
    deps = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[project.dependencies]", "dependencies = ["):
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("[") or (stripped == "]"):
                break
            # Extract package name from lines like '"requests>=2.28",'
            match = re.match(r'["\']?([a-zA-Z0-9_-]+)', stripped)
            if match:
                deps.append(match.group(1))
    return deps


def detect_architectural_patterns(folder_path: Path, files: List[FileInfo]) -> List[str]:
    """
    Detect architectural patterns by reading file content in a folder.
    Checks for state management, routing, middleware, DI, etc.
    """
    patterns_found = []

    # Check for file-based routing
    file_names = {f.name for f in files}
    if "page.tsx" in file_names or "page.ts" in file_names or "page.js" in file_names:
        patterns_found.append("file-based routing")

    # Sample up to 5 source files for pattern detection
    source_files = [f for f in files if f.role == "source file" and
                    Path(f.name).suffix in (".ts", ".tsx", ".js", ".jsx", ".py")][:5]

    for file_info in source_files:
        file_path_full = folder_path / file_info.name
        if not file_path_full.exists():
            continue
        try:
            with open(file_path_full, "r", encoding="utf-8", errors="ignore") as fh:
                content = ""
                for i, line in enumerate(fh):
                    if i >= 100:
                        break
                    content += line
        except OSError:
            continue

        for pattern_name, regexes in _ARCH_PATTERN_INDICATORS.items():
            if pattern_name in patterns_found:
                continue
            for rx in regexes:
                if rx.search(content):
                    patterns_found.append(pattern_name)
                    break

    return patterns_found


def scan_folder(
    folder_path: Path,
    project_root: Path,
    exclusion_ctx: dict,
    max_files_detail: int = 50,
    extract_signatures: bool = True,
) -> Optional[FolderInfo]:
    """Scan a single folder and return its structural info."""
    if not folder_path.is_dir():
        return None

    gitignore_patterns = exclusion_ctx.get("gitignore_patterns", [])

    try:
        rel_path = str(folder_path.relative_to(project_root)).replace("\\", "/")
    except ValueError:
        rel_path = folder_path.name

    if rel_path == ".":
        rel_path = ""

    folder_name = folder_path.name if rel_path else "root"

    files: List[FileInfo] = []
    subfolders: List[str] = []
    total_files = 0

    try:
        entries = sorted(folder_path.iterdir(), key=lambda p: (p.is_file(), p.name))
    except PermissionError:
        return None

    for entry in entries:
        if entry.is_dir():
            if not should_skip_dir(entry, project_root, gitignore_patterns):
                subfolders.append(entry.name)
        elif entry.is_file():
            if should_skip_file(entry, project_root, gitignore_patterns):
                continue
            total_files += 1
            if len(files) < max_files_detail:
                role = _infer_file_role(entry)
                line_count = _count_file_lines(entry) if entry.stat().st_size < 500_000 else 0
                file_exports = []
                if extract_signatures and role in ("source file", "barrel export / entry point",
                                                    "entry point component", "application entry point",
                                                    "service implementation", "data model/schema",
                                                    "request controller"):
                    file_exports = extract_file_signatures(entry)
                files.append(FileInfo(name=entry.name, role=role, size_lines=line_count,
                                     exports=file_exports))

    purpose = _infer_folder_purpose(folder_name, [f.name for f in files])
    has_tests = any(f.role == "test file" for f in files)
    has_config = any("config" in f.role for f in files)
    patterns = _detect_folder_patterns(folder_path, files)

    # Enhanced: architectural patterns, readme summary, barrel exports, dependencies
    arch_patterns = detect_architectural_patterns(folder_path, files)
    patterns.extend(arch_patterns)

    readme_summary = _read_readme_summary(folder_path)
    public_api = _extract_barrel_exports(folder_path, files)
    key_deps = _extract_key_dependencies(folder_path)

    return FolderInfo(
        name=folder_name,
        path=rel_path,
        purpose=purpose,
        files=files,
        subfolders=subfolders,
        children=[],  # populated by _walk in tree mode
        file_count=total_files,
        has_tests=has_tests,
        has_config=has_config,
        detected_patterns=patterns,
        readme_summary=readme_summary,
        public_api=public_api,
        key_dependencies=key_deps,
    )


# ---------------------------------------------------------------------------
# Bottom-up folder purpose enrichment
# ---------------------------------------------------------------------------

# Keywords in README text that suggest a folder's purpose
_README_PURPOSE_KEYWORDS = {
    "seed": "Database seeding and test data generation",
    "seeding": "data seeding",
    "migration": "database migrations",
    "auth": "authentication",
    "logging": "logging",
    "cache": "caching",
    "queue": "message queue",
    "worker": "background workers",
    "notification": "notifications",
    "email": "email handling",
    "payment": "payment processing",
    "search": "search functionality",
    "upload": "file uploads",
    "storage": "storage layer",
    "validation": "input validation",
    "scheduling": "task scheduling",
}

# Manifest files that indicate a specific project type
_MANIFEST_PURPOSE = {
    "go.mod": "Go",
    "package.json": "Node.js",
    "pyproject.toml": "Python",
    "Cargo.toml": "Rust",
    "pom.xml": "Java",
    "build.gradle": "Java/Kotlin",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
}

# Entry point files for strategy 7
_ENTRY_POINT_FILES = {
    "main.go", "main.py", "main.rs", "main.ts", "main.js",
    "app.py", "app.ts", "app.js",
    "index.ts", "index.js",
}

# Language label for entry point files
_ENTRY_POINT_LANG = {
    ".go": "Go", ".py": "Python", ".rs": "Rust",
    ".ts": "TypeScript", ".js": "JavaScript",
}

# Pattern name -> purpose mapping for strategy 3
_PATTERN_PURPOSE = {
    "REST API": "API endpoints",
    "GraphQL": "GraphQL API",
    "Express middleware": "Express middleware",
    "WebSocket": "WebSocket handlers",
    "file-based routing": "file-based route handlers",
    "Redux store": "Redux state management",
    "Zustand store": "Zustand state management",
    "MobX store": "MobX state management",
    "ORM (Prisma)": "Prisma data access layer",
    "ORM (SQLAlchemy)": "SQLAlchemy data access layer",
    "ORM (Drizzle)": "Drizzle data access layer",
    "DI container": "dependency injection setup",
}


def _strategy_readme(folder: FolderInfo) -> str:
    """Strategy 1: Infer purpose from README summary keywords."""
    summary = folder.readme_summary.lower()
    if not summary:
        return ""
    for keyword, purpose in _README_PURPOSE_KEYWORDS.items():
        if keyword in summary:
            return purpose
    return ""


def _strategy_manifest(folder: FolderInfo) -> str:
    """Strategy 2: Detect application type from manifest + entry point."""
    file_names = {f.name for f in folder.files}
    lang = ""
    for manifest, lang_name in _MANIFEST_PURPOSE.items():
        if manifest in file_names:
            lang = lang_name
            break
    if not lang:
        return ""
    # Check for entry point to distinguish app vs library
    has_entry = any(f.name in _ENTRY_POINT_FILES for f in folder.files)
    if has_entry:
        return f"{lang} application"
    return f"{lang} project"


def _strategy_patterns(folder: FolderInfo) -> str:
    """Strategy 3: Use detected architectural patterns."""
    for pattern in folder.detected_patterns:
        if pattern in _PATTERN_PURPOSE:
            return _PATTERN_PURPOSE[pattern]
    return ""


def _strategy_role_distribution(folder: FolderInfo) -> str:
    """Strategy 4: If 70%+ files share a specific role, use that role as folder purpose."""
    if not folder.files:
        return ""
    role_counts: Dict[str, int] = {}
    for f in folder.files:
        role_counts[f.role] = role_counts.get(f.role, 0) + 1
    total = len(folder.files)
    # Map file roles to folder-level purpose labels
    _role_to_purpose = {
        "configuration": "configuration files",
        "data/configuration": "configuration files",
        "documentation": "documentation",
        "test file": "test files",
        "stylesheet": "stylesheets",
        "SQL query/migration": "database migrations",
        "type definitions": "type definitions",
        "middleware": "middleware",
        "route definitions": "route definitions",
        "service implementation": "service implementations",
        "data model/schema": "data models",
        "error definitions": "error definitions",
        "custom hook": "custom hooks",
        "request controller": "request controllers",
    }
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        if role == "source file":
            continue  # too generic
        if count / total >= 0.7:
            return _role_to_purpose.get(role, role)
    return ""


def _split_camel_case(name) -> List[str]:
    """Split CamelCase/camelCase into lowercase words. 'NewDNSError' -> ['new', 'dns', 'error']."""
    if not isinstance(name, str):
        # This indicates a problem upstream where a non-string is passed to this function
        # This could happen if `export_item` itself was passed instead of `export_item["name"]`
        print(f"ERROR: _split_camel_case received non-string input: {name!r}", file=sys.stderr)
        return []
    # Insert space before uppercase runs: 'NewDNSError' -> 'New DNS Error'
    parts = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)
    parts = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', parts)
    # Also split on underscores
    return [w.lower() for w in re.split(r'[\s_]+', parts) if w]


def _strategy_export_keywords(folder: FolderInfo) -> str:
    """Strategy 5: Analyze export names for domain clues (whole-word matching)."""
    all_exports: List[str] = []
    for f in folder.files:
        all_exports.extend(f.exports)
    if not all_exports:
        return ""

    # Split CamelCase exports into individual words for whole-word matching
    words = set()
    for export_item in all_exports:
        words.update(_split_camel_case(export_item["name"]))

    # Check for domain-specific word presence
    clues = [
        ({"repo", "repository"}, "database repository implementations"),
        ({"service", "services"}, "business logic service implementations"),
        ({"model", "models"}, "data models and schemas"),
        ({"handler", "handlers"}, "API request handlers"),
        ({"UUID", "uuid"}, "UUID generation utilities"),
        ({"error", "err", "errors", "errs"}, "error handling"),
        ({"handler", "handle", "handlers"}, "request handlers"),
        ({"middleware"}, "middleware"),
        ({"uuid", "uuids", "guid"}, "UUID generation utilities"),
        ({"batch", "bulk", "upsert"}, "batch database operations"),
        ({"seed", "seeds", "populate", "fixture"}, "data seeding"),
        ({"version", "versioning", "revision"}, "version tracking"),
        ({"auth", "login", "session", "token"}, "authentication"),
        ({"cache", "cached", "caching"}, "caching"),
        ({"log", "logger", "logging"}, "logging"),
        ({"config", "setting", "option"}, "configuration management"),
        ({"validate", "validator", "schema"}, "validation"),
        ({"route", "router", "endpoint"}, "routing"),
        ({"test", "mock", "stub"}, "testing utilities"),
        ({"parse", "parser", "decode", "encode"}, "parsing utilities"),
        ({"render", "template", "view"}, "rendering/templates"),
        ({"store", "repository", "dao"}, "data access"),
        ({"queue", "publish", "subscribe", "consumer"}, "message queue"),
        ({"worker", "job"}, "background jobs"),
        ({"notify", "notification", "email", "sms"}, "notifications"),
        ({"convert", "transform"}, "data transformation"),
        ({"client", "http", "fetch"}, "HTTP client"),
        ({"server", "listen", "serve"}, "server setup"),
    ]
    for match_words, purpose in clues:
        if words & match_words:
            return purpose
    return ""


def _strategy_children_bubble_up(folder: FolderInfo) -> str:
    """Strategy 6: Infer parent purpose from already-enriched children."""
    if not folder.children:
        return ""
    child_purposes = [c.purpose for c in folder.children if c.purpose != "project files"]
    if not child_purposes:
        return ""
    # If all children share the same purpose, the parent is a system for that
    unique = set(child_purposes)
    if len(unique) == 1:
        base = unique.pop()
        if not base.endswith("system"):
            return f"{base} system"
        return base
    # If majority share a theme, use the most common
    purpose_counts: Dict[str, int] = {}
    for p in child_purposes:
        purpose_counts[p] = purpose_counts.get(p, 0) + 1
    most_common = max(purpose_counts, key=lambda k: purpose_counts[k])
    if purpose_counts[most_common] / len(child_purposes) >= 0.6:
        return f"{most_common} system"
    return ""


def _strategy_entry_point(folder: FolderInfo) -> str:
    """Strategy 7: Leaf folder with an entry point file."""
    if folder.children:
        return ""  # not a leaf
    for f in folder.files:
        if f.name in _ENTRY_POINT_FILES:
            suffix = Path(f.name).suffix
            lang = _ENTRY_POINT_LANG.get(suffix, "")
            if lang:
                return f"{lang} executable entry point"
            return "executable entry point"
    return ""


# Ordered list of enrichment strategies
_ENRICHMENT_STRATEGIES = [
    _strategy_readme,
    _strategy_manifest,
    _strategy_patterns,
    _strategy_entry_point,          # before role_distribution: prefer specific label for leaf folders
    _strategy_role_distribution,
    _strategy_export_keywords,
    _strategy_children_bubble_up,
]


def _enrich_purposes(root: FolderInfo) -> None:
    """
    Walk the folder tree bottom-up (children first) and refine any folder
    still labeled "project files" by trying enrichment strategies in order.
    First non-empty result wins.
    """
    # Recurse into children first (bottom-up)
    for child in root.children:
        _enrich_purposes(child)

    # Only refine folders with the generic fallback label
    if root.purpose != "project files":
        return

    for strategy in _ENRICHMENT_STRATEGIES:
        result = strategy(root)
        if result:
            root.purpose = result
            return


def scan_project_recursive(
    project_root: Path,
    project_config: ProjectConfig,
    max_depth: int = 4,
    min_significance: int = 1,
) -> List[FolderInfo]:
    """
    Recursively scan a project directory tree and return folder info for
    each significant folder (those with at least min_significance meaningful
    files or subfolders).

    Returns a flat list of FolderInfo objects, one per significant folder.
    Backward-compatible entry point.
    """
    ctx = scan_project(project_root, project_config, max_depth=max_depth, min_significance=min_significance)
    return ctx.flat


def scan_project(
    project_root: Path,
    project_config: ProjectConfig,
    max_depth: int = 4,
    min_significance: int = 1,
    extract_signatures: bool = True,
) -> ScanContext:
    """
    Scan the project once and return a ScanContext with:
    - root: tree-structured FolderInfo
    - flat: flat list of all significant FolderInfo objects
    - by_path: dict mapping relative path -> FolderInfo
    - prompt_text: pre-formatted text for AI prompts
    """
    exclusion_ctx = get_exclusion_context(project_root)
    flat_results: List[FolderInfo] = []
    by_path: Dict[str, FolderInfo] = {}

    def _walk(
        folder: Path,
        depth: int,
    ) -> Optional[FolderInfo]:
        if depth > max_depth:
            return None

        info = scan_folder(folder, project_root, exclusion_ctx,
                           extract_signatures=extract_signatures)
        if info is None:
            return None

        # Recurse into subfolders and attach as children
        for subfolder_name in info.subfolders:
            child_path = folder / subfolder_name
            child_info = _walk(
                child_path,
                depth + 1,
            )
            if child_info is not None:
                info.children.append(child_info)

        # A folder is "significant" if it has enough content
        is_significant = (
            info.file_count >= min_significance or len(info.subfolders) >= min_significance
        )

        if is_significant:
            flat_results.append(info)
            path_key = info.path if info.path else "(root)"
            by_path[path_key] = info

        return info

    root = _walk(
        project_root,
        0,
    )
    if root is None:
        root = FolderInfo(name="root", path="", purpose="project root")
    else:
        root.purpose = "project root"  # always label the root explicitly

    _enrich_purposes(root)  # bottom-up refinement of generic "project files" labels

    prompt_text = format_tree_for_prompt(root)

    return ScanContext(
        root=root,
        flat=flat_results,
        by_path=by_path,
        prompt_text=prompt_text,
    )


def format_tree_for_prompt(
    root: FolderInfo,
    max_depth: int = 4,
    max_lines: int = 200,
) -> str:
    """
    Format tree-structured FolderInfo into a concise text representation
    suitable for inclusion in an AI prompt. Recursively walks the tree.
    """
    lines: List[str] = []
    lines.append("## Project File Structure\n")

    def _format_node(folder: FolderInfo, depth: int) -> None:
        if len(lines) >= max_lines:
            return
        if depth > max_depth:
            return

        indent = "  " * depth
        folder_display = folder.path if folder.path else "(root)"
        lines.append(f"{indent}**{folder_display}/** - {folder.purpose}")

        # List key files (limit to most important)
        key_files = [f for f in folder.files if f.role not in ("source file",)]
        if key_files:
            for f in key_files[:8]:
                export_str = ""
                if f.exports:
                    exports_display = []
                    for exp_item in f.exports[:5]: # Limit to 5 for brevity
                        exp_name = exp_item["name"]
                        exp_explanation = exp_item.get("explanation")
                        if exp_explanation:
                            exports_display.append(f"{exp_name}: {exp_explanation}")
                        else:
                            exports_display.append(exp_name)
                    export_str = f" [exports: {'; '.join(exports_display)}]"
                lines.append(f"{indent}  - `{f.name}` ({f.role}){export_str}")
            if len(key_files) > 8:
                lines.append(f"{indent}  - ... +{len(key_files) - 8} more notable files")

        # File count summary
        source_count = folder.file_count - len(key_files) if folder.file_count > len(key_files) else 0
        if source_count > 0:
            lines.append(f"{indent}  ({source_count} other source files)")

        # Detected patterns
        if folder.detected_patterns:
            lines.append(f"{indent}  Patterns: {', '.join(folder.detected_patterns)}")

        # Key dependencies
        if folder.key_dependencies:
            deps_str = ", ".join(folder.key_dependencies[:10])
            lines.append(f"{indent}  Dependencies: {deps_str}")

        lines.append("")

        # Recurse into children
        for child in folder.children:
            _format_node(child, depth + 1)

    _format_node(root, 0)

    if len(lines) >= max_lines:
        lines.append("... (structure truncated for brevity)")

    return "\n".join(lines)


# Keep old name as alias for backward compat
def format_scan_for_prompt(
    folders: List[FolderInfo],
    max_lines: int = 150,
) -> str:
    """
    Format scanned folder info into a concise text representation.
    Backward-compatible wrapper. Prefers tree-based formatting if
    folders have children populated.
    """
    if not folders:
        return "(No project structure detected)"

    # If the first folder looks like a root with children, use tree format
    if folders and folders[0].children:
        return format_tree_for_prompt(folders[0], max_lines=max_lines)

    # Fallback: flat format (legacy)
    lines: List[str] = []
    lines.append("## Project File Structure\n")

    for folder in folders:
        indent = "  " * folder.path.count("/") if folder.path else ""
        folder_display = folder.path if folder.path else "(root)"

        lines.append(f"{indent}**{folder_display}/** - {folder.purpose}")

        if folder.subfolders:
            sub_list = ", ".join(folder.subfolders[:15])
            if len(folder.subfolders) > 15:
                sub_list += f", ... (+{len(folder.subfolders) - 15} more)"
            lines.append(f"{indent}  Subfolders: {sub_list}")

        key_files = [f for f in folder.files if f.role not in ("source file",)]
        if key_files:
            for f in key_files[:8]:
                lines.append(f"{indent}  - `{f.name}` ({f.role})")
            if len(key_files) > 8:
                lines.append(f"{indent}  - ... +{len(key_files) - 8} more notable files")

        if folder.file_count > len(key_files):
            remaining = folder.file_count - len(key_files)
            if remaining > 0:
                lines.append(f"{indent}  ({remaining} other source files)")

        if folder.detected_patterns:
            lines.append(f"{indent}  Patterns: {', '.join(folder.detected_patterns)}")

        lines.append("")

        if len(lines) >= max_lines:
            lines.append("... (structure truncated for brevity)")
            break

    return "\n".join(lines)


def format_scan_for_template(
    folders: List[FolderInfo],
) -> str:
    """
    Format scanned folder info as a markdown structure description
    for template-based (non-AI) generation.
    """
    if not folders:
        return ""

    lines: List[str] = []
    lines.append("## Project Structure\n")
    lines.append("This project contains the following structure:\n")

    for folder in folders:
        folder_display = folder.path if folder.path else "(root)"
        depth = folder.path.count("/") if folder.path else 0
        prefix = "  " * depth + "- "

        lines.append(f"{prefix}**`{folder_display}/`** - {folder.purpose}")

        # Show subfolders with purpose from children if available
        if folder.children:
            for child in folder.children[:10]:
                lines.append(f"{prefix}  - `{child.name}/` ({child.purpose})")
        else:
            for sub in folder.subfolders[:10]:
                sub_purpose = FOLDER_PURPOSE_MAP.get(sub.lower(), "")
                purpose_str = f" ({sub_purpose})" if sub_purpose else ""
                lines.append(f"{prefix}  - `{sub}/`{purpose_str}")

        # Show key config/entry files
        key_files = [
            f for f in folder.files
            if f.role not in ("source file", "stylesheet", "documentation")
        ]
        for f in key_files[:5]:
            lines.append(f"{prefix}  - `{f.name}` - {f.role}")

    lines.append("")
    return "\n".join(lines)


def format_folder_description(
    folder: FolderInfo,
) -> str:
    """
    Generate a brief structural description for a single folder.
    Uses actual child FolderInfo objects when available, falls back to
    FOLDER_PURPOSE_MAP for backward compat.
    """
    lines: List[str] = []
    folder_display = folder.path if folder.path else "root"
    lines.append(f"# {folder.name.title()} - {folder.purpose}\n")
    lines.append(f"**Path:** `{folder_display}/`\n")

    if folder.readme_summary:
        lines.append(f"> {folder.readme_summary}\n")

    if folder.children:
        lines.append("## Contents\n")
        for child in folder.children:
            lines.append(f"- **`{child.name}/`** - {child.purpose}")
        lines.append("")
    elif folder.subfolders:
        lines.append("## Contents\n")
        for sub in folder.subfolders:
            sub_purpose = FOLDER_PURPOSE_MAP.get(sub.lower(), "project files")
            lines.append(f"- **`{sub}/`** - {sub_purpose}")
        lines.append("")

    if folder.files:
        lines.append("## Key Files\n")
        for f in folder.files[:15]:
            if f.role != "source file":
                export_str = ""
                if f.exports:
                    export_str = f" (exports: {', '.join(f.exports[:5])})"
                lines.append(f"- `{f.name}` - {f.role}{export_str}")
        source_files = [f for f in folder.files if f.role == "source file"]
        if source_files:
            lines.append(f"- {len(source_files)} source file(s)")
        lines.append("")

    if folder.public_api:
        lines.append(f"**Public API:** {', '.join(folder.public_api[:10])}\n")

    if folder.detected_patterns:
        lines.append(f"**Patterns:** {', '.join(folder.detected_patterns)}\n")

    if folder.key_dependencies:
        lines.append(f"**Dependencies:** {', '.join(folder.key_dependencies[:10])}\n")

    return "\n".join(lines)


def generate_deterministic_folder_doc(folder: FolderInfo) -> str:
    """
    Generate a deterministic (no LLM needed) structural documentation
    for a folder. This is Tier 1 content -- always accurate, never hallucinated.

    Includes: purpose, children listing, per-file subsections with descriptions
    and exports, detected patterns, dependencies, and readme summary.
    """
    lines: List[str] = []
    folder_display = folder.path if folder.path else "root"
    title = folder.name.title() if folder.name != "root" else "Project Root"

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Path:** `{folder_display}/`")
    lines.append(f"**Purpose:** {folder.purpose}")

    if folder.ai_folder_summary:
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(folder.ai_folder_summary)
    
    lines.append("")

    if folder.readme_summary:
        lines.append(f"> {folder.readme_summary}")
        lines.append("")

    # Children / subfolders
    children_to_show = folder.children if folder.children else None
    if children_to_show:
        lines.append("## Subfolders")
        lines.append("")
        for child in children_to_show:
            detail_parts = []
            if child.file_count:
                detail_parts.append(f"{child.file_count} files")
            if child.detected_patterns:
                detail_parts.append(", ".join(child.detected_patterns))
            detail = f" ({'; '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"- **`{child.name}/`** - {child.purpose}{detail}")
        lines.append("")
    elif folder.subfolders:
        lines.append("## Subfolders")
        lines.append("")
        for sub in folder.subfolders:
            sub_purpose = FOLDER_PURPOSE_MAP.get(sub.lower(), "project files")
            lines.append(f"- **`{sub}/`** - {sub_purpose}")
        lines.append("")

    # Files: merge key files and source files into a single sorted list
    # (key files first, then source files)
    key_files = [f for f in folder.files if f.role != "source file"]
    source_files = [f for f in folder.files if f.role == "source file"]
    all_files = key_files + source_files

    # Show up to 30 files with full ### subsections
    detail_files = all_files[:30]
    overflow_files = all_files[30:]

    if detail_files:
        lines.append("## Files")
        lines.append("")

        for i, f in enumerate(detail_files):
            lines.append(f"### `{f.name}`")
            lines.append(f"**Role:** {f.role} | **Lines:** {f.size_lines}")
            lines.append("")

            if f.description:
                lines.append(f.description)
                lines.append("")

            if f.exports:
                lines.append("**Key Exports:**")
                for exp_item in f.exports[:10]:
                    exp_name = exp_item["name"]
                    exp_explanation = exp_item.get("explanation")
                    if exp_explanation:
                        lines.append(f"- `{exp_name}` - {exp_explanation}")
                    else:
                        lines.append(f"- `{exp_name}`")
                lines.append("")

            # Add separator between files, but not after the last one
            if i < len(detail_files) - 1:
                lines.append("---")
                lines.append("")

    # Overflow files in compact bullet list
    if overflow_files:
        lines.append("")
        lines.append("## Other Files")
        lines.append("")
        for f in overflow_files:
            size_str = f", {f.size_lines} lines" if f.size_lines else ""
            lines.append(f"- `{f.name}` - {f.role}{size_str}")
        lines.append("")

    # Patterns
    if folder.detected_patterns:
        lines.append("## Detected Patterns")
        lines.append("")
        for p in folder.detected_patterns:
            lines.append(f"- {p}")
        lines.append("")

    # Dependencies
    if folder.key_dependencies:
        lines.append("## Key Dependencies")
        lines.append("")
        for dep in folder.key_dependencies[:15]:
            lines.append(f"- {dep}")
        lines.append("")

    # Stats
    lines.append("## Stats")
    lines.append("")
    lines.append(f"- Total files: {folder.file_count}")
    if folder.children:
        lines.append(f"- Direct subfolders: {len(folder.children)}")
    elif folder.subfolders:
        lines.append(f"- Direct subfolders: {len(folder.subfolders)}")
    lines.append(f"- Has tests: {'yes' if folder.has_tests else 'no'}")
    lines.append(f"- Has config: {'yes' if folder.has_config else 'no'}")
    lines.append("")

    return "\n".join(lines)
