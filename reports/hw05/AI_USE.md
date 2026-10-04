# Homework 5 AI Use

1. I used an AI assistant to help translate the assignment checklist into a cumulative implementation plan, draft code for the FastAPI/Redux/MCP integration, and create repeatable validation scripts. I independently reviewed the requirements, ran the tests, inspected the generated artifacts and live outputs, and will select and capture the final UI and MCP Inspector evidence used in the report.

2. I independently found that my first Home-page implementation deleted a recall directly from the record card. That bypassed the assignment's required delete-confirmation UI even though the API operation itself worked.

3. I detected the issue by tracing the Home button to its Redux dispatch and comparing the rendered flow with the rubric's separate Delete UI requirement. I reproduced it locally: clicking Delete immediately issued the request instead of first showing the selected record and a confirmation action.

4. I changed the Home button to navigate to `/delete/:id`, added a confirmation page that loads the selected record, and dispatches `deleteRecall` only after explicit confirmation. I verified the confirmation screen, the success message, and the record's removal from MySQL.
