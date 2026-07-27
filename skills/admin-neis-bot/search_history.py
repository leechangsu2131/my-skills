import json
from pathlib import Path

def main():
    log_path = Path(r"C:\Users\lee21\.gemini\antigravity\brain\d8a868cf-ab02-44e0-92b1-68bd3ae1045a\.system_generated\logs\transcript.jsonl")
    if not log_path.exists():
        print("Transcript log not found.")
        return
        
    print("Searching transcript...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = data.get("content", "")
                if "launch_chrome" in content or "chrome.exe" in content or "CommandLine" in str(data):
                    # Print relevant step info
                    step_idx = data.get("step_index", "?")
                    print(f"\n--- Step {step_idx} ({data.get('type')}) ---")
                    # If it has tool calls, print them
                    if "tool_calls" in data:
                        for tc in data["tool_calls"]:
                            if "CommandLine" in str(tc):
                                print(f"Tool Call: {tc['name']} -> {tc.get('arguments')}")
                    else:
                        print(content[:300])
            except Exception as e:
                pass

if __name__ == "__main__":
    main()
