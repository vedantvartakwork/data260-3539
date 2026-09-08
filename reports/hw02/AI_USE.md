# Homework 2 AI Use

## 1. What I used an AI assistant for and what I did myself

I used an AI assistant to help plan the implementation, write and debug the FastAPI and LangGraph code, create the experiment scripts, and organize the report. I ran the application and model locally, captured the screenshots, checked the outputs, and reviewed the files against the assignment requirements.

## 2. One output that was wrong or one item I independently verified

During the adversarial test, the reviewer incorrectly claimed that a valid summary was over 40 words and invented requirements for mandatory brand and lot tags. This caused all five adversarial runs to reach the turn ceiling even though the planner output passed the required Pydantic schema.

## 3. How I verified it

I detected the problem by saving every run and reading the node traces in `reports/hw02/raw/adversarial_runs_before_fix.json`. The trace showed that the planner produced exactly three valid tags and a summary under 25 words, but the reviewer still rejected it using requirements copied from the embedded adversarial instruction.

## 4. What I changed and why it works now

I treated the recall text as untrusted data, removed instruction-like sentences before sending it to either model node, and narrowed the reviewer prompt to factual support instead of invented formatting rules. I kept Pydantic validation and the bounded retry ceiling. After the change, all five repeated adversarial runs completed successfully on the first attempt.
