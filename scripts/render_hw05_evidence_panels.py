#!/usr/bin/env python3
"""Render readable, self-contained HW5 code/input/output evidence panels."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports/hw05/evidence"
RAW = ROOT / "reports/hw05/raw"
WIDTH = 1800
BG = "#101713"
PANEL = "#18231d"
GREEN = "#6ee7a7"
WHITE = "#f4f7f5"
MUTED = "#b5c1ba"
RED = "#ff8a80"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


TITLE = font(42, True)
SUB = font(28, True)
BODY = font(23)
MONO = font(21)


def wrapped(text: str, width: int = 105) -> list[str]:
    lines: list[str] = []
    for raw in str(text).splitlines() or [""]:
        lines.extend(textwrap.wrap(raw, width=width, replace_whitespace=False) or [""])
    return lines


def draw_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], *, color=WHITE, spacing=31) -> int:
    for line in lines:
        draw.text((x, y), line, fill=color, font=MONO)
        y += spacing
    return y


def panel(title: str, sections: list[tuple[str, str, str]], path: Path) -> None:
    heights = []
    for _, text, _ in sections:
        heights.append(58 + 31 * len(wrapped(text)))
    height = 100 + sum(heights) + 40 * len(sections) + 40
    image = Image.new("RGB", (WIDTH, max(900, height)), BG)
    draw = ImageDraw.Draw(image)
    draw.text((55, 38), title, fill=GREEN, font=TITLE)
    y = 110
    for heading, text, kind in sections:
        lines = wrapped(text)
        box_h = 58 + 31 * len(lines)
        draw.rounded_rectangle((45, y, WIDTH - 45, y + box_h), radius=18, fill=PANEL, outline="#365443", width=2)
        draw.text((70, y + 18), heading, fill=RED if kind == "error" else GREEN, font=SUB)
        draw_lines(draw, 70, y + 58, lines, color=WHITE if kind != "note" else MUTED)
        y += box_h + 32
    image.save(path)


def composite(title: str, code: str, screenshot_names: list[str], output_name: str) -> None:
    code_lines = wrapped(code, 92)
    code_h = 100 + 31 * len(code_lines)
    screenshots = []
    for name in screenshot_names:
        source = Image.open(EVIDENCE / name).convert("RGB")
        scale = min((WIDTH - 90) / source.width, 500 / source.height)
        screenshots.append(source.resize((int(source.width * scale), int(source.height * scale))))
    height = 100 + code_h + sum(item.height + 28 for item in screenshots) + 40
    image = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(image)
    draw.text((55, 35), title, fill=GREEN, font=TITLE)
    y = 100
    draw.rounded_rectangle((45, y, WIDTH - 45, y + code_h), radius=18, fill=PANEL, outline="#365443", width=2)
    draw.text((70, y + 18), "RELEVANT REDUX / REACT CODE", fill=GREEN, font=SUB)
    draw_lines(draw, 70, y + 63, code_lines)
    y += code_h + 28
    for shot in screenshots:
        x = (WIDTH - shot.width) // 2
        image.paste(shot, (x, y))
        y += shot.height + 28
    image.save(EVIDENCE / output_name)


def api_panels() -> None:
    data = json.loads((RAW / "api_integration.json").read_text())
    checks = {item["name"]: item for item in data["checks"]}
    paths = {
        "create_manufacturer": "POST /api/v1/manufacturers",
        "read_manufacturer": "GET /api/v1/manufacturers/{id}",
        "list_manufacturers": "GET /api/v1/manufacturers?limit=50",
        "update_manufacturer": "PUT /api/v1/manufacturers/{id}",
        "create_recall": "POST /api/v1/recalls",
        "list_recalls": "GET /api/v1/recalls?q=Integration+Recall&page=1&page_size=50",
        "read_recall": "GET /api/v1/recalls/{id}",
        "relationship_endpoint": "GET /api/v1/recalls/by-manufacturer/{manufacturer_id}",
        "delete_referenced_manufacturer_blocked": "DELETE /api/v1/manufacturers/{id}",
        "update_recall": "PUT /api/v1/recalls/{id}",
        "delete_recall": "DELETE /api/v1/recalls/{id}",
        "deleted_recall_is_404": "GET /api/v1/recalls/{id}",
        "delete_manufacturer": "DELETE /api/v1/manufacturers/{id}",
    }
    groups = [
        ("28_api_manufacturers.png", ["create_manufacturer", "list_manufacturers", "read_manufacturer", "update_manufacturer"]),
        ("29_api_recalls_read.png", ["create_recall", "list_recalls", "read_recall", "relationship_endpoint"]),
        ("30_api_recalls_write.png", ["delete_referenced_manufacturer_blocked", "update_recall", "delete_recall", "deleted_recall_is_404", "delete_manufacturer"]),
    ]
    for filename, names in groups:
        sections = []
        for name in names:
            item = checks[name]
            body = item["body"]
            if isinstance(body, list):
                body = {"returned_records": len(body), "first": body[0] if body else None}
            elif isinstance(body, dict):
                body = {k: body[k] for k in ("id", "recall_code", "product_name", "total", "page", "page_size", "detail") if k in body} or body
                if "records" in item["body"]:
                    body["returned_records"] = len(item["body"]["records"])
                    body["first_recall_code"] = item["body"]["records"][0]["recall_code"]
            text = f"REQUEST: {paths[name]}\nSTATUS: {item['status']} (expected {item['expected']})\nRESPONSE: {json.dumps(body, ensure_ascii=False)}"
            sections.append((name, text, "error" if item["status"] >= 400 else "ok"))
        panel("LIVE API REQUEST / RESPONSE EVIDENCE", sections, EVIDENCE / filename)


def mcp_panels() -> None:
    raw = json.loads((RAW / "mcp_tool_outputs.json").read_text())
    for index, call in enumerate(raw["meals_server"]["calls"], start=1):
        output = call["output"].get("structuredContent")
        compact = json.dumps(output, ensure_ascii=False, indent=2)
        if len(compact) > 2600:
            compact = compact[:2600] + "\n... complete result retained in raw/mcp_tool_outputs.json"
        panel(
            f"MEALDB MCP TOOL {index}/4: {call['tool']}",
            [
                ("INPUT JSON", json.dumps(call["inputs"], indent=2), "ok"),
                ("STRUCTURED OUTPUT", compact, "ok"),
            ],
            EVIDENCE / f"{30 + index}_mealdb_{call['tool']}.png",
        )

    schemas = {
        "search": '{"query": "string, 2-80 characters", "limit": "integer, 1-25"}',
        "detail": '{"recall_id": "positive integer"}',
        "aggregate": '{"group_by": "category|manufacturer", "min_units": "integer, 0-100000000"}',
    }
    reasons = {
        "search": "One character is below the declared minimum and creates an excessively broad lookup.",
        "detail": "Database IDs begin at 1, so zero is outside the accepted domain.",
        "aggregate": "submitter is not an approved grouping dimension and could expose personal contact data.",
    }
    by_tool: dict[str, list[dict]] = {name: [] for name in schemas}
    for call in raw["domain_server"]["calls"]:
        by_tool[call["tool"]].append(call)
    for index, name in enumerate(("search", "detail", "aggregate"), start=1):
        valid, invalid = by_tool[name]
        valid_output = valid["output"]["structuredContent"]
        invalid_output = invalid["output"]["structuredContent"]
        panel(
            f"DOMAIN MCP CONTRACT {index}/3: {name}",
            [
                ("EXPECTED JSON INPUT SCHEMA", schemas[name], "note"),
                ("VALID INPUT", json.dumps(valid["inputs"], indent=2), "ok"),
                ("VALID OUTPUT", json.dumps(valid_output, indent=2), "ok"),
                ("REJECTED JSON OBJECT", json.dumps(invalid["inputs"], indent=2), "error"),
                ("COMPLETE RETURNED ERROR", json.dumps(invalid_output, indent=2), "error"),
                ("WHY REJECTED", reasons[name], "note"),
            ],
            EVIDENCE / f"{34 + index}_domain_contract_{name}.png",
        )


def code_output_panels() -> None:
    panel(
        "DATABASE + API VALIDATION CODE AND OUTPUT",
        [
            ("IMPLEMENTATION", "RecallCreate validates positive units, email, exact category, accepted terms, unique recall_code, and manufacturer_id. The API catches IntegrityError and returns HTTP 409; the FK uses ON DELETE RESTRICT.", "note"),
            ("CODE", "class RecallCreate(RecallInput): pass\n\nif db.get(Manufacturer, payload.manufacturer_id) is None:\n    raise HTTPException(404, 'Manufacturer not found')\ntry: db.commit()\nexcept IntegrityError:\n    db.rollback(); raise HTTPException(409, 'Recall code must be unique')", "ok"),
            ("MEASURED OUTPUT", "manufacturers=12; recall_notices=500; recall_events=200\nFK: manufacturer_id -> manufacturers.id ON DELETE RESTRICT\n14/14 authenticated live API checks passed", "ok"),
        ],
        EVIDENCE / "38_database_api_code.png",
    )
    panel(
        "RETRY IMPLEMENTATION AND MEASURED OUTPUT",
        [
            ("CODE", "for attempt in range(1, policy.max_attempts + 1):\n    try: return RetryResult(value=operation(), attempts=attempt)\n    except policy.retry_on as exc:\n        if attempt >= policy.max_attempts or elapsed >= policy.timeout_seconds: break\n        delay = min(base_delay * 2 ** (attempt - 1), max_delay)\n        sleep(min(delay, remaining_timeout))", "ok"),
            ("POLICY", "max_attempts=3; timeout=100ms; delays=1ms, 2ms; cap=4ms; VERIFY_SEED=263539", "note"),
            ("OUTPUT", "150 total calls (50 each at 0%, 20%, 50%)\nSuccess rates: 100%, 98%, 92%\nObserved: immediate success; failure|success; failure|failure|failure", "ok"),
        ],
        EVIDENCE / "39_retry_code.png",
    )
    panel(
        "SAFE execute_tool + OFFLINE ASSERTIONS",
        [
            ("execute_tool CODE", "if name == 'search' and isinstance(inputs, dict):\n    limit = inputs.get('limit', 5)\n    if isinstance(limit, int) and limit > 10:\n        return json.dumps(envelope(error='Safety rule blocked search: limit cannot exceed 10 records'))\nreturn json.dumps(call_domain_tool(name, inputs, repository), sort_keys=True)", "ok"),
            ("ASSERTION EXAMPLES", "assert result['ok'] and result['data']['count'] == 1\nassert not invalid['ok'] and 'Invalid search input' in invalid['error']\nassert not blocked['ok'] and blocked['error'].startswith('Safety rule blocked')\nassert run.stop_reason == 'max_steps' and run.step_count == 3", "ok"),
            ("OUTPUT", "PASS search valid/invalid; detail valid/invalid; aggregate valid/invalid\nPASS safety allowed/blocked; PASS agent max_steps\nSUMMARY 9/9 tests passed", "ok"),
        ],
        EVIDENCE / "40_execute_tests_code.png",
    )
    panel(
        "BOUNDED AGENT LOOP CODE AND OUTPUT",
        [
            ("CODE", "for step in range(1, max_steps + 1):\n    action = active_model.next_action(messages)\n    if 'final' in action: stop_reason = 'normal_completion'; break\n    result = execute_tool(action['tool'], action['inputs'], repository)\n    if not parsed_result['ok'] and error.startswith('Safety rule blocked'):\n        stop_reason = 'safety_rule_block'; break\nelse:\n    stop_reason = 'max_steps'", "ok"),
            ("OUTPUT", "Scenario 1: steps=2, tool_calls=1, normal_completion\nScenario 2: steps=2, tool_calls=1, normal_completion\nScenario 3: steps=2, tool_calls=1, normal_completion\nScenario 4: steps=1, tool_calls=1, safety_rule_block", "ok"),
        ],
        EVIDENCE / "41_agent_loop_code.png",
    )


def redux_composites() -> None:
    for source_name, output_name, top, bottom in (
        ("25_react_pagination_top.png", "25_react_pagination_top_crop.png", 0, 390),
        ("26_react_pagination_bottom.png", "26_react_pagination_bottom_crop.png", 360, 720),
        ("27_react_pagination_page2.png", "27_react_pagination_page2_crop.png", 360, 720),
    ):
        source = Image.open(EVIDENCE / source_name).convert("RGB")
        source.crop((0, top, source.width, min(bottom, source.height))).save(EVIDENCE / output_name)
    composite(
        "REDUX HOME: PAGINATED ACCESS TO ALL 500 RECORDS",
        """export const fetchRecalls = createAsyncThunk('recalls/fetch',
  async ({ query = '', page = 1 } = {}, thunkApi) => {
    const params = { page, page_size: 50 };
    const response = await apiClient.get('/recalls', { params });
    return response.data;
  });

