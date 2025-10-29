# Project Documentation: AI Rockfall Synthetic Data Generation

**(Version 2.0: Hourly & Stateful)**

## 1. Project Goal

To build a predictive AI model trained on multi-source synthetic data. The model must ingest environmental and sensor data to predict the _probability_ of a rockfall on an hourly basis.

## 2. The Core Solution: The "Data Factory"

We are building a "Digital Twin" data generator. This factory simulates realistic, multi-day scenarios to generate a large, labeled dataset for training our AI.

- **The "Factory" (Blender):** `Blender_Scene/rockfall_sim.blend`
  - This is our 3D quarry. It acts as the "stage."
  - The pre-animated rockfall (`Zone_A_Fragments`) is our "on/off switch" to generate an `UNSTABLE` event.
- **The "Boss" (Python):** `Data_Generator_Scripts/control.py`
  - This is an **Hourly Scenario Generator**. It runs _outside_ Blender.
  - Its job is to write realistic "stories" (e.g., a 7-day, 168-hour weather sequence) that respect real-world physics and temporal constraints.
- **The "Worker" (Python):** `Data_Generator_Scripts/run_sim.py`
  - This script is run _by_ Blender (in the background) for _every hour_ of a scenario.
  - It takes the hourly data from the "Boss," runs the "trigger logic," and saves the resulting data.

## 3. Key Conditions & Temporal Constraints (The "Brain")

This is the most critical part of the generator. Our "Boss" script will track two types of data to create realistic scenarios.

### A. Primary Environmental Inputs (Per-Hour Events)

These are the four direct variables generated for each simulated day:

1.  **Rainfall (`rainfall_mm`):** Simulates saturation.
2.  **Temperature (`temperature_C`):** Simulates freeze-thaw cycles.
3.  **Vibrations (`vibration_hz`):** Simulates short, high-energy events (e.g., blasting, machinery).
4.  **Wind (`wind_speed_kmh`):** A secondary stress factor, especially when correlated with rain.

### B. Derived Temporal Constraints (Accumulated State)

These are "ground memory" variables tracked by `control.py` over a sequence of days. This is what allows for the simulation of complex, real-world failures.

1.  **Ground Saturation (`ground_saturation_pct`):**
    - **What:** A "sponge" model (0-100%).
    - **How:** `Rainfall` increases it. Dry, windy, or warm hours slowly decrease it (evaporation/drainage). This models the _accumulation_ of water.
2.  **Freeze-Thaw Cycles (`freeze_thaw_cycles`):**
    - **What:** A counter.
    - **How:** The counter increments by `+1` every time the `temperature_C` _crosses_ the 0°C mark (e.g., from -2°C to 1°C). This models the "ice wedge" effect.

## 4. The Generation Loop (Hourly Labeling)

This is how we get the "consecutive day" data your ML team needs.

1.  The "Boss" (`control.py`) starts a new 1-week (168-hour) scenario. It initializes `ground_saturation` to 0.
2.  **For Hour 1 to 163:**
    - It generates a "stable" weather event (e.g., light drizzle).
    - It updates the state: `ground_saturation` slowly rises from 0% to 94%.
    - It launches the "Worker" (`run_sim.py`) for each hour.
    - The "Worker's" logic (`apply_trigger_logic()`) checks the state: `if ground_saturation_pct > 95: ...` **(False)**.
    - The "Worker" _does not_ run the animation.
    - It saves a "drone" image of the _intact_ cliff.
    - It logs the result: **`LABEL = STABLE`**.
3.  **For Hour 164:**
    - It generates one more hour of rain.
    - It updates the state: `ground_saturation` is now `95.5%`.
    - It launches the "Worker."
    - The "Worker's" logic checks the state: `if ground_saturation_pct > 95: ...` **(True)**.
    - **Decision:** `trigger_rockfall = TRUE`.
    - The "Worker" _activates_ the hidden rockfall animation.
    - It records the "sensor" CSV of the rocks falling.
    - It saves the "drone" image of the _fallen_ rocks.
    - It logs the result: **`LABEL = UNSTABLE`**.
4.  The scenario ends. The result is a 164-hour dataset: 163 `STABLE` points and 1 `UNSTABLE` point.

## 5. Critical Information for the ML Team

This dataset is specifically designed to train a **temporal predictive model** (like an LSTM or RNN).

- **How to Use:** The `master_log.csv` (see `folder_structure.md`) is your primary file. Each row is one hour of data.
- **Training Goal:** Your model's goal is to **predict the `LABEL` for Hour `H`**.
- **Training Features:** To make this prediction, you must feed the model a _sequence_ of data from the _past_ (e.g., Hours `H-24` through `H-1`).
- **What the AI Will Learn:** The AI will not just learn "rain = bad." It will learn complex, real-world **precursor patterns**:
  - *"It will learn that the risk of failure *gradually increases* as `ground_saturation` rises over 72 hours."*
  - _"It will learn that a `vibration_hz` of 4.0 is safe when `ground_saturation` is 20%, but is critical when `ground_saturation` is 90%."_
  - _"It will learn that the 3rd `freeze_thaw_cycle` in a week is the most likely to cause a failure."_
