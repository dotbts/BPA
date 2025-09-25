import requests
import geopandas as gpd
import pandas as pd
from tqdm import tqdm
import numpy as np
from shapely.ops import LineString, Point, Polygon
import math
import math
from shapely.geometry import box
import json

# see https://github.com/openaddresses/pyesridump
from esridump.dumper import EsriDumper

def bounding_box(latlon, distance_feet):
    """
    Create a bounding box around a lat/lon point with the given distance in feet.

    Parameters:
    lat (float): Latitude in degrees
    lon (float): Longitude in degrees
    distance_feet (float): Distance from the point in feet

    Returns:
    dict: Bounding box with min_lat, max_lat, min_lon, max_lon
    """
    # Constants
    feet_per_meter = 3.28084
    earth_radius_m = 6378137  # Earth radius in meters (WGS-84)

    # Convert distance from feet to meters
    distance_m = distance_feet / feet_per_meter

    # Latitude: 1 deg ≈ 111,320 meters
    delta_lat = (distance_m / 111320)

    # Longitude: 1 deg ≈ 111,320 * cos(latitude) meters
    delta_lon = distance_m / (111320 * math.cos(math.radians(latlon[0])))

    return {
        "ymin": latlon[0] - delta_lat,
        "ymax": latlon[0] + delta_lat,
        "xmin": latlon[1] - delta_lon,
        "xmax": latlon[1] + delta_lon
    }

def create_gdf_bbox(bbox):
    """
    For seeing the area you're downloading
    """
    bbox_geo = box(bbox['xmin'],bbox['ymin'],bbox['xmax'],bbox['ymax'])
    bbox_geo = gpd.GeoDataFrame({'geometry':bbox_geo},geometry='geometry',index=[0],crs='epsg:4326')
    return bbox_geo

def create_geom(row):
    """
    Creates a shapely geometry from an overpass output
    """
    is_area = False
    if (row['type'] == 'way'):
        # see if it's an area
        try:
            if row['tags.area'] == 'yes':
                is_area = True
        except:
            pass
        if is_area:     
            return Polygon([(x['lon'],x['lat']) for x in row.geometry])
        else:
            return LineString([(x['lon'],x['lat']) for x in row.geometry])
    elif (row['type'] == 'node'):
        return Point(row.lon,row.lat)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'} # This is chrome, you can set whatever browser you like

def download_feature_layer(api_endpoint):
    '''
    Downloads an esri feature layer and exports it as geojson file
    '''

    # get the feature layer name
    metadata = reference_fields(api_endpoint)

    # get the feature layer content
    d = EsriDumper(api_endpoint)
    all_features = list(d)

    new_geojson = {
        "type": "FeatureCollection",
        "features": all_features
    }

    with (Path.cwd() / f"data/{metadata.get('name')}.geojson").open('w') as fh:
        json.dump(new_geojson,fh,indent=4)

def reference_fields(api_endpoint):
    '''
    Gets metadata about the dataset from API enpoint
    '''
    params = {
        'f': 'json'
    }
    response = requests.get(api_endpoint,params=params,headers=headers)

    return response.json()

def get_attribute_metadata(api_endpoint):
    '''
    Gets all the field names from an ArcGIS REST feature layer
    '''
    
    params = {
        'f': 'json'
    }
    response = requests.get(api_endpoint,params=params,headers=headers)
    
    attributes = {}

    for x in response.json()['fields']:
        attributes[x.get('name')] = {
            'attribute_alias': x.get('alias'),
            'data_type': x.get('type'),
            'codedValues': parse_coded_values(x)
        }
    
    return attributes

def parse_coded_values(field_dict):
    '''
    Gets coded values for a field if not every possible value for a field is represented in the data
    '''    
    codedValues = access_key(field_dict,['domain','codedValues'])

    # if there is no coded values entry
    if isinstance(codedValues,list):
        if len(codedValues) > 0:
            codedValues = {x['code']:x['name'] for x in codedValues}
            return codedValues
    else:
        return None
    
def access_key(response_json,levels):
    # handles errors when accessing multiple levels of a large json
    response_json = response_json.copy()
    for level in levels:
        if isinstance(response_json,dict) == False:
            return None
        response_json = response_json.get(level)
    return response_json