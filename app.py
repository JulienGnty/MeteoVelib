
from flask import Flask, jsonify, request, render_template

# from flask import  redirect, flash

import joblib
from flask_bootstrap import Bootstrap

import pandas
import pandas as pd
import sklearn

import re
import numpy as np
import conf as cf
import json


app = Flask(__name__, template_folder='app/templates')
bootstrap=Bootstrap(app)

#Variables :
f = open(cf.DIRPATH + 'model/velib_model_list.json')
MODEL_INFO = json.load(f)
STATION_INFO = pd.read_json(cf.DIRPATH + 'data/download/stations_info.json').data[0]

LABELS = ["Class 0", "Class 1","Class 2","Class 3","Class 4"]


#Fonctions et variables nécessaires à la prédiction : 

def predict_occup(model, x_test):

    # On prédit sur les données de test
    y_pred = model.predict(x_test)
    y_pred=f"{y_pred[0]:3.1f}"
  
    return y_pred


def format_predict_input(station_id: int, lat: float, lon: float, time_str: str):
    #Combines the results from various sources to format the features used for
    # the prediction in a way compatible with the prediction model.
    
    
    # 'time_str' is returned by the html page in the format "2023-03-23T12:00")
    year = int(time_str[:4])
    month = int(time_str[5:7])
    day = int(time_str[8:10])
    hour = int(time_str[11:13])
    minute = int(time_str[14:16])

    x_test=pd.DataFrame([[station_id, lon, lat, year, month, day, hour, minute]], 
                        columns=['station_id', 'lon' ,'lat', 'year', 'month', 'day', 'hour', 'minute'])
    
    return x_test


def get_station_info(station_info: object, station_id: str):
    
    name, lat, lon = 'station_not_found', 0, 0
    for d in STATION_INFO:
        if d['station_id'] == station_id : 
            name, lat, lon = d['name'], float(d['lon']), float(d['lat'])        
    
    return name, lat, lon






@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/predict', methods=['GET','POST'])
def predict():
    if request.method == 'POST':

#
        station_int = MODEL_INFO[1]["station_id"]
        station_id = str(station_int)
        
        name, lat, lon = get_station_info(STATION_INFO, station_int)        
        
        #Rajouter une version dans le fichier du modèle, peut-être? Certaines fonctions
        # (format_predict_input) sont écrites pour un ensemble de features spécifique.
        model_name = 'velib_model_'+station_id+'.joblib.z'
        model = joblib.load(cf.DIRPATH + "model/" + model_name)       

        # On récupère le champ namequery du template index
        # format : text="2023-03-23T12:00"
        time_str = request.form['namequery']
        if time_str == '':
            time_str = "2023-03-23T12:00"
            
            # flash('Please enter some input.')
            # return redirect(request.url)
            
        x_test=format_predict_input(station_id, lat, lon, time_str)
        classif=predict_occup(model,x_test)
        
        my_list=[(name, station_id, str(0), classif, "", ""),
                 (name, station_id, str(0), classif, "", ""),
                 (name, station_id, str(0), classif, "", "")]
        
        # Render the response in the result.html template
        return render_template('index.html', my_list=my_list)
                               


    #This is called by the reset button on index.html. Used for tests.
    elif request.method == 'GET':
        return render_template('index.html')


    else :
        return render_template('index.html')




# Lancement de l'application Flask
if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
    
