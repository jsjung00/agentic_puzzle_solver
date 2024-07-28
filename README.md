# Agentic multi-step reasoning with LLMs

Agents are known to be "bad at reasoning" and puzzles. But what about textual puzzles? And how can we develop agentic systems that can do better reasoning?

This project proposes a method to improve reasoning and evaluates on the popular NYT Connections games.

The method

- Incorporates multiagent debate; implemented https://openreview.net/pdf?id=zj7YuTE4t8#page=12&zoom=100,409,81 Improving Factuality and Reasoning in Language Models by (Du et al. 2023)
- Incorporates external verifiers and allows for self-reflection
- Uses a LLM as a ranker to rank candidate solutions
- Returns the most promising candidate using ranked majority voting system