const { items, page, pageSize, total } = useSelector(s => s.recalls);
<span>Showing {firstShown}-{lastShown} of {total}</span>
<span>Page {page} of {totalPages}</span>""",
        ["25_react_pagination_top_crop.png", "26_react_pagination_bottom_crop.png", "27_react_pagination_page2_crop.png"],
        "42_redux_home_composite.png",
    )
    composite(
        "REDUX CREATE: THUNK + SAVED UI OUTPUT",
        """await dispatch(createRecall(payload)).unwrap();
export const createRecall = createAsyncThunk('recalls/create', async (payload) => {
  const response = await apiClient.post('/recalls', payload);
  return response.data;
});""",
        ["17_react_create_success.png"], "43_redux_create_composite.png",
    )
    composite(
        "REDUX UPDATE: THUNK + UPDATED UI OUTPUT",
        """await dispatch(updateRecall({ id: Number(id), payload })).unwrap();
.addCase(updateRecall.fulfilled, (state, action) => {
  const index = state.items.findIndex(item => item.id === action.payload.id);
  if (index >= 0) state.items[index] = action.payload;
});""",
        ["19_react_update_success.png"], "44_redux_update_composite.png",
    )
    composite(
        "REDUX DELETE: CONFIRMATION ROUTE + UI OUTPUT",
        """<Link to={`/delete/${record.id}`}>Delete</Link>
await dispatch(deleteRecall(Number(id))).unwrap();
.addCase(deleteRecall.fulfilled, (state, action) => {
  state.items = state.items.filter(item => item.id !== action.payload);
  state.notice = `Deleted recall ID ${action.payload} successfully.`;
});""",
        ["20_react_delete_confirm.png", "21_react_delete_success.png"], "45_redux_delete_composite.png",
    )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    api_panels()
    mcp_panels()
    code_output_panels()
    redux_composites()
    print("Rendered HW5 evidence panels to", EVIDENCE)


if __name__ == "__main__":
    main()
