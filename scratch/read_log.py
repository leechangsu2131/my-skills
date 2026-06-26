import os

def main():
    log_path = r"C:\Users\user\.gemini\antigravity\brain\e3bf87fd-79df-40e6-88aa-f1dff496159a\.system_generated\tasks\task-347.log"
    if not os.path.exists(log_path):
        print(f"Log file not found at: {log_path}")
        return
        
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"Last 50 lines of log (Total lines: {len(lines)}):")
        for line in lines[-50:]:
            print(line, end="")
    except Exception as e:
        print(f"Failed to read log: {e}")

if __name__ == "__main__":
    main()
