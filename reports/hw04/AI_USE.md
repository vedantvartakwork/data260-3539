# AI-Use Disclosure

## 1. What I used assistance for and what I did myself

I used an AI assistant to help organize the assignment requirements, draft parts of the React, FastAPI, MySQL, and RAG implementation, and review the repository structure. I checked the assignment again, ran the application and experiments, tested the required operations, reviewed the saved outputs, captured the screenshots, and checked the final code and report.

## 2. One unsuitable output or independently verified item

For the question asking what exact font size the FDA requires on every grocery recall poster, the no-RAG configuration claimed that the FDA requires at least 18-point text. That answer was not supported by any of the provided documents.

## 3. How I detected or verified it

I compared the answer with the retrieved chunks and searched the five-document corpus for a supporting font-size requirement. The documents did not provide one, so I marked the no-RAG response as an incorrect hallucination in the evaluation results.

## 4. What I changed and why it works now

I added context-grounding instructions, source labels, and the required exact refusal for questions that the retrieved documents do not support. The context-RAG configuration then returned "I cannot answer this question from the provided documents" for both unsupported questions and achieved 6/6 for correctness, grounding, and format compliance.
