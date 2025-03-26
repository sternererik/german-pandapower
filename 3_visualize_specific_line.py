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

# Filter out substations with no voltage information
substations = substations[substations['voltage'].notna()]
print(f"Antal substationer med spänningsvärde: {len(substations)}")

# Load power flow simulation results
power_flow = pd.read_csv(os.path.join(data_dir, "power_flow_lubmin_lines.csv"))

# Filter for specific power line with operator:wikidata = Q1273411
specific_line = power_lines[power_lines['operator:wikidata'] == 'Q1273411']
print(f"\nInformation om den specifika kraftledningen:")
print(f"Antal segment: {len(specific_line)}")
if not specific_line.empty:
    print("\nEgenskaper:")
    for col in specific_line.columns:
        if col != 'geometry':
            values = specific_line[col].unique()
            if len(values) > 0:
                print(f"{col}: {values[0]}")

# Convert to WGS84 (lat/lon) if needed
specific_line = specific_line.to_crs("EPSG:4326")
substations = substations.to_crs("EPSG:4326")

# Create a Folium map centered on the specific line
if not specific_line.empty:
    # Calculate the center of the line for map centering
    bounds = specific_line.total_bounds  # [minx, miny, maxx, maxy]
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create map centered on the line
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add the specific power line
    for idx, row in specific_line.iterrows():
        if row.geometry and row.geometry.geom_type == "LineString":
            # Get voltage
            voltage_str = str(row.get('voltage', '0'))
            voltages = [int(v) for v in voltage_str.split(';') if v.strip().isdigit()]
            voltage = max(voltages) if voltages else 0
            
            # Get power flow loading % (if available)
            try:
                line_loading = power_flow.iloc[idx]["loading_percent"]
            except IndexError:
                line_loading = 0
            
            # Create detailed popup with all available information
            popup_text = "<b>Kraftledningsinformation:</b><br>"
            for col in specific_line.columns:
                if col != 'geometry' and not pd.isna(row[col]):
                    popup_text += f"{col}: {row[col]}<br>"
            popup_text += f"Power Flow: {line_loading:.2f}%"
            
            # Add power line with popup
            folium.PolyLine(
                locations=[[lat, lon] for lon, lat in row.geometry.coords],
                color="red",
                weight=3,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
            
            # Add power flow label at midpoint
            mid_index = len(row.geometry.coords) // 2
            mid_point = row.geometry.coords[mid_index]
            
            folium.Marker(
                location=[mid_point[1], mid_point[0]],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 12pt; color: red; font-weight: bold;">{line_loading:.2f}%</div>'
                )
            ).add_to(m)
    
    # Add nearby substations (within 2km of the line)
    for _, substation in substations.iterrows():
        if substation.geometry.is_empty:
            continue
            
        # Check if substation is near the power line
        min_distance = float('inf')
        for _, line in specific_line.iterrows():
            distance = substation.geometry.distance(line.geometry)
            min_distance = min(min_distance, distance)
        
        # If substation is within 2km of the line, add it to the map
        if min_distance < 0.02:  # approximately 2km in degrees
            if isinstance(substation.geometry, (Polygon, MultiPolygon)):
                centroid = substation.geometry.centroid
                location = [centroid.y, centroid.x]
            else:
                location = [substation.geometry.y, substation.geometry.x]
            
            popup_text = "<b>Närliggande substation:</b><br>"
            for col in substation.index:
                if col != 'geometry' and not pd.isna(substation[col]):
                    popup_text += f"{col}: {substation[col]}<br>"
            
            folium.CircleMarker(
                location=location,
                radius=8,
                color="blue",
                fill=True,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: 90px; 
                border:2px solid grey; z-index:9999; background-color:white;
                opacity:0.8;
                padding: 10px;
                font-size: 14px;
                ">
                <p><b>Legend</b></p>
                <p><span style="color:red;">■</span> Specifik kraftledning</p>
                <p><span style="color:blue;">●</span> Närliggande substationer</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    output_file = os.path.join(data_dir, "specific_power_line_visualization.html")
    m.save(output_file)
    print(f"\n✅ Karta sparad som: 'specific_power_line_visualization.html'")
else:
    print("\n❌ Ingen kraftledning hittades med operator:wikidata = Q1273411") 