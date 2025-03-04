import osmnx as ox
import geopandas as gpd

# Define the region of interest (Mecklenburg-Vorpommern, Germany)
region = "Mecklenburg-Vorpommern, Germany"

# Fetch energy-related infrastructure from OpenStreetMap
power_data = ox.features_from_place(region, tags={"power": True})

# Display first rows to understand the data
print(power_data.head())

# Save the raw data to a GeoJSON file for GIS use
power_data.to_file("mecklenburg_power_data.geojson", driver="GeoJSON")

print("Extracted power data and saved to 'mecklenburg_power_data.geojson'")

# Filter only power lines
power_lines = power_data[power_data["power"] == "line"]

# Filter only substations
substations = power_data[power_data["power"] == "substation"]

# Filter only transformers
transformers = power_data[power_data["power"] == "transformer"]

# Save each dataset separately for GIS use
power_lines.to_file("mecklenburg_power_lines.geojson", driver="GeoJSON")
substations.to_file("mecklenburg_substations.geojson", driver="GeoJSON")
transformers.to_file("mecklenburg_transformers.geojson", driver="GeoJSON")

print("Filtered and saved:")
print("  - Power Lines: 'mecklenburg_power_lines.geojson'")
print("  - Substations: 'mecklenburg_substations.geojson'")
print("  - Transformers: 'mecklenburg_transformers.geojson'")
