# Homework 5 AI Use

1. I used an AI assistant to help translate the assignment checklist into a cumulative implementation plan, draft code for the FastAPI/Redux/MCP integration, and create repeatable validation scripts. I independently reviewed the requirements, ran the tests, inspected the generated artifacts and live outputs, and will select and capture the final UI and MCP Inspector evidence used in the report.

2. I independently verified that the supplied demo's relationship route order was unsuitable to copy directly: a dynamic `/{course_id}` route appeared before `/by-instructor/{instructor_id}`, which can cause the static relationship path to be parsed as an integer ID.

3. I detected the issue by reading the complete demo source after extracting the assignment requirements, then comparing FastAPI's declaration-order matching behavior with the required relationship endpoint. I also used production builds and offline tests rather than assuming generated code was correct.

4. I declared the static `/by-manufacturer/{manufacturer_id}` relationship route before the dynamic `/{recall_id}` route. This makes the intended relationship path unambiguous. The cumulative test suite and 13-check live API flow verify that the new route coexists with individual recall lookup.
