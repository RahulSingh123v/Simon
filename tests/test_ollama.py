import httpx 

BASE_URL = "http://127.0.0.1:11434"

def main() -> None:

    with httpx.Client(timeout=.0) as client:
        response = client.post(
            f"{BASE_URL}/api/chat",
            json={
                "model" : "qwen3:4b",
                "messages":[
                    {
                        "role":"user",
                        "content": (
                            "Give three step plan for summarizing"
                            "text files and saving a report"
                            "Do not execute anything."
                        )
                    }
                ],
                "stream":False,
                "think":False
            }
        )

        response.raise_for_status()
        result = response.json()

    print("SIMON ollama connection successful")
    print("\nModel response:\n")
    print(result["message"]["content"])

    if "prompt_eval_count" in result:
        print("\nprompt tokens:", result["prompt_eval_count"])
    
    if "eval_count" in result:
        print("\nThe generated token: ", result["eval_count"])
    
    if "eval_duration" in result:
        print("\nThe token per second: ", (result["eval_count"]/result["eval_duration"])*1e9)

    
if __name__ == "__main__":
    main()

    


