# Global Agent Rules

## 1. Continuous Memory System
You MUST use the continuous memory system to persist learnings for future agents.
1. **Read Before Acting**: Always read `.agents/memory/index.md` and the relevant domain memory files before making architectural, trading strategy, or ML changes.
2. **Update After Task**: At the end of every significant task or conversation, you MUST append any new bugs, insights, strategy failures, or architectural decisions to the appropriate file in `.agents/memory/`. If the domain doesn't exist, create it and update `index.md`.
