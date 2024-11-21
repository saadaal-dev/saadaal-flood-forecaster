# Context
The goal of this script is to forecast the river level of the station Jowhar.

This forcasting method uses Linear Regression for its prediction. Using different data sources and mathematical approaches (more details below) we're able to create a model that predicts the river level on the following day.


# Data

The source data to train the model is based on the historical weather data (precipitation) in three different weather stations in Ethiopia, near tributaries of the Shebelle river, the historical weather on the Jowhar region, and the historical sensored data of the river level in Jowhar station.

## Rain data
The locations of the weather stations for the precipitation data are:
- Harar city - Fafen river source (East Ethiopia), merging into Shebelle river. (Latitude: 9.312932684554212, Longitude: 42.12141724519376)
- Gabredarre city (a.k.a. Kebri Dehar) - Fafen river midpoint (East Ethiopia), before merging. (Latitude: 6.855563401551738, Longitude: 44.267146985550426)
- Gode city - Shebelle before merging with Fafen. (Latitude: 5.956563275108595, Longitude: 43.55199121659339)

## River level data
# Training
The prerequisite is to have the libraries in the `requirements.txt` installed.
## Method
This model uses 2 main concepts to modelize the river level behavior:
- A PCA analysis: The goal is to detect the most important features and to reduce the feature cardinality.
- A linear regression: The goal is to approximate the river behavior with a linear function. This makes sense because the river behavior can be explained physically by taking into account the rain and river level.

It is important to note that this model can be enriched and fine tuned. However, it is usable as it is.
## Run
To run the training, please ensure you have the correct csv files in the `data` folder, place yourself at the same level as this README and run:
```bash
python3 model_training.py 
```
# Inference

The prerequisite is to have the libraries in the `requirements.txt` installed.
To run the inference, please ensure you filled the `inference_inputs.csv` fill with your inputs, place yourself at the same level as this README and run:
```bash
python3 model_inference.py
```