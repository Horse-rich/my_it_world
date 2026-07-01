"""假数据天气工具（仅用于测试 Agent 是否触发工具调用）。"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.agent.tools.base import BaseTool

# 固定假数据，便于在回答里辨认「工具已被调用」
_MOCK_WEATHER: Dict[str, dict] = {
    "青岛": {
        "city": "青岛",
        "condition": "晴",
        "temperature": 22,
        "humidity": 58,
        "wind": "东南风 3 级",
        "tip": "适合出行，注意防晒。",
    },
    "北京": {
        "city": "北京",
        "condition": "多云",
        "temperature": 18,
        "humidity": 42,
        "wind": "北风 2 级",
        "tip": "早晚温差较大。",
    },
    "上海": {
        "city": "上海",
        "condition": "小雨",
        "temperature": 16,
        "humidity": 78,
        "wind": "东风 2 级",
        "tip": "出门请带伞。",
    },
    "深圳": {
        "city": "深圳",
        "condition": "阴",
        "temperature": 26,
        "humidity": 72,
        "wind": "南风 2 级",
        "tip": "体感偏闷热。",
    },
}


def _normalize_city(city: str) -> str:
    return city.strip().replace("市", "").replace(" ", "")


def _lookup_city(city: str) -> dict | None:
    key = _normalize_city(city)
    if key in _MOCK_WEATHER:
        return _MOCK_WEATHER[key]
    for name, data in _MOCK_WEATHER.items():
        if name in key or key in name:
            return data
    return None


class WeatherTool(BaseTool):
    name = "get_weather"
    description = (
        "查询指定城市的天气情况（温度、湿度、风力等）。"
        "当用户询问某地今天/明天天气、气温、是否下雨等问题时必须使用此工具。"
    )
    parameters: Dict[str, Any] = {
        "city": {
            "type": "string",
            "description": "城市名称，例如：青岛、北京、上海",
            "required": True,
        },
    }

    def execute(self, city: str) -> str:
        data = _lookup_city(city)
        if data is None:
            return json.dumps(
                {
                    "source": "mock_weather_tool",
                    "found": False,
                    "city": city,
                    "message": f"假数据工具中暂无「{city}」的天气，可尝试：青岛、北京、上海、深圳",
                },
                ensure_ascii=False,
            )

        payload = {
            "source": "mock_weather_tool",
            "found": True,
            "mock": True,
            **data,
            "summary": (
                f"{data['city']}今天{data['condition']}，"
                f"气温 {data['temperature']}°C，"
                f"湿度 {data['humidity']}%，"
                f"{data['wind']}。"
                f"{data['tip']}"
            ),
        }
        return json.dumps(payload, ensure_ascii=False)
