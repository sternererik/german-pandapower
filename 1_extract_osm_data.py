import osmnx as ox
import geopandas as gpd
from datetime import datetime
import time
import os

def log(message, indent=0):
    timestamp = datetime.now().strftime("%H:%M:%S")
    indent_str = "  " * indent
    print(f"[{timestamp}] {indent_str}{message}")

def fetch_with_progress(region, tags, description):
    log(f"Starting fetch of {description}...")
    try:
        result = ox.features_from_place(
            "Landkreis Vorpommern-Greifswald, Germany",
            tags=tags
        )
        log(f"✅ Completed {description}! Found {len(result)} objects", indent=1)
        return result
    except Exception as e:
        log(f"❌ Error fetching {description}: {str(e)}", indent=1)
        raise

# Create data directory if it doesn't exist
data_dir = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(data_dir, exist_ok=True)

# Define the region of interest
region = "Landkreis Vorpommern-Greifswald, Germany"

try:
    # Fetch power infrastructure from OSM
    log("=== STEP 1: POWER INFRASTRUCTURE ===")
    power_data = fetch_with_progress(region, {"power": True}, "power infrastructure")

    # Fetch buildings
    log("\n=== STEP 2: BUILDINGS ===")
    buildings = fetch_with_progress(region, {"building": True}, "buildings")

    # Fetch national parks
    log("\n=== STEP 3: NATIONAL PARKS ===")
    national_parks = fetch_with_progress(region, 
        {
            "boundary": "national_park",
            "leisure": "nature_reserve",
            "landuse": "national_park"
        }, 
        "national parks and nature reserves"
    )

    # Filter data
    log("\n=== STEP 4: FILTERING ===")
    log("Filtering power infrastructure...")
    power_lines = power_data[power_data["power"] == "line"]
    log(f"Found {len(power_lines)} power lines", indent=1)

    substations = power_data[power_data["power"] == "substation"]
    log(f"Found {len(substations)} substations", indent=1)

    transformers = power_data[power_data["power"] == "transformer"]
    log(f"Found {len(transformers)} transformers", indent=1)

    # Coordinate conversion
    log("\n=== STEP 5: COORDINATE CONVERSION ===")
    log("Converting coordinate systems...")
    substations = substations.to_crs("EPSG:3857")
    buildings = buildings.to_crs("EPSG:3857")
    national_parks = national_parks.to_crs("EPSG:3857")
    log("Conversion complete", indent=1)

    # Distance calculations and filtering
    log("\n=== STEP 6: DISTANCE CALCULATIONS AND FILTERING ===")
    log("Calculating distances and filtering...")
    start_time = time.time()
    
    def has_open_space(substation_geometry, buildings_gdf, radius=1000):
        buffer = substation_geometry.buffer(radius)
        total_area = buffer.area
        buildings_in_buffer = buildings_gdf[buildings_gdf.intersects(buffer)]
        if len(buildings_in_buffer) == 0:
            return True
        buildings_area = buildings_in_buffer.geometry.buffer(25).unary_union.intersection(buffer).area
        return (buildings_area / total_area) < 0.5

    # Filter substations based on all criteria
    filtered_substations = substations[
        substations.geometry.apply(lambda x: 
            (buildings.distance(x).min() >= 25 or has_open_space(x, buildings))
            and
            not national_parks.geometry.intersects(x).any()
        )
    ]
    
    elapsed = time.time() - start_time
    log(f"Filtered out {len(substations) - len(filtered_substations)} substations (time: {elapsed:.1f}s)", indent=1)
    log(f"Kept {len(filtered_substations)} stations", indent=1)

    # Save results
    log("\n=== STEP 7: SAVING RESULTS ===")
    log("Saving files...")
    
    # Define file paths in data directory
    power_lines_path = os.path.join(data_dir, "mecklenburg_power_lines.geojson")
    substations_path = os.path.join(data_dir, "mecklenburg_substations_filtered.geojson")
    transformers_path = os.path.join(data_dir, "mecklenburg_transformers.geojson")
    
    # Save files
    power_lines.to_file(power_lines_path, driver="GeoJSON")
    filtered_substations.to_file(substations_path, driver="GeoJSON")
    transformers.to_file(transformers_path, driver="GeoJSON")
    log(f"All files saved to {data_dir}", indent=1)

    log("\n PROCESS COMPLETE!")

except KeyboardInterrupt:
    log("\n⚠️ Process interrupted by user")
except Exception as e:
    log(f"\n An error occurred: {str(e)}")
