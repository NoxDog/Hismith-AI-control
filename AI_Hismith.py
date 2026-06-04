import asyncio
import numpy as np
import random
import json
import requests
import threading
from buttplug.client import ButtplugClient
from buttplug.command import DeviceOutputCommand, OutputType

# ===== CONFIGURATION =====
SPEED_MIN = 10
SPEED_MAX = 85
LEARNING_RATE = 0.3
DISCOUNT_FACTOR = 0.9
EXPLORATION_RATE = 0.2
SCENARIO_DURATION = 10
WARMUP_DURATION = 120          # seconds – only soft pattern during warmup
MAX_SPEED_INCREASE_PER_STEP = 15   # max base speed increase from one scenario to next
LLM_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "phi4:latest"

# Initial scenarios (base, amplitude, frequency, name)
SCENARIOS = [
    (15, 10, 0.3, "slow build"),
    (35, 20, 0.5, "heavy thrust"),
    (60, 25, 1.5, "fast thrust"),
]
Q = [0.0 for _ in SCENARIOS]

# Keyboard setup
USE_KEYBOARD_LIB = False
try:
    import keyboard
    USE_KEYBOARD_LIB = True
except ImportError:
    import msvcrt

feedback_buffer = []
feedback_lock = threading.Lock()
total_good = 0
total_bad = 0
stop_event = threading.Event()
device_feature_ref = None

# For smoothness
last_base_speed = SCENARIOS[0][0]   # start with slow pattern's base

def keyboard_listener():
    global feedback_buffer, total_good, total_bad
    if USE_KEYBOARD_LIB:
        def on_press(key):
            global feedback_buffer, total_good, total_bad
            try:
                if key.name == 'g':
                    with feedback_lock:
                        feedback_buffer.append(1.0)
                        total_good += 1
                    print("✔ Good")
                elif key.name == 'b':
                    with feedback_lock:
                        feedback_buffer.append(-0.5)
                        total_bad += 1
                    stop_event.set()
                    print("✘ Bad – stopping pattern")
            except:
                pass
        keyboard.on_press(on_press, suppress=False)
    else:
        while True:
            key = msvcrt.getch()
            if key == b'g':
                with feedback_lock:
                    feedback_buffer.append(1.0)
                    total_good += 1
                print("✔ Good")
            elif key == b'b':
                with feedback_lock:
                    feedback_buffer.append(-0.5)
                    total_bad += 1
                stop_event.set()
                print("✘ Bad – stopping pattern")

def get_softest_scenario():
    global SCENARIOS
    bases = [s[0] for s in SCENARIOS]
    return bases.index(min(bases))

def get_safe_scenarios(current_base, max_increase=MAX_SPEED_INCREASE_PER_STEP):
    """Return list of indices whose base speed is <= current_base + max_increase."""
    safe = []
    for i, (b, _, _, _) in enumerate(SCENARIOS):
        if b <= current_base + max_increase:
            safe.append(i)
    # Always at least include the softest
    if not safe:
        safe = [get_softest_scenario()]
    return safe

async def get_llm_pattern():
    prompt = f"""You are a pattern generator for a sex machine. Current patterns:
{', '.join([f"'{name}' (base {b}, amp {a}, freq {f} Hz)" for b,a,f,name in SCENARIOS])}

Generate a NEW, distinct pattern. Return ONLY valid JSON:
{{"name": "...", "base": integer 10-60, "amplitude": integer 5-30, "frequency": float 0.2-2.0}}
Example: {{"name": "teasing waves", "base": 20, "amplitude": 15, "frequency": 0.8}}
Do not include any other text."""
    try:
        resp = requests.post(LLM_URL, json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.9}
        }, timeout=30)
        text = resp.json()["response"].strip()
        if "{" in text:
            start = text.index("{")
            end = text.rindex("}")+1
            data = json.loads(text[start:end])
            base = int(np.clip(data["base"], 10, 60))
            amp = int(np.clip(data["amplitude"], 5, 30))
            freq = float(np.clip(data["frequency"], 0.2, 2.0))
            name = data.get("name", "llm pattern")
            return (base, amp, freq, name)
    except Exception as e:
        print(f"LLM error: {e}")
    return None

async def run_scenario_continuous(device_feature, scenario, duration_sec, global_time):
    base, amp, freq, _ = scenario
    steps = int(duration_sec / 0.05)
    for i in range(steps):
        if stop_event.is_set():
            await device_feature.stop()
            return global_time + i * 0.05
        t = (global_time + i * 0.05)
        raw = base + amp * (0.5 + 0.5 * np.sin(2 * np.pi * freq * t))
        raw += random.uniform(-3, 3)
        speed = int(np.clip(raw, SPEED_MIN, SPEED_MAX))
        cmd = DeviceOutputCommand(output_type=OutputType.OSCILLATE, value=speed)
        await device_feature.run_output(cmd)
        await asyncio.sleep(0.05)
    return global_time + duration_sec

