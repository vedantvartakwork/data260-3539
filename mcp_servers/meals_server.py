"""TheMealDB tutorial MCP server with four schema-stable tools."""

from __future__ import annotations

import logging
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.themealdb.com/api/json/v1/1"
TIMEOUT_SECONDS = 10.0
mcp = FastMCP("meals")


class SearchLimit(BaseModel):
    limit: int = Field(default=5, ge=1, le=25)


def _get(endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        response = httpx.get(
            f"{BASE_URL}/{endpoint}", params=params, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        LOGGER.error("TheMealDB request failed: %s", exc)
        raise RuntimeError(f"TheMealDB request failed: {exc}") from exc
    meals = payload.get("meals")
    return meals if isinstance(meals, list) else []


def _meal_details(meal: dict[str, Any]) -> dict[str, Any]:
    ingredients = []
    for index in range(1, 21):
        name = (meal.get(f"strIngredient{index}") or "").strip()
        measure = (meal.get(f"strMeasure{index}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure})
    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "category": meal.get("strCategory"),
        "area": meal.get("strArea"),
        "instructions": meal.get("strInstructions"),
        "image": meal.get("strMealThumb"),
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients,
    }


@mcp.tool()
def search_meals_by_name(query: str, limit: int = 5) -> dict[str, Any]:
    """Search meals by name and return compact result cards."""
    parsed = SearchLimit(limit=limit)
    meals = _get("search.php", {"s": query})[: parsed.limit]
    return {
        "meals": [
            {
                "id": meal.get("idMeal"),
                "name": meal.get("strMeal"),
                "area": meal.get("strArea"),
                "category": meal.get("strCategory"),
                "thumb": meal.get("strMealThumb"),
            }
            for meal in meals
        ],
        "message": None if meals else "no matches",
    }


@mcp.tool()
def meals_by_ingredient(ingredient: str, limit: int = 12) -> dict[str, Any]:
    """Filter meals by their main ingredient."""
    parsed = SearchLimit(limit=limit)
    meals = _get("filter.php", {"i": ingredient})[: parsed.limit]
    return {
        "meals": [
            {
                "id": meal.get("idMeal"),
                "name": meal.get("strMeal"),
                "thumb": meal.get("strMealThumb"),
            }
            for meal in meals
        ],
        "message": None if meals else "no matches",
    }


@mcp.tool()
def meal_details(id: str | int) -> dict[str, Any]:
    """Look up a meal by id and return its complete recipe shape."""
    meals = _get("lookup.php", {"i": str(id)})
    return _meal_details(meals[0]) if meals else {"meal": None, "message": "no matches"}


@mcp.tool()
def random_meal() -> dict[str, Any]:
    """Return one random meal in the same shape as meal_details."""
    meals = _get("random.php")
    return _meal_details(meals[0]) if meals else {"meal": None, "message": "no matches"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
