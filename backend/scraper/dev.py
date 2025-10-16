import os
import sys
import subprocess

def main():
    print("🚀 Starting scraper backend (dev mode)...")
    cmd = ["uvicorn", "app.main:app", "--reload", "--port", "4001"]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped manually.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
