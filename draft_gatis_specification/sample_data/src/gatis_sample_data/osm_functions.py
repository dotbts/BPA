import osmnx as ox
import requests
import pandas as pd
from pathlib import Path
import json
import geopandas as gpd
from tqdm import tqdm
import sys
import traceback

from gatis_sample_data import utils, osm_functions

ox.settings.all_oneway = True
def download_osmnx(xmin,ymin,xmax,ymax):
    """
    Gets the geometry info and processes it into routable network graph format
    """

    #retrieve graph from bbox
    G = ox.graph_from_bbox((xmin, ymin, xmax, ymax), network_type="all_public", retain_all=True, simplify=False)
 
    #simplify graph unless different osm ids
    G = ox.simplification.simplify_graph(G,edge_attrs_differ=["osmid"])
    
    #remove directed edges (edges for each direction)
    # G = ox.convert.to_undirected(G)
    
    #get edge bearing
    # G = ox.bearing.add_edge_bearings(G)

    #plot it for fun
    # ox.plot_graph(G)

    #convert to gdf
    nodes, edges = ox.convert.graph_to_gdfs(G)

    #reset index
    edges = edges.reset_index()
    
    #simplify columns to geo and id
    edges = edges[['osmid','geometry']]
    edges.columns = ['id','geometry']

    #reset nodes index
    nodes = nodes.reset_index()
    nodes = nodes[['osmid','geometry']]
    nodes.columns = ['id','geometry']

    return nodes, edges


def overpass_download(xmin,ymin,xmax,ymax):
    def query(feature_type):    
      query = f"""
      [out:json]
      [timeout:120]
      ;
      {feature_type}
      ["highway"]
      ({ymin},{xmin},{ymax},{xmax});
      out geom;
      """
      return query
    
    url = "http://overpass-api.de/api/interpreter"
    r = requests.get(url, params={'data': query("node")})
    nodes = r.json()
    r = requests.get(url, params={'data': query("way")})
    edges = r.json()
    
    #simplify for dataframe
    nodes = process_overpass_response(nodes)
    edges = process_overpass_response(edges)
    
    return nodes, edges

def overpass_nodes(xmin,ymin,xmax,ymax):
    '''
    Retrieves all nodes with at least one tag in the bounding box
    '''

    query = f"""
    [out:json]
    [timeout:120]
    ;
    node
        ({ymin},{xmin},{ymax},{xmax})
        (if:count_tags()>0);
    out geom;
    """
    
    url = "http://overpass-api.de/api/interpreter"
    r = requests.get(url, params={'data': query})

    if r.status_code != 200:
        raise Exception(r.text)

    nodes = r.json()
    
    nodes = process_overpass_response(nodes)

    return nodes

def process_overpass_response(overpass_response):
    records = []
    for record in overpass_response['elements']:
        tags = {"tags."+key:item for key,item in record.get('tags').items()}
        record.pop('tags')
        records.append(
            {
                **record,
                **tags
            }
        )
    return pd.DataFrame.from_records(records)

def download_osm_from_bbox(bbox_center_lonlat,bbox_length_ft):
    '''
    This function downloads OSM data using a bounding box.

    The first argument takes a latitude and longitude as a list:
    [lon,lat]

    Then the second argument takes a number that is the length of
    the side of the bounding box. Currently bounding boxes are square.
    '''

    print(f"Retrieving OSM data...")
 
    try:
        # create the bounding box dimensions
        bbox = utils.bounding_box(bbox_center_lonlat,bbox_length_ft)

        # get data from overpass and osmnx
        # only looks at ways and nodes with highway=*
        _, edges_attr = overpass_download(**bbox)
        overpass_geo = edges_attr.apply(lambda row: utils.create_geom(row), axis=1)
        edges_attr['geometry'] = gpd.GeoSeries(overpass_geo,crs="epsg:4326")
        _, edges = osm_functions.download_osmnx(**bbox)

        # get osm nodes with at least one tag regardless of what it is
        # gets curbs, traffic signals, crossings, etc.
        nodes_attr = overpass_nodes(**bbox)
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

        return edges, nodes_attr, zones

    except:    
        print(f"Error retrieving OSM data")
        exception_type, exception_value, trace = sys.exc_info()
        print(f"Exception Type: {exception_type.__name__}")
        print(f"Exception Value: {exception_value}")
        trace_string = "".join(traceback.format_tb(trace))
        print(f"Traceback:\n{trace_string}")