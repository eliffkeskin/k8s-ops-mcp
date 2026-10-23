## PR Review Agent

An LLM-based code review step that runs on every pull request. The model
runs locally through Ollama, the workflow runs on a self-hosted runner, so
no code leaves the machine.

### Flow

```
PR opened or updated
  -> GitHub Actions workflow (.github/workflows/pr-review.yaml, self-hosted runner)
  -> tools/pr_review/review.py fetches the PR diff via the GitHub API
  -> diff is sent to qwen2.5-coder:7b through Ollama (OpenAI-compatible API)
  -> review is posted back to the PR as a comment
  -> a human reads it and decides whether to merge
```

### Design decisions

- **Comment only, never merge.** The agent has write access to PR comments
  and nothing else. Merging stays with a human.
- **Local model.** Ollama serves `qwen2.5-coder:7b` on the runner host. The
  client uses the OpenAI-compatible endpoint, so switching to vLLM or any
  other server is a `OLLAMA_BASE_URL` and `REVIEW_MODEL` change, not a code
  change.
- **Self-hosted runner.** Keeps the diff and the model on infrastructure we
  control. Hosted runners also work: install Ollama inside the job and pull
  a smaller model.
- **temperature=0.** Small models drift between runs on the same input;
  deterministic sampling makes the output reproducible enough to compare.
- **Bounded by design.** One model call per PR, no retries, no tool use. The
  agent cannot loop or act on the repository.

### Running locally

```bash
export GITHUB_TOKEN=...
export GITHUB_REPOSITORY=eliffkeskin/k8s-ops-mcp
export OLLAMA_BASE_URL=http://localhost:11434/v1   # default
export REVIEW_MODEL=qwen2.5-coder:7b               # default

python3 tools/pr_review/review.py <pr-number>            # posts a comment
python3 tools/pr_review/review.py <pr-number> --dry-run  # prints the review, posts nothing
```

### Known limitations

- A 7B model misses some issues and occasionally comments on non-code
  files. Quality depends heavily on the prompt.
- No evaluation set yet. Next step: a small golden set of PRs with known
  issues and a hit-rate measurement, plus tracing (Langfuse).