# Mastering AI coding agent rules for Cursor and Claude Code

**The most effective AI coding rules are specific, example-driven, and maintained like production code.** Research from Anthropic, community practitioners, and security organizations reveals that rules with concrete code examples achieve **94% adherence** compared to 42% for description-only rules. Both Cursor and Claude Code have evolved sophisticated rule systems in 2024-2025, with Cursor adopting the new `.mdc` format and Claude Code using a hierarchical `CLAUDE.md` approach. The core principle across both tools: every word must earn its place in context.

## How the two rule systems actually work

Cursor and Claude Code take fundamentally different approaches to custom instructions, though both aim to inject project-specific guidance into the AI's context window.

**Cursor's rule system** has evolved significantly. The legacy `.cursorrules` file in the project root is now deprecated in favor of a more powerful system using `.cursor/rules/*.mdc` files. MDC (Markdown Domain Configuration) files use YAML frontmatter to control when rules activate:

```yaml
---
description: TypeScript service layer patterns
globs:
  - src/services/**/*.ts
alwaysApply: false
---
# Service Guidelines
- Use Result<T> for error handling
- Inject dependencies via constructor
```

Cursor supports four rule types: **Always** (applied to every context), **Auto Attached** (triggered by glob patterns), **Agent Requested** (AI decides based on description), and **Manual** (requires explicit `@ruleName` mention). Rule contents load at the start of model context, directly influencing all responses.

**Claude Code's CLAUDE.md system** uses a hierarchical approach with clear precedence. Files load in order: Enterprise policy (IT-managed, cannot be overridden) → Project memory (`./CLAUDE.md`) → Local project memory (`./CLAUDE.local.md`) → User memory (`~/.claude/CLAUDE.md`). Claude Code also supports a `.claude/rules/` directory for modular organization and recursive discovery of CLAUDE.md files in parent and child directories.

A critical difference: Claude Code's instruction-following has **diminishing returns**. Research from HumanLayer shows that as instruction count increases beyond ~50 rules, adherence quality decreases uniformly across all instructions. This makes conciseness essential for Claude Code.

## What distinguishes excellent rules from mediocre ones

The research consistently identifies **specificity** and **concrete examples** as the strongest predictors of rule effectiveness.

**Vague instructions fail because AI models are pattern-matching engines.** "Write clean code" matches millions of conflicting patterns from training data. In contrast, "Maximum 50 lines per function, pass linter with zero warnings" provides measurable criteria. Studies show rules with absolute language (ALWAYS, NEVER, MUST) achieve **2.8x higher compliance** than rules with qualifiers like "try" or "prefer."

The most effective pattern is the **❌→✅ format** that shows anti-patterns before correct patterns:

```markdown
## Error Handling

### ❌ WRONG: Silent Failures
```typescript
try {
  return await fetch(`/api/users/${id}`).json();
} catch (error) {
  return null;  // Silent failure—caller can't distinguish errors
}
```

### ✅ CORRECT: Result<T> Pattern
```typescript
async function fetchUser(id: string): Promise<Result<User>> {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) {
      return { success: false, error: `Server error: ${response.status}` };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    logger.error('fetchUser failed', { id, error });
    return { success: false, error: 'Network error' };
  }
}
```
```

Teams using explicit anti-pattern examples saw **35% fewer violations** than those using only positive examples. The mechanism is clear: showing what not to do creates a stronger negative signal than vague prohibitions.

**Information density matters for token economy.** Rules compete for context space with file trees (~2,000 tokens), open files (~10,000 tokens), and conversation history. A well-crafted rule file achieves maximum behavioral impact per token:

| Approach | Tokens | Impact |
|----------|--------|--------|
| Verbose prose explaining coding philosophy | 45 | Minimal |
| Specific rules with examples | 28 | Maximum |

The recommended structure follows a **7-section framework**: Project Context (50-100 words), Technology Stack (versions included), Architecture & Structure, Coding Standards (with examples), Testing Approach, Common Pitfalls, and Commands & Workflow. Keep total length under **500 lines**—larger files should be split into composable modules.

