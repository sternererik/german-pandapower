import folium
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon

# Load extracted GeoJSON files
power_lines = gpd.read_file("mecklenburg_power_lines.geojson")
substations = gpd.read_file("mecklenburg_substations.geojson")
transformers = gpd.read_file("mecklenburg_transformers.geojson")

# Create a folium map centered in Mecklenburg-Vorpommern
m = folium.Map(location=[53.6127, 12.4296], zoom_start=8)

# Add power lines with different colors based on voltage
for _, row in power_lines.iterrows():
    if row.geometry.geom_type == "LineString":
        # Get voltage and handle multiple voltage values
        voltage_str = row.get('voltage', '0')
        if voltage_str:
            # Take the highest voltage if multiple values exist
            voltages = [int(v) for v in str(voltage_str).split(';') if v.strip().isdigit()]
            voltage = max(voltages) if voltages else 0
        else:
            voltage = 0
        
        # Choose color based on voltage level
        if voltage >= 380000:
            color = 'red'  # 380kV lines
        elif voltage >= 220000:
            color = 'orange'  # 220kV lines
        elif voltage >= 110000:
            color = 'blue'  # 110kV lines
        else:
            color = 'gray'  # Unknown voltage
            
        # Create popup with line information
        popup_text = f"""
        Voltage: {voltage/1000}kV
        Operator: {row.get('operator', 'Unknown')}
        Name: {row.get('name', 'Unknown')}
        """
        
        folium.PolyLine(
            locations=[(lat, lon) for lon, lat in row.geometry.coords],
            color=color,
            weight=2,
            opacity=0.8,
            popup=popup_text
        ).add_to(m)

# Add substations as markers (red)
for _, row in substations.iterrows():
    # Get centroid for polygon geometries
    if isinstance(row.geometry, (Polygon, MultiPolygon)):
        centroid = row.geometry.centroid
        location = [centroid.y, centroid.x]
    else:
        location = [row.geometry.y, row.geometry.x]
        
    folium.CircleMarker(
        location=location,
        radius=5,
        color="red",
        fill=True,
        popup=f"Substation: {row.get('name', 'Unknown')}<br>Operator: {row.get('operator', 'Unknown')}",
    ).add_to(m)

# Add transformers as markers (yellow)
for _, row in transformers.iterrows():
    if isinstance(row.geometry, (Polygon, MultiPolygon)):
        centroid = row.geometry.centroid
        location = [centroid.y, centroid.x]
    else:
        location = [row.geometry.y, row.geometry.x]
        
    folium.CircleMarker(
        location=location,
        radius=3,
        color="orange",
        fill=True,
        popup=f"Transformer: {row.get('name', 'Unknown')}<br>Operator: {row.get('operator', 'Unknown')}",
    ).add_to(m)

# Add a legend
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 150px; height: 130px; 
            border:2px solid grey; z-index:9999; background-color:white;
            opacity:0.8;
            padding: 10px;
            font-size: 14px;
            ">
            <p><b>Legend</b></p>
            <p><span style="color:red;">■</span> 380kV Lines</p>
            <p><span style="color:orange;">■</span> 220kV Lines</p>
            <p><span style="color:blue;">■</span> 110kV Lines</p>
            <p><span style="color:gray;">■</span> Other Lines</p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Save map as an interactive HTML file
m.save("mecklenburg_power_grid.html")

print("Interactive map saved as 'mecklenburg_power_grid.html'. Open it in a browser!")

