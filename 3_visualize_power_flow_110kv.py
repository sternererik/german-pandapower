import folium
import geopandas as gpd
import pandas as pd
import os
from shapely.geometry import Point, Polygon, MultiPolygon

# Define data directory
data_dir = os.path.join(os.path.dirname(__file__), 'data')

# Load GeoJSON files
power_lines = gpd.read_file(os.path.join(data_dir, "mecklenburg_power_lines.geojson"))
substations = gpd.read_file(os.path.join(data_dir, "mecklenburg_substations_filtered.geojson"))
transformers = gpd.read_file(os.path.join(data_dir, "mecklenburg_transformers.geojson"))

# Load power flow simulation results
power_flow = pd.read_csv(os.path.join(data_dir, "power_flow_lubmin_lines.csv"))

# Filter out substations with no voltage information
substations = substations[substations['voltage'].notna()]
print(f"Antal substationer efter filtrering (med spänningsvärde): {len(substations)}")

# Filter power lines to only include 110kV lines
def get_voltage(voltage_str):
    if not voltage_str or pd.isna(voltage_str):
        return 0
    voltages = [int(v) for v in str(voltage_str).split(';') if v.strip().isdigit()]
    return max(voltages) if voltages else 0

power_lines['max_voltage'] = power_lines['voltage'].apply(get_voltage)
power_lines_110kv = power_lines[power_lines['max_voltage'] == 110000]
print(f"Antal kraftledningar (110kV): {len(power_lines_110kv)} av totalt {len(power_lines)}")

# Convert to WGS84 (lat/lon) if needed
substations = substations.to_crs("EPSG:4326")
transformers = transformers.to_crs("EPSG:4326")
power_lines_110kv = power_lines_110kv.to_crs("EPSG:4326")

# Debug prints
print(f"Antal transformatorer: {len(transformers)}")

# Create a Folium map centered on Lubmin
m = folium.Map(location=[54.1453, 13.6422], zoom_start=12)

# Add power lines with color-coded power flow
for idx, row in power_lines_110kv.iterrows():
    if row.geometry and row.geometry.geom_type == "LineString":
        # Get power flow loading % (if available)
        try:
            line_loading = power_flow.iloc[idx]["loading_percent"]
        except IndexError:
            line_loading = 0  # Default if no power flow data

        # Assign color based on power flow loading
        if line_loading < 50:
            color = "green"
        elif 50 <= line_loading < 80:
            color = "orange"
        else:
            color = "red"

        # Create popup message showing voltage & power flow
        popup_text = f"Voltage: 110 kV<br>Power Flow: {line_loading:.2f}%"

        # Add power line with popup
        folium.PolyLine(
            locations=[[lat, lon] for lon, lat in row.geometry.coords],
            color=color,
            weight=2.5,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

        # Add a label at the midpoint of the line showing power flow %
        mid_index = len(row.geometry.coords) // 2
        mid_point = row.geometry.coords[mid_index]

        folium.Marker(
            location=[mid_point[1], mid_point[0]],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 10pt; color: {color}; font-weight: bold;">{line_loading:.2f}%</div>'
            )
        ).add_to(m)

# Add substations as markers
for _, row in substations.iterrows():
    try:
        if row.geometry.is_empty:
            continue

        if isinstance(row.geometry, (Polygon, MultiPolygon)):
            centroid = row.geometry.centroid
            location = [centroid.y, centroid.x]
        else:
            location = [row.geometry.y, row.geometry.x]

        # Format voltage value for display
        voltage_value = row.get('voltage', 'Unknown')
        if voltage_value != 'Unknown':
            voltage_display = f"{voltage_value}V"
        else:
            voltage_display = "Unknown Voltage"

        folium.CircleMarker(
            location=location,
            radius=8,
            color="blue",
            fill=True,
            popup=f"Substation: {row.get('name', 'Unknown')}<br>Voltage: {voltage_display}"
        ).add_to(m)
    except Exception as e:
        print(f"Error adding substation: {e}")

# Add transformers as markers
for _, row in transformers.iterrows():
    try:
        if row.geometry.is_empty:
            continue

        if isinstance(row.geometry, (Polygon, MultiPolygon)):
            centroid = row.geometry.centroid
            location = [centroid.y, centroid.x]
        else:
            location = [row.geometry.y, row.geometry.x]

        folium.CircleMarker(
            location=location,
            radius=5,
            color="orange",
            fill=True,
            popup=f"Transformer: {row.get('name', 'Unknown')}<br>Voltage: {row.get('voltage', 'Unknown')}V"
        ).add_to(m)
    except Exception as e:
        print(f"Error adding transformer: {e}")

# Add legend
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 200px; height: 180px; 
            border:2px solid grey; z-index:9999; background-color:white;
            opacity:0.8;
            padding: 10px;
            font-size: 14px;
            ">
            <p><b>Legend</b></p>
            <p><span style="color:green;">■</span> Low Load (<50%)</p>
            <p><span style="color:orange;">■</span> Medium Load (50-80%)</p>
            <p><span style="color:red;">■</span> High Load (>80%)</p>
            <p><span style="color:blue;">●</span> Substations</p>
            <p><span style="color:orange;">●</span> Transformers</p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Save map with a different name to indicate 110kV filtering
m.save(os.path.join(data_dir, "power_grid_visualization_110kv.html"))
print("Power Flow Map Saved: 'power_grid_visualization_110kv.html' in data directory") 