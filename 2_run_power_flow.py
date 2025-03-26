import pandapower as pp
import geopandas as gpd
import pandas as pd
import os
import time
from shapely.geometry import Point
from shapely.ops import nearest_points

# Define data directory
data_dir = os.path.join(os.path.dirname(__file__), 'data')

# Load power grid data
print("Loading power grid data...")
power_lines = gpd.read_file(os.path.join(data_dir, "mecklenburg_power_lines.geojson"))
substations = gpd.read_file(os.path.join(data_dir, "mecklenburg_substations_filtered.geojson"))

# Ensure data is in the correct coordinate system (WGS84)
substations = substations.to_crs("EPSG:4326")
power_lines = power_lines.to_crs("EPSG:4326")

print(f"Total substations: {len(substations)}")
print(f"Total power lines: {len(power_lines)}")

if len(power_lines) == 0:
    print("ERROR: No power lines found. Check your data files.")
    exit()

# Create an empty Pandapower network
print("🔹 Creating an empty Pandapower network...")
net = pp.create_empty_network()

# Find buses located in Lubmin
lubmin_buses = substations[substations["name"].str.contains("Lubmin", na=False, case=False)]

if lubmin_buses.empty:
    lubmin_buses = substations[
        substations.geometry.x.between(13.5, 13.8) & substations.geometry.y.between(54.0, 54.3)
    ]

print(f"Found {len(lubmin_buses)} buses in Lubmin.")

# Map Lubmin buses to their IDs in Pandapower
lubmin_bus_ids = []
for _, row in lubmin_buses.iterrows():
    bus_id = pp.create_bus(net, vn_kv=380, name=row.get("name", "Lubmin Substation"))
    lubmin_bus_ids.append(bus_id)
    
    # Add external grid (slack bus) to the first Lubmin bus
    if len(lubmin_bus_ids) == 1:
        pp.create_ext_grid(net, bus=bus_id, vm_pu=1.0, va_degree=0.0)
        print(f"Added external grid connection to bus {bus_id}")

print(f"Lubmin bus IDs: {lubmin_bus_ids}")

# Convert bus geometries to a list for nearest neighbor lookup
bus_mapping = {row.geometry: bus_id for row, bus_id in zip(lubmin_buses.itertuples(), lubmin_bus_ids)}
bus_points = list(bus_mapping.keys())

def find_nearest_bus(point):
    """Finds the nearest bus ID for a given point."""
    nearest = nearest_points(point, gpd.GeoSeries(bus_points).unary_union)[1]
    return bus_mapping.get(nearest, None)

# Filter power lines where at least one end is a Lubmin bus
lubmin_lines = []
for _, row in power_lines.iterrows():
    if row.geometry.geom_type == "LineString":
        coords = list(row.geometry.coords)
        from_bus = find_nearest_bus(Point(coords[0]))
        to_bus = find_nearest_bus(Point(coords[-1]))

        if from_bus in lubmin_bus_ids or to_bus in lubmin_bus_ids:
            pp.create_line(
                net, from_bus=from_bus, to_bus=to_bus,
                length_km=row.geometry.length / 1000, std_type="NAYY 4x50 SE"
            )
            lubmin_lines.append((from_bus, to_bus))

print(f"Added {len(lubmin_lines)} lines passing through Lubmin.")

# Ensure at least one load and one generator exist
if len(lubmin_bus_ids) > 1:
    print(f"Adding loads and generators to {len(lubmin_bus_ids)} Lubmin buses...")
    for bus in lubmin_bus_ids:
        pp.create_load(net, bus=bus, p_mw=5, q_mvar=2)  
        pp.create_sgen(net, bus=bus, p_mw=10, q_mvar=3)  

    print(f"{len(net.load)} loads and {len(net.sgen)} generators added.")

# Check if any buses are isolated
for bus in net.bus.index:
    connected = net.line[(net.line.from_bus == bus) | (net.line.to_bus == bus)]
    if connected.empty:
        print(f"Warning: Bus {bus} is not connected to any line.")

# Run Power Flow Simulation
print("Running power flow analysis for Lubmin network...")
try:
    pp.runpp(net, enforce_q_lims=True, init="flat", calculate_voltage_angles=True)
    print("Power flow analysis for Lubmin completed.")

    # Print key results
    print("\nBus Voltage Results:")
    print(net.res_bus.loc[lubmin_bus_ids])

    print("\nLine Loading Results:")
    print(net.res_line.loc[[i for i, j in lubmin_lines]])

    # Save results for visualization
    net.res_bus.to_csv(os.path.join(data_dir, "power_flow_lubmin_buses.csv"))
    net.res_line.to_csv(os.path.join(data_dir, "power_flow_lubmin_lines.csv"))

    print("Lubmin power flow results saved.")

except Exception as e:
    print(f"ERROR: Power flow simulation failed. {e}")
