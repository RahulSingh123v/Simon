import httpx
from typing import Any

from simon.core.config import load_settings,SimonSettings

class ModelGateway:

    #  THIS MODULES HANDLES THE COMMUCNIATION WITH SIMON'S LLM MODEL

    def __init__(self,settings: SimonSettings) -> None:

        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.model_base_url,
            timeout=httpx.Timeout(180.0)
        )

    async def generate(
        self, messages:list[dict[str,str]], 
        response_schema: dict[str,Any] | None = None) -> dict[str,Any]:

        payload: dict[str,Any] = {
            "model": self.settings.model_name,
            "messages": messages,
            "think": False,
            "stream": False
        }

        if response_schema is not None:
            payload["format"] = response_schema

        response = await self.client.post(
            "/api/chat",
            json=payload
        )

        response.raise_for_status()

        return response.json()
        

    async def close(self) -> None:

        await self.client.aclose()



    



