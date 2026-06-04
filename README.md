# Hismith-AI-control
A Reinforcement Learning + LLM Pattern Generator
This project turns your Hismith sex machine into an adaptive, intelligent partner. Using Python, a webcam (optional), Buttplug.io, and a local AI (Ollama), the system learns your preferences in real time and generates new patterns when it gets bored.

How It Works
Q‑Learning Agent – an AI that learns which patterns you like (good 👍) or dislike (bad 👎) via keyboard presses.
Ollama LLM – a free, local AI that creates new patterns when the agent stagnates (no improvement for several cycles).
Smooth & Safe – a warm‑up period (2 minutes at the softest setting), gradual speed increases (capped at +15 base per cycle), and immediate stop on a “bad” press.
Real‑time Feedback – press g (good) or b (bad) at any moment. A b press instantly stops the current pattern and switches to the softest one.
Setup Guide
What You Need
Component	Requirement
Hismith machine	With a compatible controller (Bluetooth / USB / wired).
Computer	Windows (tested); Linux/Mac may need adjustments.
Buttplug.io	Download & install the Intiface Desktop (server) from intiface.com.
Python 3.9+	Install from python.org. Add to PATH.
Ollama	Free, open‑source LLM runner. Download from ollama.com.
Storage	A model like phi4 (2.5 GB) – you can store it on a different drive (see below).
1. Install Buttplug.io (Intiface)
Download & install Intiface Desktop.
Run it and start the server (default port 12345).
Keep it running while using the script.
2. Install Python Libraries
Open a Command Prompt as Administrator and run:

pip install buttplug numpy requests keyboard
(If keyboard fails, the script falls back to the built‑in msvcrt – that’s fine.)

3. Install & Set Up Ollama
Download OllamaSetup.exe from ollama.com and install.
By default models are stored on C:. To save space, set a different folder:
Open System Properties → Environment Variables.
Add a New System Variable:
Name: OLLAMA_MODELS
Value: D:\OllamaModels (or your preferred drive)
Restart your PC or the Ollama service.
Open a new Command Prompt and pull a lightweight model:
ollama pull phi4:latest
(You can also use gemma3:2b – even smaller.)

4. Download the Script
Save the script from the next section as hismith_ai.py on your desktop.

5. Run It
Make sure Intiface is running and your Hismith is connected (paired via Bluetooth or plugged in).
In a Command Prompt, navigate to the script folder and run:
python hismith_ai.py
You’ll see Connecting... then Connected to Hismith.
The machine will start with the softest pattern for 2 minutes (warm‑up).
Press g (good) or b (bad) while it runs.
Press b to instantly stop a bad pattern and go back to the softest.
Press Ctrl+C to quit.

Customization Tips
Parameter  	     Recommended          Value  	                              Purpose  
WARMUP_DURATION |	120 (seconds) |	How long the machine stays at its softest. Increase for longer warm‑up.

MAX_SPEED_INCREASE_PER_STEP |	15 |	Prevents sudden jumps. Lower = slower build. 

LLM_MODEL	| phi4:latest or gemma3:2b |	Which AI model to use for pattern generation. phi4 is balanced; gemma3:2b is smaller.

SCENARIO_DURATION	| 10 |	Seconds each pattern runs before the AI decides the next one.

Troubleshooting

No key presses registered – Focus the terminal window. If msvcrt fails, install keyboard (pip install keyboard as admin).

Ollama not responding – Make sure Ollama is running (check system tray). Run ollama list to see if model is downloaded.

Buttplug connection fails – Ensure Intiface Desktop is running and the Hismith is paired. Try restarting Intiface.

Stuck on “Connecting…” – Check machine batteries, Bluetooth, or USB connection.

Safety & Ethics
This is a self‑built experimental tool. Use at your own risk.
Always keep a physical emergency stop (power switch) nearby.
The AI is not sentient – it only selects patterns based on your feedback.
Patterns are generated locally – no data leaves your computer.

Get Involved
This is an open project. You can adapt the script, add new features (like webcam motion tracking, voice control, or sensor integration), and share your improvements. The code is provided as‑is – feel free to experiment!
