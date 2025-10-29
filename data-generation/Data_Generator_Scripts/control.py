import os
import subprocess
import random
import numpy as np
import csv
import sys
import shutil
from pathlib import Path

# --- CONFIGURATION ---
BLENDER_EXE_PATH = r"D:\Blender\blender.exe" # (Your Windows path)

# --- PROJECT PATHS ---
BASE_DIR = Path(__file__).resolve().parent.parent
BLENDER_SCENE = BASE_DIR / "Blender_Scene" / "rockfall_sim.blend"
WORKER_SCRIPT = BASE_DIR / "Data_Generator_Scripts" / "run_sim.py"
GENERATED_DATA_DIR = BASE_DIR / "Generated_Data"

# --- SCENARIO PARAMETERS ---
# How many "stories" do you want to generate?
TOTAL_SCENARIOS_TO_GENERATE = 10 # Let's generate 10 "weeks" of data
SCENARIO_DURATION_HOURS = 168   # 7-day scenario
 
# !!! THIS IS YOUR NEW CONTROL !!!
# What percentage of scenarios should be UNSTABLE?
# 0.3 = 30% of scenarios will be engineered to cause a rockfall.
# 0.5 = 50% stable, 50% unstable.
UNSTABLE_SCENARIO_CHANCE = 0.5 

# --- Trigger Logic Thresholds ---
SATURATION_THRESHOLD = 50.0 
VIBRATION_THRESHOLD = 4.0
FREEZE_THAW_THRESHOLD = 3

# --- GLOBAL VARIABLES ---
# We need a global hour counter to make sure image names are always unique
global_hour_counter = 0


class GroundState:
    """Tracks the derived temporal "ground memory" variables."""
    def __init__(self):
        self.ground_saturation_pct = 0.0
        self.freeze_thaw_cycles = 0
        self.last_temp = 0.0

    def update_state(self, rainfall, temp, wind):
        """Updates the ground state based on the current hour's weather."""
        if rainfall > 0:
            saturation_increase = rainfall * 0.75 
            self.ground_saturation_pct += saturation_increase
        else:
            evaporation_rate = (max(0, temp - 10) * 0.01) + (wind * 0.005)
            self.ground_saturation_pct -= evaporation_rate
        self.ground_saturation_pct = max(0, min(100, self.ground_saturation_pct))

        if self.last_temp < 0 and temp >= 0:
            self.freeze_thaw_cycles += 1
            print(f"  (Freeze-thaw cycle: {self.freeze_thaw_cycles})")
        self.last_temp = temp

    def apply_trigger_logic(self, weather):
        """Checks if the current state triggers a failure."""
        if self.ground_saturation_pct > SATURATION_THRESHOLD: 
            return "UNSTABLE", "Saturation Threshold Met"
        if weather["vibration_hz"] > VIBRATION_THRESHOLD and self.ground_saturation_pct > (SATURATION_THRESHOLD - 10.0):
            return "UNSTABLE", "Vibration + Saturation Met"
        if self.freeze_thaw_cycles >= FREEZE_THAW_THRESHOLD and self.last_temp < 0 and weather["temperature_C"] >= 0:
            return "UNSTABLE", "Freeze-Thaw Threshold Met"
        return "STABLE", "No Trigger"

# --- SCENARIO GENERATORS ---

def generate_stable_scenario_story():
    """
    Generates a 168-hour "story" of mild weather that is
    GUARANTEED *NOT* to cause a rockfall.
    """
    print("\n--- Generating NEW STABLE Scenario ---")
    weather_story = []
    for h in range(SCENARIO_DURATION_HOURS):
        hour_of_day = h % 24
        temp_variation = np.sin((hour_of_day - 8) * (2 * np.pi / 24))
        temperature_C = 7.5 + (temp_variation * 7.5) + random.uniform(-1, 1)
        
        # Low chance of very light rain
        rainfall_mm = random.uniform(0.1, 0.5) if random.random() < 0.05 else 0.0
        # No vibrations
        vibration_hz = 0.0
        wind_speed_kmh = random.uniform(5, 20)
        
        weather_story.append({
            "rainfall_mm": rainfall_mm, "temperature_C": temperature_C,
            "vibration_hz": vibration_hz, "wind_speed_kmh": wind_speed_kmh,
        })
    return weather_story


