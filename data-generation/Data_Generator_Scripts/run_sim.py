import bpy
import sys
import os
import argparse
import csv
from pathlib import Path

# --- CONSTANTS (from Blender scene) ---
# This is the animated piece of the cliff
ROCKFALL_COLLECTION_NAME = "Zone_A_Low"
CAMERA_NAME = "Drone_Camera"
ANIM_START_FRAME = 0
ANIM_END_FRAME = 240


def parse_arguments():
    """Parses command-line arguments."""
    try:
        argv = sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        argv = []
        
    if '--render_stable_template' in argv:
        parser_template = argparse.ArgumentParser()
        parser_template.add_argument('--render_stable_template', action='store_true')
        parser_template.add_argument('--output_path', type=str, required=True)
        args = parser_template.parse_args(args=argv)
        return args

    parser = argparse.ArgumentParser(description="Blender Worker Script (UNSTABLE Events)")
    parser.add_argument("--hour", type=int, required=True)
    parser.add_argument("--rainfall_mm", type=float, required=True)
    parser.add_argument("--temperature_C", type=float, required=True)
    parser.add_argument("--vibration_hz", type=float, required=True)
    parser.add_argument("--wind_speed_kmh", type=float, required=True)
    parser.add_argument("--ground_saturation_pct", type=float, required=True)
    parser.add_argument("--freeze_thaw_cycles", type=int, required=True)
    parser.add_argument("--log_file", type=str, required=True)
    parser.add_argument("--img_dir", type=str, required=True)
    parser.add_argument("--sensor_dir", type=str, required=True)
    
    args = parser.parse_args(args=argv)
    args.render_stable_template = False
    return args


def setup_scene(collection_name):
    """
    Gets scene objects AND FORCES all the correct render settings.
    This function OVERRIDES your .blend file settings.
    """
    print("Worker: Setting up scene...")
    rockfall_collection = bpy.data.collections.get(collection_name)
    camera_obj = bpy.data.objects.get(CAMERA_NAME)

    if not rockfall_collection:
        print(f"Error: Cannot find rockfall COLLECTION named '{collection_name}'")
        sys.exit(1)
    if not camera_obj:
        print(f"Error: Cannot find camera named '{CAMERA_NAME}'")
        sys.exit(1)

    bpy.context.scene.camera = camera_obj
    
    # --- RENDER SPEEDUP (for Blender 4.x) ---
    print("  Setting render engine to EEVEE_NEXT")
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT' 
    print("  Setting render samples to 16")
    bpy.context.scene.eevee.taa_render_samples = 16 
    
    # --- RENDER FIXES ---
    print("  Setting output format to PNG")
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024
    
    print("  FIX: Setting film_transparent to False")
    bpy.context.scene.render.film_transparent = False 
    
    print("  FIX: Setting World background color")
    world = bpy.context.scene.world
    if world:
        if world.use_nodes and world.node_tree:
            bg_node = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
            if bg_node:
                bg_node.inputs['Color'].default_value = (0.05, 0.15, 0.3, 1.0)
                bg_node.inputs['Strength'].default_value = 1.0
        else:
            world.color = (0.05, 0.15, 0.3)
    
    print("  FIX: Setting camera clip_end to 2000.0m")
    camera_obj.data.clip_end = 2000.0

    print("Worker: Scene setup complete.")
    return rockfall_collection


def render_image(filepath):
    """Renders the current scene frame and saves it."""
    print(f"  Rendering image to {filepath}...")
    bpy.context.scene.render.filepath = str(filepath)
    bpy.ops.render.render(write_still=True)
    print("  Render complete.")


def log_sensor_data(filepath, rockfall_collection):
    """Records the "sensor" CSV data for an UNSTABLE event."""
    print(f"  Logging sensor data (Frames {ANIM_START_FRAME}-{ANIM_END_FRAME})...")
    rock_fragments = [obj for obj in rockfall_collection.objects if obj.type == 'MESH']
    
    if not rock_fragments:
        print(f"  Warning: No MESH objects found in collection '{rockfall_collection.name}' to log.")
        return

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['frame', 'particle_id', 'x', 'y', 'z'])
        
        for frame in range(ANIM_START_FRAME, ANIM_END_FRAME + 1):
            bpy.context.scene.frame_set(frame)
            for obj in rock_fragments:
                world_loc = obj.matrix_world.translation
                writer.writerow([
                    frame, obj.name,
                    f"{world_loc.x:.4f}", f"{world_loc.y:.4f}", f"{world_loc.z:.4f}"
                ])
    print(f"  Logged {len(rock_fragments)} fragments over {ANIM_END_FRAME+1} frames.")


def do_stable_render(rockfall_collection, output_path):
    """Job 1: Render the STABLE template image (Frame 0)."""
    print("Worker: Received job 'render_stable_template'")
    
    # --- THIS IS THE CORRECT LOGIC ---
    print(f"  Making '{ROCKFALL_COLLECTION_NAME}' VISIBLE for STABLE render.")
    rockfall_collection.hide_render = False
    
    print(f"  Setting frame to {ANIM_START_FRAME} for 'before' shot.")
    bpy.context.scene.frame_set(ANIM_START_FRAME) 
    
    render_image(output_path)
    print(f"Worker: Saved stable template to {output_path}")


def do_unstable_event(params, rockfall_collection):
    """Job 2: Render UNSTABLE event (Frame 240) and log sensors."""
    print(f"Worker: Received job 'UNSTABLE' for Hour {params.hour}")
    
    rockfall_collection.hide_render = False 
    
    sensor_filename = f"sensor_h_{params.hour:06d}.csv"
    sensor_filepath = os.path.join(params.sensor_dir, sensor_filename)
    
    # --- !!! THIS IS THE FIX !!! ---
    # Removed the stray underscore from 'log_sensor_.data'
    log_sensor_data(sensor_filepath, rockfall_collection)
    
    # Set scene to FINAL frame for render
    bpy.context.scene.frame_set(ANIM_END_FRAME)
    
    img_filename = f"img_h_{params.hour:06d}.png"
    img_filepath = os.path.join(params.img_dir, img_filename)
    render_image(img_filepath)
    
    print(f"  Worker for Hour {params.hour} complete. Saved image and sensor data.")


def main():
    """Main "Worker" execution flow."""
    params = None
    try:
        params = parse_arguments()
        rockfall_collection = setup_scene(ROCKFALL_COLLECTION_NAME)

        if params.render_stable_template:
            do_stable_render(rockfall_collection, params.output_path)
        else:
            do_unstable_event(params, rockfall_collection)

    except Exception as e:
        print(f"Blender worker script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 

if __name__ == "__main__":
    main()