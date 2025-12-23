"""chat endpoint for pharmacy ai agent"""
import logging
import traceback
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from backend.config import settings
from backend.services.openai_service import OpenAIAgentService
from backend.services.safety_guards import SafetyGuard
from backend.models.user import UserDatabase
from backend.middleware.security import pii_masker, audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
user_db = UserDatabase()


class Message(BaseModel):
    """chat message model"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """chat completion request model"""
    messages: List[Message]
    language: Optional[str] = "en"
    conversation_id: Optional[str] = None


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
        client_ip = request.client.host if request and request.client else "unknown"

        audit_logger.log_data_access(
            user_id=x_user_id or "anonymous",
            resource_type="chat",
            resource_id="completion",
            action="create",
            ip_address=client_ip
        )

        logger.info(f"chat completion request from user: {x_user_id}, language: {chat_request.language}, messages: {len(chat_request.messages)}")

        conversation_id = chat_request.conversation_id
        if x_user_id and not conversation_id:
            conversation_id = user_db.create_conversation(x_user_id, chat_request.language)
            logger.info(f"created new conversation: {conversation_id} for user: {x_user_id}")

        service = OpenAIAgentService()
        system_prompt = service.build_system_prompt(language=chat_request.language)

        masked_messages = []
        for msg in chat_request.messages:
            masked_content, detections = pii_masker.mask_text(msg.content)
            if detections:
                audit_logger.log_pii_access(
                    user_id=x_user_id or "anonymous",
                    pii_type=",".join([d["type"] for d in detections]),
                    action="mask_outbound",
                    ip_address=client_ip
                )
                logger.warning(f"pii detected and masked in user message: {[d['type'] for d in detections]}")
            masked_messages.append({"role": msg.role, "content": masked_content})

        messages = [
            {"role": "system", "content": system_prompt}
        ] + masked_messages

        if x_user_id and conversation_id and chat_request.messages:
            last_msg = chat_request.messages[-1]
            if last_msg.role == "user":
                masked_storage, _ = pii_masker.mask_text(last_msg.content)
                user_db.add_message(conversation_id, "user", masked_storage)
                logger.debug(f"saved user message to conversation: {conversation_id}")

        safety_guard = SafetyGuard()

        response = await service.client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=service.tools,
            tool_choice="auto",
            stream=True,
            temperature=settings.openai_temperature
        )

        async def generate():
            """generate streaming response chunks with tracking"""
            assistant_content = ""
            tool_calls_made = []
            total_tokens = 0

            try:
                async for chunk in response:
                    chunk_dict = chunk.model_dump()

                    delta = chunk_dict.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        assistant_content += delta["content"]
                        violation_reason = safety_guard.check_text(assistant_content)
                        if violation_reason:
                            assistant_content = safety_guard.refusal_message(violation_reason)
                            safety_chunk = {
                                "choices": [
                                    {
                                        "delta": {"content": assistant_content}
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(safety_chunk)}\n\n"

                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            if tc.get("function", {}).get("name"):
                                tool_name = tc["function"]["name"]
                                if tool_name not in tool_calls_made:
                                    tool_calls_made.append(tool_name)
                                    if x_user_id:
                                        user_db.track_tool_call(x_user_id, tool_name)

                    if chunk_dict.get("usage"):
                        total_tokens = chunk_dict["usage"].get("total_tokens", 0)

                    yield f"data: {json.dumps(chunk_dict)}\n\n"

                if x_user_id and conversation_id and assistant_content:
                    user_db.add_message(
                        conversation_id,
                        "assistant",
                        assistant_content,
                        json.dumps(tool_calls_made) if tool_calls_made else None,
                        total_tokens
                    )

                logger.info(f"streaming complete for conversation: {conversation_id}, tokens: {total_tokens}, tools used: {tool_calls_made}")
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

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Conversation-Id": conversation_id or ""
            }
        )

    except Exception as e:
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
        service = OpenAIAgentService()
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
        service = OpenAIAgentService()
        return {
            "tools": service.tools,
            "count": len(service.tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
