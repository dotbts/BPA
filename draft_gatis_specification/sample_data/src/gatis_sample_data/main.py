from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
import sys
import traceback

from gatis_sample_data import osm_functions, utils

if __name__ == '__main__':
    # read the data
    with (Path.cwd()/"bounding_boxes.json").open('rb') as fh:
        locations = json.load(fh)

    # create sample data filepath
    if (Path.cwd()/'sample_data_raw').is_dir() == False:
        (Path.cwd()/'sample_data_raw').mkdir()
    else:
        user_input = input(f"Do you want to overwrite the existing data? (enter 'n' if no else type anything else)")

    for record in locations:
        # create file name
        file_dir = Path.cwd()/f"sample_data_raw/{record['bbox_name']}"
        if file_dir.is_dir() == False:
            file_dir.mkdir()
        if (file_dir/"edges.geojson").exists() & (file_dir/"nodes.geojson").exists() & (user_input == "n"):
            continue
            
        print(f"Retrieving OSM data for {record['bbox_name']}")

        try: 
            # create the bounding box dimensions
            bbox = utils.bounding_box(record['latlon'],record['bbox_length_ft'])

            # get data from overpass and osmnx
            # only looks at ways and nodes with highway=*
            _, edges_attr = utils.overpass_download(**bbox)
            overpass_geo = edges_attr.apply(lambda row: utils.create_geom(row), axis=1)
            edges_attr['geometry'] = gpd.GeoSeries(overpass_geo,crs="epsg:4326")
            _, edges = osm_functions.download_osmnx(**bbox)

            # get osm nodes with at least one tag regardless of what it is
            # gets curbs, traffic signals, crossings, etc.
            nodes_attr = utils.overpass_nodes(**bbox)
            nodes_attr['geometry'] = nodes_attr.apply(lambda row: utils.create_geom(row),axis=1)
            nodes_attr = gpd.GeoDataFrame(nodes_attr,geometry='geometry',crs="epsg:4326")

            # merge the two
            # nodes = pd.merge(nodes,nodes_attr,on='id')
            edges = pd.merge(edges,edges_attr,on='id',how='outer')

            # combine geometry
            edges['geometry'] = edges['geometry_x'].fillna(edges['geometry_y'])
            edges.drop(columns=['geometry_x','geometry_y'],inplace=True)
            edges.set_geometry('geometry',inplace=True)

            # create zones layer
            zones = edges[edges.geometry.geom_type == 'Polygon']
            edges = edges[edges.geometry.geom_type == 'LineString']

            # save as geojson
            # with (file_dir/"nodes.geojson").open('w') as f:
            #     f.write(nodes.to_json(na="drop",indent=4))
            with (file_dir/"edges.geojson").open('w') as f:
                f.write(edges.to_json(na="drop",indent=4))
            with (file_dir/"zones.geojson").open('w') as f:
                f.write(zones.to_json(na="drop",indent=4))
            with (file_dir/"nodes_attr.geojson").open('w') as f:
                f.write(nodes_attr.to_json(na="drop",indent=4))
        except:
            
            print(f"Error retrieving {record['bbox_name']}")
            exception_type, exception_value, trace = sys.exc_info()
            print(f"Exception Type: {exception_type.__name__}")
            print(f"Exception Value: {exception_value}")
            trace_string = "".join(traceback.format_tb(trace))
            print(f"Traceback:\n{trace_string}")
            continue