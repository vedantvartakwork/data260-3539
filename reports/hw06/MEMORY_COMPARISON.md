# MongoDB Memory vs. File Memory

| Criterion | MongoDB memory | `MEMORY.md` file memory |
|---|---|---|
| Inspectability | Queryable collections expose messages, summaries, timestamps, embeddings, and indexes. | Human-readable and diffable in an editor or Git. |
| Restart persistence | Persists across API/model restarts while the MongoDB volume remains. | Persists across all process restarts and travels with the repository. |
| Scalability | Handles many users/sessions, indexes, aggregation, and retrieval. | Best for a small set of durable project facts and instructions. |
| Must-not-forget facts | Strong when backed up and retrieved correctly, but less visible to humans. | Best for small critical constraints because humans can audit and version them. |

Use MongoDB for high-volume conversational and episodic memory. Use `AGENT.md` and
`MEMORY.md` for compact, must-not-forget project rules. The hybrid prompt provides
both scalable retrieval and directly inspectable durable constraints.