## Configuration best practices for each tool

For **Cursor**, the transition to MDC format unlocks powerful capabilities. Use `alwaysApply: true` sparingly for universal standards like TypeScript strict mode or security requirements. Apply glob patterns for context-specific rules—`**/*.tsx` for React component standards, `src/services/**/*.ts` for service layer patterns. Include verification steps at the end of rules ("Before completing: run typecheck, verify imports, check linting").

A Cursor employee's own rules illustrate the preferred tone: "DO NOT GIVE ME HIGH LEVEL SHIT, IF I ASK FOR FIX OR EXPLANATION, I WANT ACTUAL CODE. Be terse. Suggest solutions I didn't think about. Treat me as an expert. Give the answer immediately." This directness proves more effective than polite, verbose instructions.

For **Claude Code**, the official recommendation from Anthropic emphasizes conciseness. Use the `/init` command to bootstrap a CLAUDE.md file, then refine iteratively. Include bash commands (build, test, lint), code style specifics (ES modules over CommonJS), and workflow instructions (typecheck after changes, run single tests not full suite).

Claude Code supports **import syntax** for modularity: reference `@docs/architecture.md` or `@src/components/auth/LoginForm.tsx` to provide examples without duplicating content. This approach keeps the main CLAUDE.md lean while providing rich context on demand.

The **settings.json** file controls permissions and automation:

```json
{
  "permissions": {
    "allow": ["Bash(npm run lint)", "Bash(npm run test:*)"],
    "deny": ["Read(./.env)", "Read(./secrets/**)"]
  },
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write(*.py)",
      "hooks": [{"type": "command", "command": "python -m black $file"}]
    }]
  }
}
```

## The most common mistakes developers make

**The Encyclopedia trap** treats rules like comprehensive documentation. Most content already exists in AI training data; critical project-specific rules get buried in generic advice. Focus exclusively on what makes your project unique: security constraints, architectural decisions, team conventions, deprecated patterns.

**Stale rules** cause cascading problems. When frameworks update, rules that reference old patterns cause the AI to generate deprecated code. Establish a maintenance cadence: weekly additions for new patterns, monthly removal of deprecated patterns, quarterly full team review.

**Contradictory rules** create unpredictable behavior. If one rule says "prefer interfaces" and another says "use type aliases for unions," the AI arbitrarily chooses. Ask the AI itself to audit your rules for contradictions—it's surprisingly effective at identifying conflicts.

**Over-constrained personas** backfire. Anthropic's research shows "You are a helpful assistant" often outperforms elaborate personas like "You are a world-renowned expert who never makes mistakes and only speaks in technical jargon." The latter creates pressure that degrades response quality.

**Ignoring context window limits** is particularly problematic with Cursor's new rule system. With multiple MDC files, glob patterns, and always-applied rules, context can fill quickly. Monitor the Agent sidebar to see which rules are active—if too many compete for attention, the AI's adherence to any single rule suffers.

## Security considerations that most developers miss

AI-generated code carries significant security risks: **62% contains design flaws or known vulnerabilities** according to Cloud Security Alliance research. The AI reproduces vulnerable patterns from training data without understanding your specific threat model.

Essential security rules to include:

- NEVER commit API keys, passwords, tokens, or .env files
- Validate ALL user input using schema validation (Zod, Pydantic)
- Never use `eval()`, `Function()`, or dynamic code execution
- Parameterized queries only—never string concatenation for SQL
- Hash passwords with bcrypt (minimum 10 rounds)
- Apply Content-Security-Policy headers

**Prompt injection** represents an emerging threat. Malicious content in README files, rule files, or even file names can become injection vectors. Mitigations include applying least privilege to AI tool access, sandboxing command execution, and manually reviewing sources for hidden instructions.

Language-specific considerations matter: C/C++ requires extra caution with memory management and buffer sizes; JavaScript needs protection against `eval()` and prototype pollution; Python should avoid `pickle` with untrusted data and use `subprocess` safely.

## High-quality resources and community examples