async def main():
    global stop_event, device_feature_ref, feedback_buffer, total_good, total_bad, last_base_speed

    client = ButtplugClient("OllamaRL_Smooth")
    await client.connect("ws://127.0.0.1:12345")
    print("Connecting...")
    for _ in range(20):
        await asyncio.sleep(0.5)
        if client.devices:
            break
    else:
        print("No Hismith found.")
        return

    device = client.devices[0]
    feat = device._features[0]
    device_feature_ref = feat
    print(f"Connected to {device.name}")

    # Start keyboard listener thread
    t = threading.Thread(target=keyboard_listener, daemon=True)
    t.start()
    print("\n=== READY ===")
    print("Press 'g' (good) or 'b' (bad) anytime.")
    print("Pressing 'b' will immediately stop the current pattern and switch to the softest one.")
    print(f"First {WARMUP_DURATION} seconds: only the softest pattern.")
    print("After warm-up, speed increases are capped at +" + str(MAX_SPEED_INCREASE_PER_STEP) + " per step.")
    print("Press Ctrl+C to quit.\n")

    global_time = 0.0
    current_idx = get_softest_scenario()
    exploration = EXPLORATION_RATE
    stagnation_counter = 0
    last_best_index = None
    warmup = True

    try:
        while True:
            # Warm‑up check
            if global_time < WARMUP_DURATION:
                warmup = True
                next_idx = get_softest_scenario()
            else:
                warmup = False
                # Get allowed scenarios (smoothness filter)
                safe_indices = get_safe_scenarios(last_base_speed)
                if not safe_indices:
                    safe_indices = [get_softest_scenario()]
                # Epsilon‑greedy among safe indices
                if random.random() < exploration:
                    next_idx = random.choice(safe_indices)
                else:
                    # Choose best Q among safe indices
                    best_q = -1e9
                    best_idx = safe_indices[0]
                    for idx in safe_indices:
                        if Q[idx] > best_q:
                            best_q = Q[idx]
                            best_idx = idx
                    next_idx = best_idx

            # Run scenario
            global_time = await run_scenario_continuous(feat, SCENARIOS[next_idx], SCENARIO_DURATION, global_time)
            last_base_speed = SCENARIOS[next_idx][0]   # update for next selection

            # Check stop event
            interrupted = stop_event.is_set()
            if interrupted:
                with feedback_lock:
                    feedback_buffer.clear()
                Q[next_idx] += LEARNING_RATE * (-0.5 + DISCOUNT_FACTOR * max(Q) - Q[next_idx])
                print(f"Interrupted. Negative reward applied.")
                await feat.stop()
                next_idx = get_softest_scenario()
                last_base_speed = SCENARIOS[next_idx][0]
                print(f"Forced to softest: {SCENARIOS[next_idx][3]}")
                stop_event.clear()
                continue

            # Process feedback (only if not interrupted)
            with feedback_lock:
                rewards = feedback_buffer[:]
                feedback_buffer.clear()
            if rewards:
                for rew in rewards:
                    Q[next_idx] += LEARNING_RATE * (rew + DISCOUNT_FACTOR * max(Q) - Q[next_idx])
                print(f"Scenario {next_idx+1} updated. Q: {[f'{q:.2f}' for q in Q]} | G:{total_good} B:{total_bad} | Last base:{last_base_speed}")

            # Stagnation detection (only after warmup)
            if not warmup:
                current_best = int(np.argmax(Q))
                if current_best == last_best_index:
                    stagnation_counter += 1
                else:
                    stagnation_counter = 0
                    last_best_index = current_best

                if stagnation_counter >= 5:
                    print("Requesting new pattern from LLM...")
                    new_scenario = await get_llm_pattern()
                    if new_scenario:
                        SCENARIOS.append(new_scenario)
                        Q.append(0.0)
                        print(f"Added: {new_scenario[3]}")
                        exploration = min(1.0, exploration * 2)
                    else:
                        print("Failed.")
                    stagnation_counter = 0

            # Exploration decay
            if exploration > EXPLORATION_RATE:
                exploration *= 0.95
            exploration = max(EXPLORATION_RATE, exploration)

            current_idx = next_idx

    except KeyboardInterrupt:
        pass
    finally:
        await feat.stop()
        await client.disconnect()
        print("Stopped.")

if __name__ == "__main__":
    asyncio.run(main())
