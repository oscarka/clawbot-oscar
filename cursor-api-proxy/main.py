"""
Cursor API Proxy - 将 Cursor 的能力封装为 OpenAI 兼容的 API
"""
import os
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic
import asyncio

# 加载环境变量
load_dotenv()

app = FastAPI(title="Cursor API Proxy", version="1.0.0")

# 初始化 Anthropic 客户端
anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# OpenAI 兼容的请求模型
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False

def convert_openai_to_anthropic(messages: List[Message]) -> str:
    """将 OpenAI 格式的消息转换为 Anthropic 格式的 prompt"""
    system_prompt = ""
    user_messages = []
    
    for msg in messages:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            user_messages.append(msg.content)
        elif msg.role == "assistant":
            # Anthropic 格式中，assistant 消息需要特殊处理
            user_messages.append(f"Assistant: {msg.content}")
    
    # 组合成 Anthropic 格式
    prompt = "\n\n".join(user_messages)
    return prompt, system_prompt

def convert_anthropic_to_openai(response: str, model: str) -> Dict[str, Any]:
    """将 Anthropic 响应转换为 OpenAI 格式"""
    return {
        "id": f"chatcmpl-{hash(response) % 1000000000}",
        "object": "chat.completion",
        "created": int(asyncio.get_event_loop().time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(response.split()) * 2,  # 粗略估算
            "completion_tokens": len(response.split()),
            "total_tokens": len(response.split()) * 3
        }
    }

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "service": "Cursor API Proxy",
        "version": "1.0.0"
    }

@app.get("/v1/models")
async def list_models():
    """列出可用的模型"""
    return {
        "object": "list",
        "data": [
            {
                "id": "claude-opus-4-5",
                "object": "model",
                "created": 1234567890,
                "owned_by": "cursor-proxy"
            },
            {
                "id": "claude-sonnet-4-5",
                "object": "model",
                "created": 1234567890,
                "owned_by": "cursor-proxy"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None)
):
    """处理聊天完成请求"""
    try:
        # 验证 API Key（如果设置了）
        proxy_api_key = os.getenv("PROXY_API_KEY")
        if proxy_api_key and authorization:
            expected_auth = f"Bearer {proxy_api_key}"
            if authorization != expected_auth:
                raise HTTPException(status_code=401, detail="Invalid API key")
        
        # 转换消息格式
        prompt, system_prompt = convert_openai_to_anthropic(request.messages)
        
        # 确定使用的模型
        model_mapping = {
            "claude-opus-4-5": "claude-3-opus-20240229",
            "claude-sonnet-4-5": "claude-3-sonnet-20240229",
            "claude-haiku-3-5": "claude-3-haiku-20240307"
        }
        anthropic_model = model_mapping.get(request.model, "claude-3-sonnet-20240229")
        
        # 调用 Anthropic API
        if request.stream:
            # 流式响应
            async def generate_stream():
                try:
                    with anthropic_client.messages.stream(
                        model=anthropic_model,
                        max_tokens=request.max_tokens or 4096,
                        temperature=request.temperature or 0.7,
                        system=system_prompt if system_prompt else None,
                        messages=[{"role": "user", "content": prompt}]
                    ) as stream:
                        for text in stream.text_stream:
                            chunk = {
                                "id": f"chatcmpl-{hash(prompt) % 1000000000}",
                                "object": "chat.completion.chunk",
                                "created": int(asyncio.get_event_loop().time()),
                                "model": request.model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": text},
                                        "finish_reason": None
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                        
                        # 发送结束标记
                        final_chunk = {
                            "id": f"chatcmpl-{hash(prompt) % 1000000000}",
                            "object": "chat.completion.chunk",
                            "created": int(asyncio.get_event_loop().time()),
                            "model": request.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop"
                                }
                            ]
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                except Exception as e:
                    error_chunk = {
                        "error": {
                            "message": str(e),
                            "type": "api_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            response = anthropic_client.messages.create(
                model=anthropic_model,
                max_tokens=request.max_tokens or 4096,
                temperature=request.temperature or 0.7,
                system=system_prompt if system_prompt else None,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 转换响应格式
            openai_response = convert_anthropic_to_openai(
                response.content[0].text,
                request.model
            )
            
            return openai_response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PROXY_PORT", 8000))
    host = os.getenv("PROXY_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
