import httpx
import json

from simon.agent.contracts import TaskPlan

BASE_URL = "http://127.0.0.1:11434"

def main() -> None:

    schema = TaskPlan.model_json_schema()

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{BASE_URL}/api/chat",
            json={
                "model":"qwen3:4b",
                "messages": [
                    {
                        "role":"user",
                        "content":"Create three-step plan for finding"
                        "text files, summarizing them and "
                        "Do not execute anything"
                    }
                ],
                "format": schema,
                "stream":False,
                "think":False
            },
        )

        response.raise_for_status()
        result = response.json()

    raw_content = result["message"]["content"]

    parsed_json = json.loads(raw_content)
    plan = TaskPlan.model_validate(parsed_json)

    print("\nValidated task plan:")
    print(plan.model_dump_json(indent=2))
    
    print("\nValidation successful.")
    print("Number of steps:", len(plan.steps))


if __name__ == "__main__":
    main()





