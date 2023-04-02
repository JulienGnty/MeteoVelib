from flask import Flask, jsonify, request, render_template
from flask_bootstrap import Bootstrap
import folium
from colour import Color
import pandas as pd
import numpy as np
import datetime as dt
import joblib
import json
import re
import random
import sys
from math import radians, sin, cos, sqrt, asin
import conf as cf
from glob import glob
from datasets import getStationsStatus, getStationsInfo


app = Flask(__name__, template_folder='app/templates')
bootstrap = Bootstrap(app)

# Variables :
with open(cf.DIRPATH + 'model/velib_model_list.json') as f:
    MODEL_INFO = json.load(f)
STATION_INFO = pd.read_json(cf.DIRPATH + 'data/download/stations_info.json').data[0]

LABELS = ["Class 0", "Class 1","Class 2","Class 3","Class 4"]


# Pour faire un dégradé de couleurs
# Dans cet exemple: 10 étapes pour passer du rouge au vert
def red(brightness):
    redc = Color("red")
    colors = list(redc.range_to(Color("green").hex,10))
    brightness = min([int(round(9 * brightness)),9]) # convert from 0.0-1.0 to 0-255
    return colors[brightness]


#Fonctions et variables nécessaires à la prédiction : 

def predict_occup(model, x_test):
    # On prédit sur les données de test
    y_pred = model.predict(x_test)
    y_pred = f"{y_pred[0]:3.1f}"
  
    return y_pred


def get_station_info(station_info: object, station_id: str):
    
    name, lat, lon, cap = 'station_not_found', 0, 0, 0
    for d in STATION_INFO:
        if d['station_id'] == station_id : 
            name, lat, lon, cap = d['name'], float(d['lon']), float(d['lat']) , int(d['capacity'])       
    
    return name, lat, lon, cap


# lat=48.856614, lon=2.3522219
def get_iframe_current_occup(lat = 48.856614, lon = 2.3522219, zoom = 12, time_str = ""):
    """
        Create a map as an iframe to embed on a page.
    """
    today = dt.datetime.now()
    year = str(today.year)
    month = str(today.month).zfill(2)
    day = str(today.day).zfill(2)
    list_files = glob(cf.DIRPATH + "data/download/stations_status_" + year + "_" + month + "_" + day + "_*.json")

    df = getStationsStatus(list_files[-1])

    df = df.merge(getStationsInfo(), on = "station_id")
    
    m = folium.Map(location = [lat, lon], zoom_start = zoom )

    # set the iframe width and height
    m.get_root().width = "800px"
    m.get_root().height = "600px"

    for _, row in df.iterrows():
        if row["capacity"]:
            occupation  = row["num_bikes_available"] / row["capacity"]
            if occupation > 1:
                occupation = 1.0
        else:
            occupation = 0.0
        
        folium.CircleMarker(
            location = [row['lat'], row['lon']],
            color = "#000000",
            weight = 2,
            fill_color = red(occupation).hex,            
            # fill_color = red(abs(y_test)).hex,            
            #fill_color = "#000000",
            fill_opacity = 1.0,
            # popup = str(v.y_test) + " % ",
            popup = "Station n°" + str(row['stationCode']) + "\n"+str(row['name']),
            radius = 2 + 3 * (row["capacity"] / 74),
        ).add_to(m)

    iframe = m.get_root()._repr_html_()

    return iframe


# lat=48.856614, lon=2.3522219
def get_iframe_predicted(close_stations, lat = 48.856614, lon = 2.3522219, zoom = 12, time_str = ""):
    """
        Create a map as an iframe to embed on a page.
    """
    m = folium.Map(location = [lat, lon], zoom_start = zoom )

    # set the iframe width and height
    m.get_root().width = "800px"
    m.get_root().height = "600px"

    test = True
    for v in STATION_INFO:
        if v["station_id"] in close_stations.keys():
            occupation = close_stations[v["station_id"]][-2]/close_stations[v["station_id"]][-1]
            folium.CircleMarker(
                location = [v['lat'], v['lon']],
                color = "#000000",
                weight = 2,
                fill_color = red(occupation).hex,            
                fill_opacity = 1.0,
                popup = "Station n°" + str(v['stationCode']) + "\n"+str(v['name']),
                radius = 2 * (3 + 2 * (v["capacity"] / 74)),
            ).add_to(m)
        else:
            folium.CircleMarker(
                location = [v['lat'], v['lon']],
                color = "#000000",
                weight = 2,
                fill_color = "#000000",
                fill_opacity = 0.3,
                popup = "Station n°" + str(v['stationCode']) + "\n"+str(v['name']),
                radius = 4 + 1 * (v["capacity"] / 74),
            ).add_to(m)

    #Marker for the user's position
    folium.CircleMarker(
        location = [lat, lon],
        color = "#3333CC",
        weight = 2,
        fill_color = "#3333CC",
        fill_opacity = 1.0,
        popup = "User",
        radius = 5
    ).add_to(m)

    iframe = m.get_root()._repr_html_()

    return iframe


#Compute the distance in km between two points knowing their latitudes and
# longitudes (cf wikipedia haversine formula)
def distance(lon1 :float, lat1 :float, lon2 :float, lat2 :float):
    # approximate radius of earth in km
    R = 6373.0

    # convert latitudes and longitudes from degrees to radians
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    # apply the Haversine formula to calculate the distance
    h = sin((lat2-lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1) / 2)**2
    distance = 2*R*asin(sqrt( h ))
    
    return distance