The **cursor.directory** community (67,700+ members) serves as the primary hub for sharing Cursor rules, offering browse-by-framework functionality and a rule generator tool. The **awesome-cursorrules** GitHub repository (35,400+ stars) provides categorized templates for every major framework.

For Claude Code, the **steipete/agent-rules** repository (5,100+ stars) provides rules that work for both Claude Code and Cursor, including sophisticated workflow rules for commits, PR reviews, and changelogs. Anthropic's own **engineering blog post** on Claude Code best practices remains the authoritative source.

A highly-rated community rule from Elementor engineers prevents the AI from being a "yes-man":

```markdown
## CRITICAL PARTNER MINDSET
Do not affirm my statements or assume my conclusions are correct.
Question assumptions, offer counterpoints, test reasoning.
Prioritize truth over agreement.

## EXECUTION SEQUENCE (always reply with "Applying rules X,Y,Z")
1. SEARCH FIRST - Use codebase_search until finding similar functionality
2. Investigate deeply, be 100% sure before implementing
```

This pattern addresses a common failure mode: AI assistants that enthusiastically implement whatever the developer suggests, even when the suggestion is flawed.

## Testing and iterating on rules effectively

The gold standard test: select a representative function (50-100 lines), document requirements, delete the implementation, ask AI to regenerate, then diff against the original. **90-100% match** indicates excellent rules; below 70% signals significant gaps requiring rewrite.

Track three metrics: **Adherence Rate** (percentage of AI code following rules without modification—target >90%), **Iteration Count** (review rounds before acceptance—should match or beat manual coding), and **Pattern Compliance** (automated linter/type-checker violations—target zero).

**Rule reinforcement** handles context window limitations. Due to optimization during long conversations, the AI may "forget" rules. Periodically prompt with "remember the rules" or "read the rules again." For critical tasks, start fresh conversations where rules load at the beginning of context.

For multi-project environments, use **dotfiles** to maintain consistent rules across machines. Symlink a shared rules directory to `~/.cursor/rules`, using imports to pull in relevant modules. This enables version control of your AI configuration alongside other development environment settings.

## Advanced patterns for sophisticated workflows

**Custom modes** in Cursor v0.45+ create specialized AI personas. A "Committer" mode enables only Search and Run tools with prompts focused on git conventions. A "Reviewer" mode emphasizes code analysis without edit permissions. Bind these to keyboard shortcuts for rapid context switching.

The **scout pattern** from Simon Willison uses parallel agents for exploration: send one agent to tackle a difficult problem with no intention of landing the code—just to learn the approach. Build proof-of-concept implementations with unfamiliar libraries before committing to real implementation.

**GitButler integration** automates version control of AI work through lifecycle hooks. Each chat automatically creates a new branch; commits generate on task completion with the prompt as the message. This creates clear audit trails of AI contributions and simplifies squashing or reverting changes.

For teams, shared `.cursor/rules/` directories ensure consistent AI behavior across all developers. Studies show **60% reduction** in time spent explaining code standards to new team members and **35% faster** initial PR submissions with fewer revision cycles.

## Conclusion

The most effective AI coding rules share common characteristics: they are **specific rather than vague**, include **concrete code examples**, focus on **project-unique constraints**, and are **maintained like production code**. Both Cursor and Claude Code have matured significantly in 2024-2025, offering sophisticated systems for context-aware rule application.

Key insights that emerge from comprehensive research: rules with examples achieve 2.2x the adherence of description-only rules; the ❌→✅ pattern reduces violations by 35%; context window economy forces ruthless prioritization. Security rules deserve front-loading given that 62% of AI-generated code contains vulnerabilities.

The tooling continues to evolve rapidly. Cursor's MDC format enables modular, glob-triggered rules while Claude Code's hierarchical CLAUDE.md system supports team-wide and personal configurations. An emerging standard called **AGENTS.md** aims to unify configuration across tools, though adoption remains early. Developers who invest in crafting precise, example-rich, well-maintained rules gain compounding advantages as AI capabilities expand.