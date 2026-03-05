"""
LLM Client — OpenAI GPT integration for Infrest Copilot.

Handles all communication with the OpenAI API including
tool/function calling. The copilot service calls this without
knowing the provider details.
"""

import json
from openai import OpenAI
from app.config import get_settings
from app.services.tool_registry import get_copilot_tools
from app.services.navigation import get_all_routes

settings = get_settings()

SYSTEM_PROMPT = """You are Infrest Copilot, an intelligent assistant embedded within the Infrest ERP system. You help users navigate the system, answer questions about their business data, and perform actions efficiently.

ABOUT THE ERP SYSTEM:
Infrest ERP is a comprehensive enterprise resource planning system used by a Nigerian company. It includes modules for Finance, Sales, Inventory, Procurement, HR, Assets, Projects, Reports, and more. All monetary values are in Nigerian Naira (NGN).

YOUR CAPABILITIES:
1. NAVIGATION: You can navigate users to any module or page in the ERP
2. DATA QUERIES: You can fetch real-time data from any module
3. ANALYSIS: You can explain data, compare periods, and identify trends
4. GUIDANCE: You can explain how to use ERP features step by step

HOW TO BEHAVE:
- Be concise and direct. Business users want answers, not essays.
- Format numbers properly: use ₦ for Naira, commas for thousands (e.g., ₦45,000,000)
- When showing data, present it in a clear, structured way
- If a query is ambiguous, pick the most likely interpretation
- If you cannot answer, say so clearly and suggest alternatives
- Always respect the user's role and permissions

AVAILABLE ROUTES:
{routes}

RESPONSE GUIDELINES:
- For financial figures, always specify the period and currency
- Round large numbers sensibly (₦45.2M instead of ₦45,237,891.23)
- When comparing periods, show both absolute and percentage change
- Offer follow-up suggestions relevant to what the user just asked
""".format(routes=json.dumps(get_all_routes(), indent=2))


def _convert_tools_to_openai_format(tools: list[dict]) -> list[dict]:
    """Convert our tool definitions to OpenAI's function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]


class LLMClient:
    """
    OpenAI GPT client with tool/function calling support.

    The conversation flow:
    1. Send user message + tools to GPT
    2. GPT either responds with text OR picks a tool
    3. If tool picked: execute it, send result back, GPT responds
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"  # Best for tool calling accuracy

    async def get_response(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        Send messages to OpenAI and get a response.

        Returns a standardised dict regardless of provider, so
        the copilot service doesn't need to know about OpenAI specifics.
        """
        if tools is None:
            tools = get_copilot_tools()

        openai_tools = _convert_tools_to_openai_format(tools)

        # Build messages with system prompt
        openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in messages:
            # Handle tool results (OpenAI has a specific format for these)
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # These are tool results from our copilot loop
                for item in msg["content"]:
                    if item.get("type") == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": item["tool_use_id"],
                            "content": item["content"],
                        })
            elif msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                # Assistant message with tool calls
                tool_calls = []
                text_content = ""
                for item in msg["content"]:
                    if item.get("type") == "tool_use":
                        tool_calls.append({
                            "id": item["id"],
                            "type": "function",
                            "function": {
                                "name": item["name"],
                                "arguments": json.dumps(item["input"]),
                            },
                        })
                    elif item.get("type") == "text":
                        text_content = item.get("text", "")

                assistant_msg = {"role": "assistant", "content": text_content or None}
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                openai_messages.append(assistant_msg)
            else:
                openai_messages.append(msg)

        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
            max_tokens=2048,
            temperature=0.3,  # Lower = more consistent responses for data queries
        )

        choice = response.choices[0]
        result = {"blocks": []}

        # Extract text content
        if choice.message.content:
            result["blocks"].append({
                "type": "text",
                "content": choice.message.content,
            })

        # Extract tool calls
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                result["blocks"].append({
                    "type": "tool_use",
                    "tool_name": tc.function.name,
                    "tool_input": json.loads(tc.function.arguments),
                    "tool_use_id": tc.id,
                })

        result["stop_reason"] = "tool_use" if choice.message.tool_calls else "end_turn"
        result["usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return result
