HOW TO RUN THE PROGRAM:

1. Use conda to create a new environment:
   ```bash
   conda create -n gis python=3.10
   conda activate gis
   ```

2. Install required packages:
   ```bash          
   pip install -r requirements.txt
   ```

3. Run the scripts in the following order:
   ```bash
   python scripts/1_extract_osm_data.py
   python scripts/2_extract_buildings.py
   python scripts/3_visualize_power_flow.py
   ```  

4. Open the file `index.html` in your web browser to see the results.    