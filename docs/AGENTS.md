# Development rules

The user is a beginner in application development.

## Technology
- Use Python.
- Use Streamlit for the prototype UI.
- Do not introduce React, TypeScript, JavaScript frameworks, or databases unless explicitly requested.
- Keep calculation logic independent from the UI.

## Development style
- Work on one small phase at a time.
- Do not implement features that were not requested.
- Before large changes, explain the plan.
- Prefer simple code over elaborate abstractions.
- Do not rewrite unrelated files.

## Testing
- Add pytest tests for calculation logic.
- Run existing tests after every meaningful change.
- Never modify expected test values merely to make a failing test pass.
- If a test fails, investigate the implementation first.

## Accuracy
- Do not guess Genshin or Akasha mechanics.
- Keep confirmed specifications and assumptions separate.
- Mark unknown behavior explicitly.
- Akasha compatibility must be validated against real Akasha results.

## Git
- Do not commit unless explicitly requested.
- Before a commit, summarize the changed files and test results.

# Project domain

This project is a Genshin Impact artifact optimizer focused on Hu Tao.

## Terms

- Hu Tao / 胡桃:
  The only supported character in the initial prototype.

- Artifact / 聖遺物:
  Equipment consisting of five slots:
  Flower, Plume, Sands, Goblet, Circlet.

- Akasha:
  akasha.cv.
  The final goal is to reproduce one specific Hu Tao leaderboard score
  and estimate hypothetical rankings.

- Dust of Enlightenment / 聖啓の塵:
  An artifact substat reconstruction system.
  Exact mechanics must be taken from docs/dust_spec.md,
  not from model memory.

## Accuracy rule

Do not assume numerical Genshin or Akasha mechanics from model knowledge.
Use project specification files and verified sources.

If a mechanic is uncertain, do not guess.
Record it as unresolved.