def generate_unstable_scenario_story():
    """
    Generates a 168-hour "story" that is
    GUARANTEED *TO* cause a rockfall.
    This creates the "precursor data" your model needs.
    """
    print("\n--- Generating NEW UNSTABLE Scenario (Saturation Event) ---")
    weather_story = []
    
    # This story will build up saturation
    # We'll make it rain for 3 days straight to force a trigger
    
    # Hours 0-95 (4 days): Mild, slightly wet weather
    for h in range(96): 
        hour_of_day = h % 24
        temp_variation = np.sin((hour_of_day - 8) * (2 * np.pi / 24))
        temperature_C = 10.0 + (temp_variation * 5.0) + random.uniform(-1, 1)
        rainfall_mm = random.uniform(0.1, 1.0) if random.random() < 0.2 else 0.0 # Light drizzle
        vibration_hz = 0.0
        wind_speed_kmh = random.uniform(5, 20)
        weather_story.append({
            "rainfall_mm": rainfall_mm, "temperature_C": temperature_C,
            "vibration_hz": vibration_hz, "wind_speed_kmh": wind_speed_kmh,
        })

    # Hours 96-167 (3 days): The "Storm" to force a trigger
    for h in range(96, SCENARIO_DURATION_HOURS):
        hour_of_day = h % 24
        temp_variation = np.sin((hour_of_day - 8) * (2 * np.pi / 24))
        temperature_C = 5.0 + (temp_variation * 3.0) # Colder
        rainfall_mm = random.uniform(1.0, 3.0) # Consistent, moderate rain
        vibration_hz = 0.0
        wind_speed_kmh = random.uniform(20, 40) # Windy
        weather_story.append({
            "rainfall_mm": rainfall_mm, "temperature_C": temperature_C,
            "vibration_hz": vibration_hz, "wind_speed_kmh": wind_speed_kmh,
        })
        
    return weather_story

# --- SCRIPT EXECUTION ---

def get_next_run_dir(base_data_dir):
    """Finds the next available 'Run_XXX' directory."""
    run_number = 1
    while True:
        run_dir = base_data_dir / f"Run_{run_number:03d}"
        if not os.path.exists(run_dir):
            print(f"Creating new run directory: {run_dir.name}")
            return run_dir
        run_number += 1

def setup_directories_and_log(log_file, img_dir, sensor_dir):
    """Creates output directories and the master log file header."""
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(sensor_dir, exist_ok=True)
    header = [
        "global_hour", "scenario_id", "hour_in_scenario",
        "rainfall_mm", "temperature_C", "vibration_hz", 
        "wind_speed_kmh", "ground_saturation_pct", "freeze_thaw_cycles", 
        "LABEL", "trigger_reason", "image_file"
    ]
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
    print(f"Directories and log file created in: {log_file.parent}")

def render_stable_template(blender_exe, blender_scene, worker_script, stable_image_path):
    """Launches Blender ONCE to render the stable (frame 0) image."""
    print("--- Pre-rendering STABLE template image... ---")
    cmd = [
        blender_exe, '-b', str(blender_scene),
        '--python', str(worker_script),
        '--',
        '--render_stable_template',
        f'--output_path={stable_image_path}'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"--- STABLE template saved to {stable_image_path} ---")
    except subprocess.CalledProcessError as e:
        print("!!! ERROR: Failed to render stable template image !!!")
        print(e.stderr)
        sys.exit(1)

