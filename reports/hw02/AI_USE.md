# AI-Use Disclosure:

## 1. What I used an AI assistant for and what I did myself

I used an AI assistant to understand the homework requirements, organize my implementation and get help when I was stuck. I ran the web application and local model, tested the required operations, completed the experiments, checked the results and prepared the report.

## 2. One unsuitable AI output or independently verified item

During the adversarial test, the Reviewer rejected an output that already followed the required schema. It added requirements for brand and lot tags even though the homework only required exactly three valid tags and a summary of no more than 25 words.

## 3. How I detected or verified it

I found the problem by reading the saved traces and comparing the Planner output with the Pydantic rules and the assignment. The Planner produced three valid tags and a summary under 25 words, but the Reviewer still rejected it because of extra requirements that were not part of the homework.

## 4. What I changed and why it works now

I changed the prompts so the recall text was treated only as data and the Reviewer checked factual support instead of adding extra formatting rules. I kept the Pydantic checks and the retry limit. After the change, all five adversarial runs completed successfully and none reached the turn limit.
