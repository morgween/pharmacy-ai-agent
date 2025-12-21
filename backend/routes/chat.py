"""chat endpoint for pharmacy ai agent"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from backend.config import settings
from backend.services.openai_service import OpenAIAgentService
from backend.models.user import UserDatabase

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
    request: ChatRequest,
    x_user_id: Optional[str] = Header(None)
):
    """
    handle chat completion with streaming, function calling, and user tracking

    args:
        request: chat request with messages and language
        x_user_id: user identifier from header

    returns:
        streaming response with chat completions
    """
    try:
        # create or get conversation
        conversation_id = request.conversation_id
        if x_user_id and not conversation_id:
            conversation_id = user_db.create_conversation(x_user_id, request.language)

        service = OpenAIAgentService()
        system_prompt = service.build_system_prompt(language=request.language)

        messages = [
            {"role": "system", "content": system_prompt}
        ] + [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # save user message if tracking
        if x_user_id and conversation_id and request.messages:
            last_msg = request.messages[-1]
            if last_msg.role == "user":
                user_db.add_message(conversation_id, "user", last_msg.content)

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

                    # track content and tool calls
                    delta = chunk_dict.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        assistant_content += delta["content"]
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            if tc.get("function", {}).get("name"):
                                tool_name = tc["function"]["name"]
                                if tool_name not in tool_calls_made:
                                    tool_calls_made.append(tool_name)
                                    # track tool usage
                                    if x_user_id:
                                        user_db.track_tool_call(x_user_id, tool_name)

                    # estimate tokens (rough)
                    if chunk_dict.get("usage"):
                        total_tokens = chunk_dict["usage"].get("total_tokens", 0)

                    yield f"data: {json.dumps(chunk_dict)}\n\n"

                # save assistant message if tracking
                if x_user_id and conversation_id and assistant_content:
                    user_db.add_message(
                        conversation_id,
                        "assistant",
                        assistant_content,
                        json.dumps(tool_calls_made) if tool_calls_made else None,
                        total_tokens
                    )

                yield "data: [DONE]\n\n"
            except Exception as e:
                error_data = {"error": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"

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
