import os
import httpx
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient

class UserMessage:
    def __init__(self, text: str):
        self.text = text


class LlmChat:
    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = "anthropic"
        self.model_name = "claude-sonnet-4-6"

    def with_model(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name
        return self

    async def send_message(self, message: UserMessage):
        # 1. Fetch chat history from DB
        history = []
        try:
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "test_database")
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            if self.session_id and self.session_id.startswith("recovery-"):
                # Format is: recovery-{case_id}-{user_id}
                parts = self.session_id.split("-")
                if len(parts) >= 2:
                    case_id = parts[1]
                    msgs = await db.recovery_chat.find({"case_id": case_id}).sort("created_at", 1).to_list(100)
                    for m in msgs:
                        history.append({"role": m["role"], "content": m["content"]})
            elif self.session_id:
                msgs = await db.chat_messages.find({"session_id": self.session_id}).sort("created_at", 1).to_list(100)
                for m in msgs:
                    history.append({"role": m["role"], "content": m["content"]})
        except Exception as e:
            print(f"Error fetching chat history from MongoDB: {e}")

        # Ensure the current message is included in history
        current_msg = message.text
        if not history or history[-1]["content"] != current_msg:
            history.append({"role": "user", "content": current_msg})

        # 2. Try Cloud LLM providers via LiteLLM if keys are available
        openai_key = os.environ.get("OPENAI_API_KEY")
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if gemini_key or openai_key or anthropic_key:
            try:
                import litellm
                messages = [{"role": "system", "content": self.system_message}] + history
                
                if gemini_key:
                    resp = await litellm.acompletion(
                        model="gemini/gemini-1.5-flash",
                        messages=messages,
                        api_key=gemini_key
                    )
                    return resp.choices[0].message.content
                elif openai_key:
                    resp = await litellm.acompletion(
                        model="gpt-4o-mini",
                        messages=messages,
                        api_key=openai_key
                    )
                    return resp.choices[0].message.content
                elif anthropic_key:
                    resp = await litellm.acompletion(
                        model="claude-3-5-sonnet-20241022",
                        messages=messages,
                        api_key=anthropic_key
                    )
                    return resp.choices[0].message.content
            except Exception as e:
                print(f"Cloud LLM call failed, trying local Ollama: {e}")

        # 3. Try Local Ollama (running llama3.1:8b)
        try:
            ollama_payload = {
                "model": "llama3.1:8b",
                "messages": [{"role": "system", "content": self.system_message}] + history,
                "stream": False
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post("http://127.0.0.1:11434/api/chat", json=ollama_payload, timeout=60)
                if resp.status_code == 200:
                    return resp.json()["message"]["content"]
                else:
                    raise Exception(f"Ollama returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Ollama call failed: {e}")
            # Raise exception so the caller falls back to rule-based response
            raise e