#Selects the nmax stations closest to the position (lat,lon)
def get_station_close(lat :float, lon :float, nmax = 5 ):
    dict_distance={}
    for station in STATION_INFO:
        dict_distance[station['station_id']] = distance(station['lon'], station['lat'], lon, lat)

    key_list = []
    for k, v in sorted(dict_distance.items(), key=lambda item: item[1])[:nmax] :
        key_list.append(k)


    selected_station = []
    for station in STATION_INFO:
        if station['station_id'] in key_list:
            station['distance']=dict_distance[station['station_id']]
            selected_station.append(station)
        
    
    return selected_station


def get_table_line(station, time_str , ret_classif = 0):     
   
    station_int = station['station_id']
    lon = station['lon']
    lat = station['lat']

    # 'time_str' is returned by the html page in the format "2023-03-23T12:00")
    year = int(time_str[:4])
    month = int(time_str[5:7])
    day = int(time_str[8:10])
    hour = int(time_str[11:13])
    minute = int(time_str[14:16])

    weekday = dt.datetime(year, month, day, hour, minute).weekday()

    # TODO: GET FORECAST WEATHER
    # DEFAULT: Get Weather of the 28th March
    with open(cf.DIRPATH + "data/download/weather_2023_03_28_" + str(hour) + ".json") as f_weather:
        data = json.load(f_weather)
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

    # TODO: GET FORECAST STRIKES AND DEMONSTRATIONS
    # DEFAULT: to 0
    strike = 0
    demonstration = 0

    x_data = pd.DataFrame([
        [temperature, humidity, wind_speed, strike, demonstration, weekday, year, month, day, hour, minute]
        ],
        columns = ["temperature", "humidity", "wind_speed", "strike", "demonstration",
                   "weekday", "year", "month", "day", "hour", "minute"]
    )

    # Check if this station has a model
    if not MODEL_INFO[str(station_int)]:
        return (station['name'], station['stationCode'], station['distance'] * 1000, 0, 0)
        
    model_name = 'velib_model_' + str(station['station_id']) + '.joblib.z'
    model = joblib.load(cf.DIRPATH + "model/" + model_name) 
    #model = model_dict[station_int]

    #Predict the occupation percentage
    classif = predict_occup(model, x_data)

    # TODO: Delete
    if ret_classif :
        return classif


    name = station['name']
    station_code = station['stationCode']
    distance = station['distance'] * 1000
    capacity = station['capacity']
    n_avail_bikes = float(classif) * capacity / 100.

    table_line = (name, station_code, f"{int(distance)} m.", int(np.round(n_avail_bikes)), capacity)
    return table_line


@app.route('/')
def hello():
    lat_u = random.uniform(48.8,48.9)
    lon_u = random.uniform(2.3,2.4)
    iframe = get_iframe_current_occup()
    return render_template('index.html', lat = round(lat_u, 5), lon = round(lon_u, 5), iframe = iframe)


@app.route('/predict', methods=['GET','POST'])
def predict():
    if request.method == 'POST':
        # On récupère le champ namequery du template index
        # format : text="2023-03-23T12:00"
        time_str = request.form['timequery']   
        if time_str == '':
            time_str = "2023-03-23T12:00"            
            
        # On n'utilisera pas une station_id en entrée mais une position de
        # l'utilisateur à base de latitude/longitude
        lat_u = float(request.form['lat_inp'])
        lon_u = float(request.form['lon_inp'])
        selected_station = get_station_close(lat_u, lon_u)

        # We generate the list "my_list" that is used to create the tables in
        # the html by looping on each selected station
        my_list = []
        my_dict = {}
        for station in selected_station :
            row = get_table_line(station, time_str)
            my_list.append(row)
            my_dict[station["station_id"]] = row

        iframe = get_iframe_predicted(my_dict, lat_u, lon_u, 16, time_str)
        
        # Render the response in the result.html template
        return render_template('predict.html', my_list = my_list, hour1 = time_str[11:16], iframe = iframe, lat = round(lat_u, 5), lon = round(lon_u, 5))
                               
    #This is called by the reset button on index.html. Used for tests.
    elif request.method == 'GET':
        return render_template('index.html')

    # TODO: Remove ?
    elif request.method == 'PUT':
        # Retrieve parameters from the request body
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        time_str = request.args.get('time_str')
    
        if not lat or not lon or not time_str:
            # Return an error response if any parameter is missing
            return jsonify(error='Missing required parameter'), 400
    
        # We generate the list "my_list" that is used to create the tables in
        # the html by looping on each selected station
        selected_station = get_station_close(float(lat), float(lon))
        my_list = []
        for station in selected_station :
            my_list.append(get_table_line(station, time_str))
    
        iframe=get_iframe(float(lat), float(lon), 16, time_str)
    
        # Render the response in the result.html template
        return render_template('predict.html', my_list = my_list, hour1 = time_str[11:16], iframe = iframe)                               

    else :
        return render_template('index.html')


# Lancement de l'application Flask
if __name__ == '__main__':
    app.run(debug = True, port = 5000)
    
    
