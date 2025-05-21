import os
import sys
import subprocess
import webbrowser
import time
from dotenv import load_dotenv

def main():
    print("Starting PDF Processing API...")
    
    # Check if virtual environment exists
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
        python_cmd = "venv\\Scripts\\python"
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/Mac
        activate_cmd = "source venv/bin/activate"
        python_cmd = "venv/bin/python"
        pip_cmd = "venv/bin/pip"
    
    # Install dependencies
    print("Installing dependencies...")
    if os.name == 'nt':  # Windows
        subprocess.run(f"{pip_cmd} install -r requirements.txt", shell=True, check=True)
    else:
        subprocess.run(f"{activate_cmd} && {pip_cmd} install -r requirements.txt", shell=True, check=True)
    
    # Check if .env file exists, if not run setup
    if not os.path.exists(".env"):
        print("No .env file found. Running setup...")
        if os.name == 'nt':  # Windows
            subprocess.run(f"{python_cmd} setup.py", shell=True, check=True)
        else:
            subprocess.run(f"{activate_cmd} && {python_cmd} setup.py", shell=True, check=True)
    
    # Load environment variables
    load_dotenv()
    
    # Get host and port from environment variables or use defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    # Start the application in a new process
    print(f"Starting server at http://{host}:{port}")
    if host == "0.0.0.0":
        url = f"http://localhost:{port}"
    else:
        url = f"http://{host}:{port}"
    
    if os.name == 'nt':  # Windows
        process = subprocess.Popen(f"{python_cmd} -m uvicorn app.main:app --host {host} --port {port} --reload", shell=True)
    else:
        process = subprocess.Popen(f"{activate_cmd} && {python_cmd} -m uvicorn app.main:app --host {host} --port {port} --reload", shell=True)
    
    # Wait a bit for the server to start
    print("Waiting for server to start...")
    time.sleep(2)
    
    # Open browser
    print(f"Opening {url} in browser...")
    webbrowser.open(url)
    
    print("\nPress Ctrl+C to stop the server")
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        print("\nServer stopped")

if __name__ == "__main__":
    main()
