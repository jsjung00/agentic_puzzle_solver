# agentic_puzzle_solver

TODO steps

- [x] Figure out how to get multion account
- [] Write code to connect to the website
- [x] Define the multi-step algorithm
  - [] Improve the algorithm
- [x] Add json mode
- [] Add debater code
- [] Add verification of json output

- [x] Fix the prompt: the problem is that when you ask it to return the solution in a certain format (and the format is complicated), the reasoning output is much worse
  - [] FIX BUG: agent_contexts are identical across agents...
  - [] Need to use 4omini to summarize the response reasoning and state the final grouping. Token limit?
- [] Take the final outputs with reasoning and groups across agents; use 4o to format into json -> run external verifier -> add ranker and sort the groupings -> get the majority vote (i.e most frequent grouping) to try

- [] (optional) Add together.ai and convert to llama models

  - [] It seems like I can simply use 4o mini and get away with that or just pay the 4o cost
  - [] Add self verification if need be

- [] The model can fail by generating the wrong category theme but have the right group... the judge doesn't check for this
- [] Regenerate multiple plans using different agents and check to see if any of them succeed
- [x] Need to write a check function to ensure formatted thing is json and has no duplicates
- [] Add memory into the GPT
- [] Need to prompt optimize to not return incorrect things

Plan: read a little bit for motivation. Then, use the dude's tool. Then try using other models (sonnet)
