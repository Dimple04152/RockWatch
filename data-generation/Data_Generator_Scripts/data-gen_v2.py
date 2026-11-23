import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. SETUP LOCATIONS ---
locations = [
    {'Location_ID': 'Case_1_Low_Risk',       'Slope_Angle': 30.0, 'Fracturing_Density': 0.1, 'Aspect': 45.0},
    {'Location_ID': 'Case_2_Extreme_Risk',   'Slope_Angle': 70.0, 'Fracturing_Density': 0.8, 'Aspect': 225.0},
    {'Location_ID': 'Case_3_The_Sponge',     'Slope_Angle': 45.0, 'Fracturing_Density': 0.9, 'Aspect': 240.0},
    {'Location_ID': 'Case_4_Freeze_Thaw',    'Slope_Angle': 55.0, 'Fracturing_Density': 0.4, 'Aspect': 180.0},
    {'Location_ID': 'Case_5_The_Deceptive',  'Slope_Angle': 35.0, 'Fracturing_Density': 0.7, 'Aspect': 270.0}
]

# --- 2. CONFIGURATION FOR RAIN ONLY (Temp is removed) ---
season_configs = {
    'Summer': { 'months': [3, 4, 5, 6],     'rain_prob': 0.05, 'rain_intensity': (1, 5) },
    'Rainy':  { 'months': [7, 8, 9],        'rain_prob': 0.40, 'rain_intensity': (5, 20) },
    'Winter': { 'months': [10, 11, 12, 1, 2], 'rain_prob': 0.10, 'rain_intensity': (1, 8) }
}

# --- 3. GENERATE GLOBAL WEATHER (Smooth Temp + Seasonal Rain) ---
dates = pd.date_range(start='2024-01-01', end='2025-01-01', freq='h')[:-1] # 8784 hours
df_global = pd.DataFrame({'Timestamp': dates})

# A. SMOOTH TEMPERATURE (The Fix)
# We use a sine wave peaking in June (approx day 172)
day_of_year = df_global['Timestamp'].dt.dayofyear
hour_of_day = df_global['Timestamp'].dt.hour

# Constants for your location (e.g., India/Global average)
yearly_avg = 20.0  # Average annual temp
yearly_var = 15.0  # Swings by +/- 15 degrees (5°C winter to 35°C summer)

# 1. Yearly Cycle (Smooth Curve)
# Cosine wave shifted so peak is in mid-year
yearly_curve = yearly_avg - yearly_var * np.cos((day_of_year - 15) * 2 * np.pi / 365)

# 2. Daily Cycle (Smooth Curve)
daily_cycle = 5.0 * np.sin((hour_of_day - 9) * 2 * np.pi / 24)

# 3. Combine
df_global['Base_Temp'] = yearly_curve + daily_cycle + np.random.normal(0, 1.5, len(dates))


# B. SEASONAL RAIN (Discrete Blocks)
rain_data = []
is_raining = False

for i, timestamp in enumerate(dates):
    month = timestamp.month
    
    # Pick the Rain Config based on Month
    if month in season_configs['Summer']['months']:
        cfg = season_configs['Summer']
    elif month in season_configs['Rainy']['months']:
        cfg = season_configs['Rainy']
    else:
        cfg = season_configs['Winter']

    # Rain State Machine
    if not is_raining:
        if np.random.rand() < cfg['rain_prob'] / 24:
            is_raining = True
            rain_data.append(np.random.uniform(*cfg['rain_intensity']))
        else:
            rain_data.append(0)
    else:
        # If it's raining, we tend to stay raining (70% chance)
        if np.random.rand() < 0.70:
            rain_data.append(np.random.uniform(*cfg['rain_intensity']))
        else:
            is_raining = False
            rain_data.append(0)

df_global['Rainfall_Hourly'] = rain_data


# --- 4. APPLY PHYSICS (Per Location) ---
final_dfs = []

for loc in locations:
    df_loc = df_global.copy()
    df_loc['Location_ID'] = loc['Location_ID']
    
    # Static Features
    df_loc['Slope_Angle'] = loc['Slope_Angle']
    df_loc['Fracturing_Density'] = loc['Fracturing_Density']
    df_loc['Aspect'] = loc['Aspect']

    # 1. Freeze-Thaw (With Aspect)
    is_sunny = (loc['Aspect'] >= 135) & (loc['Aspect'] <= 225)
    temp_mod = 5.0 if is_sunny else -5.0
    df_loc['Local_Temp'] = df_loc['Base_Temp'] + temp_mod
    
    temp_sign = np.sign(df_loc['Local_Temp'])
    df_loc['Freeze_Thaw_Cycle'] = (temp_sign != temp_sign.shift(1)).fillna(0).astype(int)

    # 2. Pore Pressure (With Rain Multiplier)
    df_loc['Rainfall_24h_Rolling'] = df_loc['Rainfall_Hourly'].rolling(window=24).sum().fillna(0)
    rain_multiplier = 1.0 + (loc['Fracturing_Density'] * 2.0)
    df_loc['Pore_Water_Pressure'] = 5.0 + (df_loc['Rainfall_24h_Rolling'] * rain_multiplier)

    # 3. Seismic
    df_loc['Seismic_Energy'] = np.random.uniform(0, 0.5, len(df_loc))
    blast_mask = (df_loc['Timestamp'].dt.dayofweek == 4) & (df_loc['Timestamp'].dt.hour == 14)
    df_loc.loc[blast_mask, 'Seismic_Energy'] = 50.0

    # 4. Factor of Safety
    base_stability = 100 - (loc['Slope_Angle'] * 1.2) - (loc['Fracturing_Density'] * 40)
    stress = (df_loc['Pore_Water_Pressure'] * 0.8) + \
             (df_loc['Freeze_Thaw_Cycle'] * 15.0) + \
             (df_loc['Seismic_Energy'] * 0.5)
             
    df_loc['Safety_Score'] = base_stability - stress
    df_loc['Rockfall_Occurred'] = (df_loc['Safety_Score'] < 0).astype(int)
    
    final_dfs.append(df_loc)

full_dataset = pd.concat(final_dfs)

# --- 5. VISUALIZATION (To Verify Smoothness) ---
# Plot just the first location to check the Temperature curve
"""subset = full_dataset[full_dataset['Location_ID'] == 'Case_1_Low_Risk']
plt.figure(figsize=(12, 4))
plt.plot(subset['Timestamp'], subset['Base_Temp'], label='Temperature (Smooth)', color='orange', linewidth=0.5)
plt.title("Verified: Smooth Yearly Temperature Cycle")
plt.ylabel("Temp (°C)")
plt.show()
"""

# Save
full_dataset.to_csv('simulated_rockfall_smooth_temp.csv', index=False)