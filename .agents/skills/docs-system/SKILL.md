---
name: docs-system
description: How docs/ is organised and kept current. Use when writing or updating a doc, when a change alters how the product or platform behaves, or when deciding whether content belongs in docs/, a skill, or AGENTS.md.
---

# Docs system

## What goes where

| Place | Holds | Reader asks |
| --- | --- | --- |
| `AGENTS.md` | Entry point: the project in a few lines, repo map, hard rules, skills index. | "Where do I start, and what must I never break?" |
| `.agents/skills/` | How to do one task: steps, commands, gotchas. | "How do I do X here?" |
| `docs/` | How the product and platform work and why: concepts, flows, data, decisions. For humans and agents. | "How does X work?" |
| Folder `README.md` | How to run and check that folder's code. | "How do I start this?" |

A doc explains; a skill instructs. If a page has numbered steps an agent follows to change code, it is a skill. If it describes behaviour someone needs before deciding anything, it is a doc. Link across rather than copy.

## Layout

```
docs/
├── README.md                  # index: one line per doc
└── <topic>/
    ├── README.md              # overview of the topic
    └── <subtopic>.md          # added when the overview passes ~200 lines
```

- The agentic platform is the main topic: `docs/agentic-platform/`.
- A new topic gets a folder with a `README.md` and a line in `docs/README.md`.
- Link to code by relative path (`../../marketplace/backend/app/pricing.py`) so the reader can check the source.
- Unknown or pending parts get a heading with `> TODO:` and a line on what will fill it. Fill or remove the TODO when the answer lands.

## Keeping it current

1. When your change alters behaviour a doc describes (a flow, a price rule, an API, what the agent may do), update that doc in the same commit.
2. Describe what the code does now; mark planned work as **Planned**.
3. Facts the code already states (env var lists, endpoint schemas) stay in the code or its README; the doc links there.
4. Public repo: no secrets, tokens, personal emails, or phone numbers.