def log_to_master(log_file, data_dict):
    """Appends a single hour's result to the master CSV log."""
    header = [
        "global_hour", "scenario_id", "hour_in_scenario",
        "rainfall_mm", "temperature_C", "vibration_hz", 
        "wind_speed_kmh", "ground_saturation_pct", "freeze_thaw_cycles", 
        "LABEL", "trigger_reason", "image_file"
    ]
    try:
        with open(log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writerow(data_dict)
    except Exception as e:
        print(f"Error: Could not write to master log file {log_file}: {e}")

def main():
    """Main "Boss" loop."""
    global global_hour_counter
    
    if not os.path.isfile(BLENDER_EXE_PATH):
        print(f"Error: Blender executable not found at '{BLENDER_EXE_PATH}'")
        sys.exit(1)

    # --- Setup new Run directory ---
    output_dir = get_next_run_dir(GENERATED_DATA_DIR)
    log_file = output_dir / "master_log.csv"
    img_dir = output_dir / "images"
    sensor_dir = output_dir / "sensor_data"
    stable_image_src = output_dir / "stable_image.png"
    
    setup_directories_and_log(log_file, img_dir, sensor_dir)
    render_stable_template(BLENDER_EXE_PATH, BLENDER_SCENE, WORKER_SCRIPT, stable_image_src) 
    
    # --- Main Scenario Generation Loop ---
    for scenario_id in range(1, TOTAL_SCENARIOS_TO_GENERATE + 1):
        
        # Decide what kind of story to generate
        if random.random() < UNSTABLE_SCENARIO_CHANCE:
            weather_story = generate_unstable_scenario_story()
        else:
            weather_story = generate_stable_scenario_story()
            
        ground_state = GroundState()
        unstable_event_triggered_in_this_scenario = False

        # --- Hourly Simulation Loop (for this one story) ---
        for hour_in_scenario, weather in enumerate(weather_story, 1):
            
            global_hour_counter += 1
            ground_state.update_state(
                weather["rainfall_mm"], weather["temperature_C"], weather["wind_speed_kmh"]
            )

            # Check for trigger, BUT only if one hasn't already happened in this story
            if not unstable_event_triggered_in_this_scenario:
                label, reason = ground_state.apply_trigger_logic(weather)
            else:
                label, reason = "STABLE", "Post-Failure" # Ignore triggers after one event

            print(f"  Scen {scenario_id}, Hour {hour_in_scenario}: Sat={ground_state.ground_saturation_pct:.2f}%, LABEL={label}")

            img_filename = f"img_h_{global_hour_counter:06d}.png"
            img_filepath = img_dir / img_filename
            
            log_data = {
                "global_hour": global_hour_counter,
                "scenario_id": scenario_id,
                "hour_in_scenario": hour_in_scenario,
                "rainfall_mm": f"{weather['rainfall_mm']:.4f}",
                "temperature_C": f"{weather['temperature_C']:.4f}",
                "vibration_hz": f"{weather['vibration_hz']:.4f}",
                "wind_speed_kmh": f"{weather['wind_speed_kmh']:.4f}",
                "ground_saturation_pct": f"{ground_state.ground_saturation_pct:.4f}",
                "freeze_thaw_cycles": ground_state.freeze_thaw_cycles,
                "image_file": img_filename,
                "LABEL": label,
                "trigger_reason": reason
            }
            
            if label == "UNSTABLE":
                unstable_event_triggered_in_this_scenario = True
                print(f"  *** UNSTABLE EVENT TRIGGERED! Reason: {reason} ***")
                print("  Launching Blender worker...")
                
                cmd = [
                    BLENDER_EXE_PATH, '-b', str(BLENDER_SCENE),
                    '--python', str(WORKER_SCRIPT),
                    '--',
                    f"--hour={global_hour_counter}", # Use global hour for unique filenames
                    f"--rainfall_mm={weather['rainfall_mm']}",
                    f"--temperature_C={weather['temperature_C']}",
                    f"--vibration_hz={weather['vibration_hz']}",
                    f"--wind_speed_kmh={weather['wind_speed_kmh']}",
                    f"--ground_saturation_pct={ground_state.ground_saturation_pct}",
                    f"--freeze_thaw_cycles={ground_state.freeze_thaw_cycles}",
                    f"--log_file={log_file}", # Not really used by worker, but good to pass
                    f"--img_dir={img_dir}",
                    f"--sensor_dir={sensor_dir}"
                ]
                try:
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                    print(f"  ERROR: Blender worker for hour {global_hour_counter} failed:")
                    print(e.stderr)

            else:
                # STABLE: Just copy the template image
                try:
                    shutil.copy(stable_image_src, img_filepath)
                except Exception as e:
                    print(f"  ERROR: Failed to copy stable image: {e}")

            log_to_master(log_file, log_data)

    print(f"\n--- Scenario generation complete. Data saved to {output_dir} ---")


if __name__ == "__main__":
    main()