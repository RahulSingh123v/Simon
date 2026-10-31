import asyncio

from simon.core.config import load_settings
from simon.core.model_gateway import ModelGateway

async def main() -> None:

    settings = load_settings()
    gateway = ModelGateway(settings)

    try:
        result = await gateway.generate(
            messages=[
                {
                    "role":"system",
                    "content":"You are SIMON's local AI engine. "
                    "Answer clearly and concisely."
                },
                {
                    "role":"user",
                    "content":"Explain the difference between "
                    "planning and executing a task."
                },
            ],
        )

        print("Gateway connection successful.")
        print("\nModel response:")
        print(result["message"]["content"])

    finally:
        await gateway.close()

if __name__ == "__main__":
    asyncio.run(main())