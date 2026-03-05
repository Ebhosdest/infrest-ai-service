"""
Copilot Orchestration Service.

This is the central coordinator. When a user sends a message:
1. It formats the conversation for the LLM
2. Sends it to the LLM with available tools
3. If the LLM wants to use a tool, executes it
4. Sends the tool result back to the LLM
5. Returns the final response to the user

The tool-calling loop can run multiple times per turn
(e.g., if the LLM needs data from two different modules
to answer a complex question).
"""

import json
import time
import structlog
from app.services.llm_client import LLMClient
from app.services.erp_client import ERPClient
from app.services.navigation import find_route
from app.models.chat import (
    ChatRequest, ChatResponse, ChatMessage,
    ResponseType, NavigationAction, DataTableResponse,
)

logger = structlog.get_logger()


# Help content for common topics
HELP_TOPICS = {
    "purchase order": (
        "To create a Purchase Order:\n"
        "1. Go to Procurement → Purchase Orders\n"
        "2. Click 'New Purchase Order'\n"
        "3. Select the vendor from the dropdown\n"
        "4. Add line items with quantities and prices\n"
        "5. Submit for approval\n"
        "6. Once approved, the PO is sent to the vendor"
    ),
    "sales order": (
        "To create a Sales Order:\n"
        "1. Go to Sales → Sales Orders\n"
        "2. Click 'New Order'\n"
        "3. Select the customer\n"
        "4. Add products with quantities\n"
        "5. Review pricing and VAT\n"
        "6. Submit the order"
    ),
    "invoice": (
        "To create an Invoice:\n"
        "1. Go to Sales → Invoices\n"
        "2. Click 'New Invoice' or generate from a Sales Order\n"
        "3. Verify line items and amounts\n"
        "4. Set payment terms and due date\n"
        "5. Send to customer"
    ),
    "journal entry": (
        "To create a Journal Entry:\n"
        "1. Go to Finance → General Ledger\n"
        "2. Click 'New Journal Entry'\n"
        "3. Enter the date and description\n"
        "4. Add debit and credit lines (must balance)\n"
        "5. Post the entry"
    ),
    "leave request": (
        "To submit a Leave Request:\n"
        "1. Go to HR → Leave Management\n"
        "2. Click 'New Request'\n"
        "3. Select leave type\n"
        "4. Choose start and end dates\n"
        "5. Add a note if needed\n"
        "6. Submit for approval"
    ),
}


