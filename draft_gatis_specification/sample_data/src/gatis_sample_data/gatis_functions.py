import pandas as pd
import geopandas as gpd

def geojson_to_geopandas(geojson,feature_type=None,subfeature_type=None):
    """
    Converts GATIS template geojson to a geopandas dataframe. Optionally, specify the
    feature type and subfeature type to only return one feature type
    """
    
    # convert to pandas dataframe
    records = []
        
    # raise exception if feature_type or subfeature_type are not defined
    if feature_type is not None:
        accepted_feature_types = ["edge","node","point","zone"]
        if feature_type not in accepted_feature_types:
            raise Exception(f"feature type is not one of {accepted_feature_types}")
    if subfeature_type is not None:
        accepted_subfeature_types = [x['properties'][f'{feature_type}_type'] for x in geojson['features']]
        if subfeature_type not in accepted_subfeature_types:
            raise Exception(f"subfeature type is not one of {accepted_subfeature_types}")

    for record in geojson['features']:
        record = record['properties']
        if (feature_type is not None) & (subfeature_type is not None):
            if record[f"{feature_type}_type"] is not None:
                if record[f"{feature_type}_type"] != subfeature_type:
                    continue
        record['geometry'] = None
        records.append(record)
    gdf = pd.DataFrame.from_records(records)

    # replace all NaN with None
    return gdf

def create_empty_gdf_like(empty_df_with_cols,gdf_to_mimic):
    """
    Helper function that copies the index and number of rows of the dataset you're trying to convert
    to GATIS
    """
    return gpd.GeoDataFrame([empty_df_with_cols.values[0] for x in range(0,gdf_to_mimic.shape[0])],geometry=gdf_to_mimic.geometry,columns=empty_df_with_cols.columns,index=gdf_to_mimic.index)