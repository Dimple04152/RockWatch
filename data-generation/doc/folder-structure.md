```text
RockWatch/data-generation/
│
├── Blender_Scene/
│   └── rockfall_sim.blend          # Your main Blender file with the rigged quarry
│
├── Data_Generator_Scripts/
│   ├── control.py                  # The "Boss" script. This is the one you run.
│   └── run_sim.py                  # The "Worker" script. Blender runs this.
│
├── doc/
│   ├── data-gen.md                 # The main project documentation
│   ├── data-gen.docx               # A copy of the text for your Word doc
│   └── folder-structure.md         # This file
│
└── Generated_Data/
    │                               # This is your "Database".
    │
    └── Run_001/                    # A "Run" is one long scenario (e.g., 1 "year")
        │
        ├── master_log.csv          # <-- THIS IS THE MASTER FILE for your ML team.
        │
        ├── images/                 # All drone images (lightweight)
        │   ├── img_h_000001.png
        │   ├── img_h_000002.png
        │   └── ...
        │
        └── sensor_data/            # Contains *only* the CSVs for UNSTABLE events
            ├── sensor_h_005123.csv
            └── sensor_h_007122.csv            
```