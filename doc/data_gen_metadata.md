## 📄 Metadata for `master_log.csv`

This file is the **primary source of truth for training your predictive model**. Each row represents one simulated hour.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| **Indexing** | | |
| `global_hour` | `int` | A unique, sequential ID for every hour generated, across all scenarios. File names (`img_h_...`, `sensor_h_...`) are based on this. |
| `scenario_id` | `int` | An ID for the "story" or "week" this hour belongs to (e.g., 1, 2, 3...). |
| `hour_in_scenario` | `int` | The hour *within* that story, from 1 to 168. |
| **Static Scenario Parameters** | | (These values are constant for an entire scenario, i.e., for all 168 hours of a single `scenario_id`) |
| `simulated_RMR` | `float` | **Rock Mass Rating.** A simulated score (30-80) for rock quality. **Lower = weaker rock.** |
| `simulated_discontinuity_score` | `int` | **Rock Jointing.** A simulated score (0, 1, 2) for fractures. **Higher = more joints = weaker rock.** |
| `simulated_slope_angle` | `float` | **Slope Angle.** The simulated steepness of the slope in degrees (40-80). **Higher = steeper = less stable.** |
| **Hourly Environmental Inputs** | | (These are the direct "weather" inputs for the hour) |
| `rainfall_mm` | `float` | The *amount* of rain (in mm) that fell during this hour. |
| `temperature_C` | `float` | The average air temperature (in Celsius) for this hour. |
| `vibration_hz` | `float` | The peak vibration (e.g., from blasting/machinery) for this hour. `0` for most hours. |
| `wind_speed_kmh` | `float` | The average wind speed for this hour. |
| **Hourly Derived State** | | (These are the "ground memory" variables calculated by the simulation) |
| `ground_saturation_pct` | `float` | **Pore Pressure Proxy.** The key "sponge" model state (0-100%). A primary driver of failure. |
| `freeze_thaw_cycles` | `int` | **Strain Proxy.** A counter of how many times the temperature has crossed from \< 0°C to \>= 0°C. |
| `consecutive_rain_hours` | `int` | A counter of how many hours in a row it has been raining. |
| `rainfall_intensity_mm_hr`| `float` | The amount of rain in this hour (same as `rainfall_mm` but explicit). |
| `weathering_factor` | `float` | **Rock Weakening.** A simulated factor (starts at 1.0, slowly decreases) representing gradual weakening. |
| `daily_max_temp` | `float` | The maximum temperature seen so far *today* (resets at midnight). |
| `daily_min_temp` | `float` | The minimum temperature seen so far *today* (resets at midnight). |
| `diurnal_range` | `float` | The difference between `daily_max_temp` and `daily_min_temp`. |
| **Target & Output** | | |
| `LABEL` | `string` | **The Target Variable.** `STABLE` or `UNSTABLE`. |
| `trigger_reason` | `string` | **Debug Info.** *Why* the label became `UNSTABLE` (e.g., "Saturation Threshold Met"). |
| `image_file` | `string` | The filename of the drone image associated with this hour (e.g., `img_h_000123.png`). |

-----

## 📁 Standard Data Folder Structure (Data Batches)

You asked how many folders you will be keeping. The system is designed to put all generated data into **one main run folder (a "data batch")** at a time.

Your `generate_dataset.bat` script is configured to put everything into **`Run_001`**. If you run it again, it will *append* new scenarios to the *same* `Run_001` folder and `master_log.csv`.

If you want to create a new, clean "batch" (e.g., for a different experiment), you just need to change the `RUN_NAME` variable in `generate_dataset.bat` from `Run_001` to `Run_002`.

Here is the **standard format** you can expect inside any `Run_XXX` folder:

```text
Generated_Data/
│
└── Run_001/                  <-- This is your "Data Batch"
    │
    ├── master_log.csv        <-- THIS IS THE MAIN FILE. (Metadata above)
    │
    ├── stable_image.png      <-- A lightweight template image. (Can be ignored by processing).
    │
    ├── images/               <-- Folder for ALL hourly images.
    │   ├── img_h_000001.png
    │   ├── img_h_000002.png
    │   └── ...
    │
    └── sensor_data/          <-- Folder ONLY for UNSTABLE event CSVs.
        ├── sensor_h_000129.csv   (If global_hour 129 was UNSTABLE)
        ├── sensor_h_000345.csv   (If global_hour 345 was UNSTABLE)
        └── ...
```

### File Naming Convention

Your processing scripts can rely on this standard:

  * **Images:** `img_h_{GLOBAL_HOUR}.png`
  * **Sensor Data:** `sensor_h_{GLOBAL_HOUR}.csv`

The `global_hour` in the filename will **always** match the `global_hour` column in the `master_log.csv`, allowing you to easily join all data sources.