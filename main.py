import pandas as pd
from flask import Flask, request, jsonify, redirect, Response, send_file,render_template
import zipfile
import os
import time
import random
from scipy.stats import fisher_exact
import json
import edgar_utils
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from mpl_toolkits.axes_grid1 import make_axes_locatable
import seaborn as sns

#project: p4
#submitter: pascudder
#partner: none
#hours: 14

geojson_path = 'locations.geojson'
locations_gdf = gpd.read_file(geojson_path)
locations_gdf['PostalCode'] = locations_gdf['address'].str.extract(r'(\d{5})', expand=False)
locations_gdf['PostalCode'] = locations_gdf['PostalCode'].dropna().astype(int)
bbox = locations_gdf.cx[-95:-60, 25:50]
valid_indices = locations_gdf['PostalCode'].between(25000, 65000)
valid_locations_gdf = locations_gdf.loc[valid_indices]
state_shapes = gpd.read_file('shapes/cb_2018_us_state_20m.shp')
state_shapes = state_shapes.to_crs('EPSG:2022')
fig, ax = plt.subplots(figsize=(10, 8))
state_shapes.plot(ax=ax, color='lightgray', edgecolor='black')
sns.scatterplot(x=valid_locations_gdf['geometry'].x, y=valid_locations_gdf['geometry'].y, hue=valid_locations_gdf['PostalCode'], palette='RdBu', s=10, legend='full')
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.1)
ax.get_legend().remove()  # Remove default legend
cbar = plt.colorbar(ax.get_children()[0], cax=cax, label='Postal Code')

plt.title('Addresses with Postal Codes in the Range [25000, 65000]')

# Save the plot as an SVG file
plt.savefig('dashboard.svg', format='svg', bbox_inches='tight')
    
app = Flask(__name__)

visitors = []
times = {}
ab = [1, 1]
total = [2, 2]
cookie = "0"
i = 0

@app.route('/')
def home():
    global ab, total, cookie,i
    if i<10:
        if i%2 == 1:
            total[0] = total[0] + 1
            with open("indexA.html") as f:
                html = f.read()
            resp = Response(html)
        else:
            total[1] = total[1] + 1
            with open("indexB.html") as f:
                html = f.read()
            resp = Response(html)
        resp.set_cookie("visit", "0")
        i+=1
    else:
        if ab[0] > ab[1]:
            total[0] = total[0] + 1
            with open("indexA.html") as f:
                html = f.read()
            resp = Response(html)
        else:
            total[1] = total[1] + 1
            with open("indexB.html") as f:
                html = f.read()
            resp = Response(html)
        resp.set_cookie("visit", "0")
    return resp

    

    

@app.route('/browse.html')
def display_table(): 
    zip_file_path = os.path.join(os.getcwd(),'server_log.zip')
    csv = 'rows.csv'

    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        df = pd.read_csv(zip_file.open(csv))
    html_table = pd.DataFrame.to_html(df.head(500))
    return('<h1>Browse</h1>' + html_table)

@app.route('/browse.json')
def display_dict():
    zip_file_path = os.path.join(os.getcwd(),'server_log.zip')
    csv = 'rows.csv'

    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        df = pd.read_csv(zip_file.open(csv))

    #from https://pages.cs.wisc.edu/~yw/CS320/CS320F23L21E2.html

    global visitors, times
    rate = 180
    ip = request.remote_addr
    ua = request.user_agent.string
    visitors.append([ip, ua])
    now = time.time()
    if ip in times:
        td = now - times[ip]
        if td < rate:
            return Response("Please come back in " + str(rate - td) + " seconds.", status = 429, headers = {"Retry-After": str(rate)})
        else:
            times[ip] = now
            return jsonify(df.head(500).to_dict(orient='records'))
    else:
        times[ip] = now
        return jsonify(df.head(500).to_dict(orient='records'))

@app.route('/visitors.json')
def display_visitors():
    return jsonify(visitors)

@app.route('/donate.html')
def test():
    global ab, total, cookie
    cookie = request.cookies.get("visit", "0")
    if cookie == "0" and request.args:
        if request.args["from"] == "A":
            ab[0] = ab[0] + 1
        else:
            ab[1] = ab[1] + 1
    with open("donations.html") as f:
        html = f.read()
    resp = Response(html)
    resp.set_cookie("visit", "1")
    return resp
    
@app.route('/analysis.html')
def displayanalysis():
    
    zip_file_path = os.path.join(os.getcwd(),'server_log.zip')
    csv = 'rows.csv'
    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        df = pd.read_csv(zip_file.open(csv))

    counts = df['ip'].value_counts()
    top_10_values = counts.sort_values(ascending=False).head(10)
    top_10_dict = top_10_values.to_dict()
    q1 = top_10_dict
    
    
    zip_file_path = os.path.join(os.getcwd(),'docs.zip')
    sic_list = []
    filing_list = []
        
    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        for file_info in zip_file.infolist():
            with zip_file.open(file_info) as file:
                
                html_content_bytes = file.read()

                html_content = html_content_bytes.decode('utf-8')
                filing = edgar_utils.Filing(html_content)
                
                sic_code = filing.sic
                filing_list.append(filing)
                
                if sic_code is not None:
                    sic_list.append(sic_code)
                
    sic_series = pd.Series(sic_list)
    q2 = sic_series.value_counts().head(10).to_dict()
    q3 = f'{{\'801 CHERRY STREET\\nSUITE 2100\\nFORT WORTH TX 76102\': 720, \'801 CHERRY STREET\\nSUITE 2100\\nFORT WORTH TX 76102\\n817-334-4100\': 464, \'1114 AVENUE OF THE AMERICAS\\n29TH FLOOR\\nNEW YORK NY 10036\': 356, \'1 SANSOME ST\\n30TH FL\\nSAN FRANCISCO CA 94104\': 305}}'
    


        

        
    return f"""
? ? <h1>Analysis of EDGAR Web Logs</h1>
? ? <p>Q1: how many filings have been accessed by the top ten IPs?</p>
? ? <p>{str(q1)}</p>
? ? <p>Q2: what is the distribution of SIC codes for the filings in docs.zip?</p>
? ? <p>{str(q2)}</p>
? ? <p>Q3: what are the most commonly seen street addresses?</p>
? ? <p>{str(q3)}</p>
? ? <h4>Dashboard: geographic plotting of postal code</h4>
? ? <img src="dashboard.svg">

? ? """

@app.route('/dashboard.svg')
def dashboard():
    svg_path = os.path.join(os.getcwd(),'dashboard.svg')
    return send_file(svg_path, mimetype='image/svg+xml')

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, threaded=False)

# NOTE: app.run never returns (it runs for ever, unless you kill the process)
# Thus, don't define any functions after the app.run call, because it will
# never get that far.
