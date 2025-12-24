"""chat endpoint for pharmacy ai agent"""
import asyncio
import logging
import traceback
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Iterable, Tuple
import json
from backend.domain.config import settings
from backend.services.openai_service import get_openai_service, OpenAIAgentService
from backend.services.safety_guards import SafetyGuard
from backend.models.user import UserDatabase
from backend.utils.security import pii_masker, audit_logger
from backend.utils.language import detect_language
from backend.tool_framework.parser import ToolCallAccumulator
from backend.tool_framework.stream import StreamProcessor
from backend.tool_framework.runner import ToolRunner
from backend.tool_framework.inference import infer_tool_arguments

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
user_db = UserDatabase()


class Message(BaseModel):
    """chat message model"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """chat completion request model"""
    model_config = ConfigDict(populate_by_name=True)
    messages: List[Message]
    language: Optional[str] = "auto"
    conversation_id: Optional[str] = None
    user_id: Optional[str] = Field(default=None, alias="userId")


def _get_client_ip(request: Request) -> str:
    """return best-effort client ip for audit logging."""
    if request and request.client:
        return request.client.host
    return "unknown"


def _resolve_language(chat_request: ChatRequest) -> str:
    """resolve requested language, falling back to auto-detection."""
    requested_language = (chat_request.language or "auto").lower()
    if requested_language != "auto":
        return requested_language

    last_user_message = next(
        (msg.content for msg in reversed(chat_request.messages) if msg.role == "user"),
        ""
    )
    return detect_language(last_user_message)


def _mask_messages(
    messages: List[Message],
    effective_user_id: Optional[str],
    client_ip: str
) -> Tuple[List[Dict[str, str]], str]:
    """mask pii in messages and return masked list plus last user message."""
    masked_messages = []
    for msg in messages:
        masked_content, detections = pii_masker.mask_text(msg.content)
        if detections:
            audit_logger.log_pii_access(
                user_id=effective_user_id or "anonymous",
                pii_type=",".join([d["type"] for d in detections]),
                action="mask_outbound",
                ip_address=client_ip
            )
            logger.warning(f"pii detected and masked in user message: {[d['type'] for d in detections]}")
        masked_messages.append({"role": msg.role, "content": masked_content})

    last_user_message = next(
        (msg["content"] for msg in reversed(masked_messages) if msg["role"] == "user"),
        ""
    )
    return masked_messages, last_user_message


def _summarize_tool_calls(tool_calls: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    """build minimal tool call summaries for logging."""
    summaries = []
    for tool_call in tool_calls:
        function = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
        summaries.append(
            {
                "id": tool_call.get("id") if isinstance(tool_call, dict) else None,
                "name": function.get("name"),
                "args_len": len(function.get("arguments", "")),
            }
        )
    return summaries


def _build_buffered_chunk(buffered_text: str) -> str:
    """wrap buffered text into an sse chunk for the client."""
    buffered_chunk = {
        "choices": [
            {
                "delta": {"content": buffered_text}
            }
        ]
    }
    return f"data: {json.dumps(buffered_chunk)}\n\n"


def _contains_any(text: str, keywords: List[str]) -> bool:
    """return true if any keyword is contained in text (casefolded)."""
    text_fold = text.casefold()
    return any(keyword in text_fold for keyword in keywords)


def _determine_tool_choice(
    *,
    service: OpenAIAgentService,
    last_user_message: str,
    detected_language: str
) -> Optional[Dict[str, Dict[str, Dict[str, str]]]]:
    """select a forced tool when intent is clear to avoid non-tool answers."""
    if not last_user_message:
        return None

    ingredient_terms = [
        "ingredient", "active ingredient", "contains", "contain", "содерж", "ингредиент", "состав",
        "מרכיב", "מכיל", "يحتوي", "مكون", "المادة الفعالة"
    ]
    stock_terms = [
        "in stock", "stock", "available", "availability", "в наличии", "налич", "есть ли",
        "доступн", "מלאי", "במלאי", "זמין", "متوفر", "المخزون"
    ]
    pharmacy_terms = [
        "nearest pharmacy", "pharmacy near", "nearby pharmacy", "find pharmacy",
        "аптека", "аптек", "ближайш", "בית מרקחת", "קרובה", "صيدلية", "قريبة"
    ]

    if _contains_any(last_user_message, ingredient_terms):
        args = infer_tool_arguments(
            "search_by_ingredient",
            last_user_message,
            detected_language,
            service
        )
        if args:
            return {"type": "function", "function": {"name": "search_by_ingredient"}}

    if _contains_any(last_user_message, stock_terms):
        args = infer_tool_arguments(
            "check_stock",
            last_user_message,
            detected_language,
            service
        )
        if args:
            return {"type": "function", "function": {"name": "check_stock"}}

    if _contains_any(last_user_message, pharmacy_terms):
        args = infer_tool_arguments(
            "find_nearest_pharmacy",
            last_user_message,
            detected_language,
            service
        )
        if args:
            return {"type": "function", "function": {"name": "find_nearest_pharmacy"}}

    args = infer_tool_arguments(
        "get_medication_info",
        last_user_message,
        detected_language,
        service
    )
    if args:
        return {"type": "function", "function": {"name": "get_medication_info"}}

    return None


async def _persist_user_message(
    chat_request: ChatRequest,
    effective_user_id: Optional[str],
    conversation_id: Optional[str]
) -> None:
    """persist the latest user message for conversation history."""
    if not (effective_user_id and conversation_id and chat_request.messages):
        return

    last_msg = chat_request.messages[-1]
    if last_msg.role != "user":
        return

    masked_storage, _ = pii_masker.mask_text(last_msg.content)
    await asyncio.to_thread(
        user_db.add_message,
        conversation_id,
        "user",
        masked_storage
    )
    logger.debug(f"saved user message to conversation: {conversation_id}")


async def _stream_chat(
    *,
    service: OpenAIAgentService,
    safety_guard: SafetyGuard,
    detected_language: str,
    messages: List[Dict[str, str]],
    last_user_message: str,
    effective_user_id: Optional[str],
    conversation_id: Optional[str]
):
    """stream model output and tool calls, persisting assistant messages."""
    assistant_content = ""
    tool_calls_made: List[str] = []
    total_tokens = 0
    max_steps = 10
    step = 0
    working_messages = list(messages)
    forced_tool_choice = _determine_tool_choice(
        service=service,
        last_user_message=last_user_message,
        detected_language=detected_language
    )

    try:
        while step < max_steps:
            tool_choice = forced_tool_choice if step == 0 and forced_tool_choice else "auto"
            response = await service.openai_client.client.chat.completions.create(
                model=settings.openai_model,
                messages=working_messages,
                tools=service.tools,
                tool_choice=tool_choice,
                stream=True,
                temperature=settings.openai_temperature
            )

            tool_call_accumulator = ToolCallAccumulator()
            processor = StreamProcessor(
                safety_guard=safety_guard,
                detected_language=detected_language,
                tool_call_accumulator=tool_call_accumulator,
                tool_calls_made=tool_calls_made,
                effective_user_id=effective_user_id,
                user_db=user_db,
                assistant_content=assistant_content,
                total_tokens=total_tokens
            )

            async for payload in processor.iter_chunks(response):
                yield payload

            assistant_content = processor.assistant_content
            step_assistant_content = processor.step_assistant_content
            buffered_text = processor.buffered_text
            tool_calls_detected = processor.tool_calls_detected
            safety_blocked = processor.safety_blocked
            total_tokens = processor.total_tokens

            if safety_blocked:
                break

            tool_calls = tool_call_accumulator.build()
            if not tool_calls:
                if buffered_text:
                    yield _build_buffered_chunk(buffered_text)
                break

            logger.info(
                f"step {step} tool calls summary: {_summarize_tool_calls(tool_calls)}"
            )

            assistant_tool_message = {
                "role": "assistant",
                "content": "" if tool_calls_detected else step_assistant_content,
                "tool_calls": tool_calls
            }
            tool_runner = ToolRunner(
                service=service,
                last_user_message=last_user_message,
                detected_language=detected_language,
                effective_user_id=effective_user_id
            )
            async for payload in tool_runner.run(tool_calls):
                yield payload
            tool_messages = tool_runner.tool_messages

            if not tool_messages:
                logger.error("tool calls detected but no valid tool messages could be produced")
                break

            # always pass tool results back to the model - let the model formulate the response
            # don't short-circuit with fallback_message, as the model should handle errors gracefully
            working_messages = working_messages + [assistant_tool_message] + tool_messages
            step += 1

        if effective_user_id and conversation_id and assistant_content:
            await asyncio.to_thread(
                user_db.add_message,
                conversation_id,
                "assistant",
                assistant_content,
                json.dumps(tool_calls_made) if tool_calls_made else None,
                total_tokens
            )

        logger.info(
            f"streaming complete for conversation: {conversation_id}, "
            f"tokens: {total_tokens}, tools used: {tool_calls_made}"
        )
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"streaming error: {str(e)}", exc_info=True)
        logger.error(f"stack trace: {traceback.format_exc()}")
        error_data = {
            "error": "stream_error",
            "message": "An error occurred while processing your request. Please try again."
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/completions")
async def chat_completion(
    chat_request: ChatRequest,
    request: Request,
    x_user_id: Optional[str] = Header(None)
):
    """
    handle chat completion with streaming, function calling, user tracking, and pii protection

    args:
        chat_request: chat request with messages and language
        request: fastapi request for client info
        x_user_id: user identifier from header

    returns:
        streaming response with chat completions
    """
    try:
        client_ip = _get_client_ip(request)
        effective_user_id = x_user_id or chat_request.user_id

        audit_logger.log_data_access(
            user_id=effective_user_id or "anonymous",
            resource_type="chat",
            resource_id="completion",
            action="create",
            ip_address=client_ip
        )

        detected_language = _resolve_language(chat_request)
        logger.info(
            f"chat completion request from user: {effective_user_id}, "
            f"language: {detected_language}, messages: {len(chat_request.messages)}"
        )

        conversation_id = chat_request.conversation_id
        if effective_user_id and not conversation_id:
            conversation_id = await asyncio.to_thread(
                user_db.create_conversation,
                effective_user_id,
                detected_language
            )
            logger.info(f"created new conversation: {conversation_id} for user: {effective_user_id}")

        service = get_openai_service()
        system_prompt = service.build_system_prompt(language=detected_language)

        masked_messages, last_user_message = _mask_messages(
            chat_request.messages,
            effective_user_id,
            client_ip
        )

        if last_user_message:
            logger.info(
                f"last user message (masked, first 160 chars): {last_user_message[:160]}"
            )

        messages = [
            {"role": "system", "content": system_prompt}
        ] + masked_messages

        await _persist_user_message(chat_request, effective_user_id, conversation_id)

        safety_guard = SafetyGuard()

        return StreamingResponse(
            _stream_chat(
                service=service,
                safety_guard=safety_guard,
                detected_language=detected_language,
                messages=messages,
                last_user_message=last_user_message,
                effective_user_id=effective_user_id,
                conversation_id=conversation_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Conversation-Id": conversation_id or ""
            }
        )

    except Exception as e:
        logger.exception("chat completion failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/function-call")
async def execute_function(function_name: str, arguments: dict):
    """
    execute a function call manually for testing purposes

    args:
        function_name: name of the function to execute
        arguments: function arguments as json object

    returns:
        function execution result
    """
    try:
        service = get_openai_service()
        result = await service.execute_function_call(function_name, arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def get_available_tools():
    """
    get list of available tools and function schemas

    returns:
        list of tool schemas and count
    """
    try:
        service = get_openai_service()
        return {
            "tools": service.tools,
            "count": len(service.tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