class CopilotService:
    """
    Main orchestrator for the Infrest Copilot.

    Manages the conversation flow between the user, the LLM,
    and the ERP data layer.
    """

    def __init__(self):
        self.llm = LLMClient()
        self.erp = ERPClient()

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a user message and return an AI response.

        This is the main entry point called by the API route.
        """
        start_time = time.time()

        try:
            # Build the conversation messages for the LLM
            messages = self._build_messages(request)

            # Send to LLM and handle the tool-calling loop
            response = await self._run_conversation(messages, request.current_module)

            processing_time = int((time.time() - start_time) * 1000)
            response.processing_time_ms = processing_time
            response.session_id = request.session_id

            logger.info(
                "copilot_response",
                session_id=request.session_id,
                processing_time_ms=processing_time,
                response_type=response.response_type,
            )

            return response

        except Exception as e:
            logger.error("copilot_error", error=str(e), session_id=request.session_id)
            return ChatResponse(
                message="I ran into an issue processing your request. Please try rephrasing your question, or contact support if the problem persists.",
                response_type=ResponseType.ERROR,
                session_id=request.session_id,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    def _build_messages(self, request: ChatRequest) -> list[dict]:
        """
        Convert the chat request into the message format
        expected by the LLM API.
        """
        messages = []

        # Add conversation history
        for msg in request.conversation_history[-10:]:  # Keep last 10 messages for context
            messages.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        # Add the current message with context
        user_content = request.message
        if request.current_module:
            user_content = f"[User is currently viewing: {request.current_module}]\n\n{request.message}"

        messages.append({
            "role": "user",
            "content": user_content,
        })

        return messages

    async def _run_conversation(self, messages: list[dict], current_module: str = None) -> ChatResponse:
        """
        Run the LLM conversation with tool-calling loop.

        The loop runs until the LLM returns a text response
        (stop_reason != 'tool_use') or we hit the maximum
        number of tool calls (safety limit).
        """
        max_tool_rounds = 5  # Safety limit
        round_count = 0

        while round_count < max_tool_rounds:
            round_count += 1

            # Call the LLM
            llm_response = await self.llm.get_response(messages)

            # Check if the LLM wants to use a tool
            tool_blocks = [b for b in llm_response["blocks"] if b["type"] == "tool_use"]
            text_blocks = [b for b in llm_response["blocks"] if b["type"] == "text"]

            if not tool_blocks:
                # No tools — LLM is done, return the text response
                text_content = " ".join(b["content"] for b in text_blocks)
                return ChatResponse(
                    message=text_content or "I'm not sure how to help with that. Could you rephrase your question?",
                    response_type=ResponseType.TEXT,
                    session_id="",
                )

            # Execute each tool and collect results
            # First, add the assistant's response to the conversation
            assistant_content = []
            for b in llm_response["blocks"]:
                if b["type"] == "text":
                    assistant_content.append({"type": "text", "text": b["content"]})
                elif b["type"] == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": b["tool_use_id"],
                        "name": b["tool_name"],
                        "input": b["tool_input"],
                    })

            messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and add results
            tool_results = []
            navigation_action = None
            data_table = None

            for tool_block in tool_blocks:
                tool_name = tool_block["tool_name"]
                tool_input = tool_block["tool_input"]
                tool_id = tool_block["tool_use_id"]

                logger.info("executing_tool", tool=tool_name, input=tool_input)

                # Execute the tool
                result, nav, table = await self._execute_tool(tool_name, tool_input)

                if nav:
                    navigation_action = nav
                if table:
                    data_table = table

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result, default=str),
                })

            messages.append({"role": "user", "content": tool_results})

            # If the LLM's stop reason was end_turn (it gave text + tool),
            # we still need to loop so it can process tool results.
            # But if it was only tools, the next iteration will get the final text.

        # If we hit the limit, return what we have
        return ChatResponse(
            message="I gathered some information but the query was quite complex. Could you try asking something more specific?",
            response_type=ResponseType.TEXT,
            session_id="",
        )

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> tuple[dict, NavigationAction | None, DataTableResponse | None]:
        """
        Execute a tool and return the result.

        Returns a tuple of (result_data, navigation_action, data_table).
        The navigation and data_table are optional — only set for
        specific tool types.
        """
        navigation = None
        data_table = None

        # Navigation
        if tool_name == "navigate_to_module":
            target = tool_input.get("target", "")
            route = find_route(target)
            if route:
                navigation = NavigationAction(path=route.path, label=route.label)
                result = {"success": True, "path": route.path, "label": route.label, "description": route.description}
            else:
                result = {"success": False, "message": f"Could not find a page matching '{target}'"}

        # Finance
        elif tool_name == "get_cash_balance":
            result = await self.erp.get_cash_balance(tool_input.get("as_of_date"))

        elif tool_name == "get_financial_summary":
            result = await self.erp.get_financial_summary(
                tool_input.get("start_date"),
                tool_input.get("end_date"),
                tool_input.get("period", "monthly"),
            )

        elif tool_name == "get_ar_aging":
            result = await self.erp.get_ar_aging(tool_input.get("customer_id"))

        elif tool_name == "get_ap_aging":
            result = await self.erp.get_ap_aging(tool_input.get("vendor_id"))

        # Sales
        elif tool_name == "get_sales_summary":
            result = await self.erp.get_sales_summary(
                tool_input.get("start_date"),
                tool_input.get("end_date"),
                tool_input.get("top_n", 10),
            )

        elif tool_name == "get_customer_details":
            result = await self.erp.get_customer_details(tool_input["search_term"])

        elif tool_name == "get_inactive_customers":
            result = await self.erp.get_inactive_customers(tool_input.get("days_inactive", 90))

        # Inventory
        elif tool_name == "get_stock_levels":
            result = await self.erp.get_stock_levels(
                tool_input.get("item_name"),
                tool_input.get("category"),
                tool_input.get("low_stock_only", False),
            )

        elif tool_name == "get_warehouse_summary":
            result = await self.erp.get_warehouse_summary()

        # Procurement
        elif tool_name == "get_vendor_performance":
            result = await self.erp.get_vendor_performance(
                tool_input.get("top_n", 10),
                tool_input.get("sort_by", "spend"),
            )

        elif tool_name == "get_purchase_order_status":
            result = await self.erp.get_purchase_order_status(
                tool_input.get("status"),
                tool_input.get("vendor_name"),
            )

        # HR
        elif tool_name == "get_employee_summary":
            result = await self.erp.get_employee_summary(tool_input.get("department"))

        elif tool_name == "get_payroll_summary":
            result = await self.erp.get_payroll_summary(
                tool_input.get("year"),
                tool_input.get("month"),
            )

        elif tool_name == "get_leave_summary":
            result = await self.erp.get_leave_summary(
                tool_input.get("status"),
                tool_input.get("department"),
            )

        # Assets
        elif tool_name == "get_asset_summary":
            result = await self.erp.get_asset_summary(tool_input.get("category"))

        # Projects
        elif tool_name == "get_project_summary":
            result = await self.erp.get_project_summary(
                tool_input.get("status"),
                tool_input.get("department"),
            )

        # Help
        elif tool_name == "get_help":
            topic = tool_input.get("topic", "").lower()
            help_text = None
            for key, text in HELP_TOPICS.items():
                if key in topic:
                    help_text = text
                    break
            if help_text:
                result = {"topic": topic, "guidance": help_text}
            else:
                result = {
                    "topic": topic,
                    "guidance": f"I can help with: {', '.join(HELP_TOPICS.keys())}. Ask me about any of these topics.",
                }

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return result, navigation, data_table
