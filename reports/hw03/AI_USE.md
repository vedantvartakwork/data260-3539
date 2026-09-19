# AI-Use Disclosure:

## 1. What I used assistance for and what I did myself

I used an assistant to help organize the assignment requirements, draft the first version of the authentication and retrieval scripts, and review the repository structure. I checked the assignment again, ran the application and experiments, verified the outputs, captured the screenshots, and reviewed the final code and report.

## 2. One unsuitable output or independently verified item

One draft of the metrics helper treated the first retriever row as the top-1 cosine value. That was not precise enough for this assignment because the instructions define top-1 as the highest explicit cosine similarity among the returned top-k chunks.

## 3. How I detected or verified it

I found the issue by rereading the metric definition in the homework PDF and comparing it with the saved per-query cosine values. I also recomputed the table directly from the JSONL file and checked the result against the terminal output.

## 4. What I changed and why it works now

I changed the summary calculation to take the maximum explicit cosine value from each question's top-k results before averaging across the five questions. This matches the definition in the assignment and keeps the reported metrics reproducible from the raw files.
