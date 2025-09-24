import requests
import pandas as pd
from tqdm import tqdm
import numpy as np
import datetime
import sys
import pickle
from collections import defaultdict

from attribute_scraper import misc

### Main Functions ###

def arcgis_scrape(api_endpoint):
    '''
    With a given ArcGIS REST API Endpoint, this function
    gets metadata about the feature layer and the attributes.

    Minimal cleaning operations are performed in this step. Those
    should be completed in a seperate step after backing up the response data.
    '''

    # TODO scrape entity name or put in the domain name
    # allow manual results to override this
    # get orgid from api endpoint
    # only valid if the domain is services.arcgis.com or services{number}.arcgis.com
    # then get "name"
    # otherwise grab the domain
    # NqY8dnPSEdMJhuRw
    # https://arcgis.com/sharing/rest/portals/{org_id}?f=pjson
    # https://arcgis.com/sharing/rest/portals/NqY8dnPSEdMJhuRw?f=pjson

    # get reference metadata
    references = reference_fields(api_endpoint)

    # get the bounding box
    bbox = get_bbox(api_endpoint)
    if bbox is not None:
        references |= {'bbox': bbox}

    # create attribute metadata
    attributes = get_attribute_metadata(api_endpoint)
    
    # get statistics for numeric fields
    if references['supportsStatistics']:
        #NOTE: is this comprehensive?
        esri_numeric_dtypes = [
        'esriFieldTypeInteger',
        'esriFieldTypeDouble',
        'esriFieldTypeSmallInteger',
        'esriFieldTypeBigInteger',
        'esriFieldTypeShort',
        'esriFieldTypeLong',
        'esriFieldTypeSingle'
        ]

        numeric_fields = [key for key, item in attributes.items() if item['data_type'] in esri_numeric_dtypes]
        if len(numeric_fields) > 0:
            stats = {numeric_field:get_stats(api_endpoint,numeric_field) for numeric_field in numeric_fields}
            if stats is not None:
                attributes = {
                    key: {
                        **item, **stats.get(key)
                        } if stats.get(key) is not None else item for key, item in attributes.items()
                    }
                
        # get non null counts
        non_null = {key:get_stats(api_endpoint,key,stat_ops=['count']) for key in attributes.keys()}
        if non_null is not None:
            attributes = {
                key: {
                    **item,'non_null_count':non_null.get(key).get('count')
                    } if non_null.get(key) is not None else item for key, item in attributes.items()
                }

    # get unique val counts
    if references['supportsCountDistinct']:
        unique_counts = {key:get_unique_count(api_endpoint,key) for key in attributes.keys()}
        if unique_counts is not None:
            attributes = {
                key: {
                    **item, 'unique_count':unique_counts.get(key)
                } if unique_counts.get(key) is not None else item for key, item in attributes.items()
            }

        # get unique values
        if references['supportsDistinct']:
            threshold = 20 # number of unique values to retrieve
            unique_vals = {key:get_unique_values(api_endpoint,key,threshold) for key in attributes.keys()}
            if unique_vals is not None:
                attributes = {
                    key: {
                        **item, 'unique_values':unique_vals.get(key)
                    } if unique_vals.get(key) is not None else item for key, item in attributes.items()
                }

    # reformat attributes into records
    attributes = [{"attribute_id":key,**item} for key, item in attributes.items()]

    return references, attributes

def arcgis_process_results(result):
    '''
    Processes arcgis scraped data into schema
    '''

    response = result.get('response')
    if response is None:
        raise f"No scraped data found for {result.get("dataset_id")}"

    #TODO could simplify code by making a function that checks if thing exists in response
    # if it does then it runs the correct function

    # don't require any special processing
    references = {}
    keys = ["column_count","row_count","bbox"]
    for key in keys:
        # if response[0].get(key) is not None:
        references[key] = response[0].get(key)
    
    references['description'] = process_description(response[0])
    references['last_updated'] = process_last_updated(response[0])
    
    attributes = []
    keys = ['attribute_id','attribute_alias','data_type','unique_count','min','max','avg','sum']
    for response_record in response[1]:
        record = {}
        for key in keys:
            record[key] = response_record.get(key)
        
        record['null_percent'] = process_null_count(response_record,references.get('row_count'))
        record['unique_values'] = process_unique_vals(response_record)
        attributes.append(record)

    # update the dictionary (don't need to export)
    result['processed_response'] = (references,attributes)

#### API Request Functions ####

def get_attribute_metadata(api_endpoint):
    '''
    Gets all the field names from an ArcGIS REST feature layer
    '''
    
    params = {
        'f': 'json'
    }
    response = requests.get(api_endpoint,params=params,headers=misc.headers)
    
    # return response error
    if response.status_code != 200:
        misc.log_error(api_endpoint, 'get_unique_values', response)
        return
    
    # sometimes esri will return a 200 status code but the json will have an error
    if response.json().get('error') is not None:
        misc.log_error(api_endpoint, 'get_unique_values', response)
        return
    
    attributes = {}

    for x in response.json()['fields']:
        attributes[x.get('name')] = {
            'attribute_alias': x.get('alias'),
            'data_type': x.get('type'),
            'codedValues': parse_coded_values(x)
        }
    
    return attributes

def reference_fields(api_endpoint):
    '''
    Gets metadata about the dataset from API enpoint
    '''
    reference_fields_dict = {}
    params = {
        'f': 'json'
    }
    response = requests.get(api_endpoint,params=params,headers=misc.headers)
    record_count_response = get_record_count(api_endpoint)
    
    if record_count_response.status_code != 200:
        misc.log_error(api_endpoint, 'get_unique_values', record_count_response)
        return

    response_json = response.json()
    reference_fields_dict.update({
        'dataset_name': access_key(response_json,['name']),
        'description': access_key(response_json,['description']),
        'last_updated': [
            get_dates(access_key(response_json,['editingInfo','lastEditDate'])),
            get_dates(access_key(response_json,['editingInfo','schemaLastEditDate'])),
            get_dates(access_key(response_json,['editingInfo','dataLastEditDate']))
        ],
        'row_count': access_key(record_count_response.json(),['count']),
        'column_count': len(access_key(response_json,['fields'])),
        'supportsStatistics': access_key(response_json,['supportsStatistics']),
        'supportsCountDistinct': access_key(response_json,['advancedQueryCapabilities','supportsCountDistinct']),
        'supportsDistinct': access_key(response_json,['advancedQueryCapabilities','supportsDistinct'])
    })
    return reference_fields_dict

def get_record_count(api_endpoint):
    '''
    Retrieves the number of records
    '''
    params = {
        'where': '1=1',
        'outFields': 'OBJECTID',
        'returnIdsOnly': 'true',
        'returnCountOnly': 'true',
        'f': 'json'
    }
    response = requests.get(api_endpoint+'/query',params=params,headers=misc.headers)
    if response.status_code != 200:
        misc.log_error(api_endpoint, 'get_record_count', response)
        return None
    
    return response

def get_unique_count(api_endpoint,field):
    '''
    Retrieves the number of distinct values in a field
    '''
    params = {
        'where': '1=1',
        'outFields': field,
        'returnGeometry': 'false',
        'returnDistinctValues': 'true',
        'returnCountOnly': 'true',
        'f': 'json'
    }
    # sometimes this one timesout sents it's used multiple times
    response = requests.get(api_endpoint+'/query',params=params,headers=misc.headers)
    
    if response.status_code != 200:
        misc.log_error(api_endpoint, f'get_unique_count/{field}', response)
        return None
    if response.json().get('error') is not None:
        misc.log_error(api_endpoint, f'get_unique_count/{field}', response)
        return None
    
    try:
        return response.json()['count']
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, f'get_unique_count/{field}', error_message)
        return None

def get_unique_values(api_endpoint,field,threshold=20):
    '''
    Retrieves unique values in a field
    '''
    params = {
        'where': '1=1',
        'outFields': field,
        'returnGeometry': 'false',
        'returnDistinctValues': 'true',
        'f': 'json'
    }
    response = requests.get(api_endpoint+'/query',params=params,headers=misc.headers)
    
    if response.status_code != 200:
        misc.log_error(api_endpoint, f'get_unique_values/{field}', response)
        return None
    if response.json().get('error') is not None:
        misc.log_error(api_endpoint, f'get_unique_values/{field}', response)
        return None
    
    try:
        unique_vals = [unique_val for x in response.json()['features'] for unique_val in list(x['attributes'].values())]
        
        # if there is more than the threshold just return up to the threshold to get an idea of what the data look like
        if len(unique_vals) > threshold:
            unique_vals = unique_vals[0:threshold]

        return unique_vals
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, f'get_unique_values/{field}', error_message)
        return None

def get_stats(api_endpoint,field,stat_ops=['min','max','avg']):
    '''
    Does the inputed stat ops on the specified field
    Default is min/max/avg
    Put count to get number of non-null values
    '''
    out_stats = []
    for stat_op in stat_ops:
        out_stats.append({
            "statisticType": stat_op,
            "onStatisticField": field,
            "outStatisticFieldName": stat_op
        })
    params = {
        'outStatistics': str(out_stats),
        'f': 'json'
    }
    response = requests.get(api_endpoint+'/query',params=params,headers=misc.headers)
    
    if response.status_code != 200:
        misc.log_error(api_endpoint, f'get_stats/{stat_ops}/{field}', response)
        return None
        
    if response.json().get('error') is not None:
        misc.log_error(api_endpoint, f'get_stats/{stat_ops}/{field}', response)
        return None
        
    try:
        return response.json()['features'][0]['attributes']
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, f'get_stats/{stat_ops}/{field}', error_message)
        return None

def get_bbox(api_endpoint):
    '''
    Gets the bounding box of the dataset in EPSG 4326
    '''
    coordinate_precision = 5

    params = {
        'where': '1=1',
        'returnExtentOnly': 'true',
        'outSR': '4326',
        'f': 'json'
    }
    response = requests.get(api_endpoint+'/query',params=params,headers=misc.headers)

    if response.status_code != 200:
        misc.log_error(api_endpoint, 'get_bbox', response)
        return None

    try:
        response_json = response.json()
        bbox = {
            "xmin": round(response_json['extent']['xmin'],coordinate_precision),
            "ymin": round(response_json['extent']['ymin'],coordinate_precision),
            "xmax": round(response_json['extent']['xmax'],coordinate_precision),
            "ymax": round(response_json['extent']['ymax'],coordinate_precision)
        }
        return bbox
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, f'get_bbox', error_message)
        return None

#### Cleaning / Parsing Functions ####

def get_dates(timestamp):
    '''
    Converts esri timestamp to date (epochs)
    '''
    try:
        timestamp = datetime.datetime.fromtimestamp(timestamp/1000)
        return str(timestamp.date())
    except:
        return timestamp

def access_key(response_json,levels):
    # handles errors when accessing multiple levels of a large json
    response_json = response_json.copy()
    for level in levels:
        if isinstance(response_json,dict) == False:
            return None
        response_json = response_json.get(level)
    return response_json

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

#### Processing Functions Here ####

def process_description(response):
    description = response.get('description')
    if description == '':
        return None
    else:
        return description

def process_last_updated(response):
    last_updated = response.get('last_updated')
    date_format = "%Y-%m-%d"
    try:
        new_dates = []
        for date in last_updated:
            try:
                new_dates.append(datetime.strptime(date,date_format))
            except:
                continue
        if len(new_dates) > 0:
            most_recent_date = max(new_dates) # get most recent
            return datetime.strftime(most_recent_date,date_format)
    except:
        return None

def process_null_count(response_record,row_count):
    
    if response_record.get('non_null_count') is not None:
        if isinstance(row_count,int) & isinstance(response_record['non_null_count'],int) & (row_count != 0):
            return int(round((row_count - response_record['non_null_count']) / row_count * 100,0))
        else:
            return None

def process_unique_vals(response_record):
    '''
    Parses the unique values list
    - Sorts in ascending order
    '''

    if response_record.get('unique_values') is not None:

        unique_vals = response_record['unique_values']
        coded_vals = response_record['codedValues']

        if isinstance(unique_vals,list) == False:
            return None
        if len(unique_vals) == 0:
            return None

        # remove None from unique values
        unique_vals = [unique_val for unique_val in unique_vals if unique_val is not None]

        # if there are coded values, then replace
        if isinstance(coded_vals,dict):
            unique_vals = [coded_vals.get(unique_val) for unique_val in unique_vals if coded_vals.get(unique_val) is not None]

        # order in ascending order
        unique_vals = sorted(unique_vals)

        cleaned_unique_vals = []
        for val in unique_vals:
            # round floats to third decimal point
            if isinstance(val,float):
                cleaned_unique_vals.append(round(val,3))
            elif val is None:
                # skip if null
                continue
            elif isinstance(val,str):
                val = val.strip()
                # remove empty strings
                if val == '':
                    continue
                # remove <Null>
                if val == '<Null>':
                    continue
                # remove trailing spaces
                cleaned_unique_vals.append(val)
            # TODO might need to add more esri date fields here
            elif response_record.get('data_type') == "esriFieldTypeDate":
                cleaned_unique_vals.append(get_dates(val))
            else:
                cleaned_unique_vals.append(val)
        
        if len(cleaned_unique_vals) == 0:
            return None
        else:
            return cleaned_unique_vals

###

# def arcgis_process_results1(results,references,attributes,rest_references,rest_attributes):
    
#     # track which ones were successfully scraped
#     successfully_scraped = [result.get('dataset_id') for result in results if result.get('error_msg') is None]
    
#     references_scraped = pd.DataFrame.from_records([x.get('dataset') for x in results if x.get('dataset') is not None])
#     attributes_scraped = pd.concat([x.get('attributes') for x in results if x.get('attributes') is not None],axis=0)

#     # extract from results
#     references_scraped = pd.DataFrame.from_records([x.get('dataset') for x in results if x.get('dataset') is not None])
#     attributes_scraped = pd.concat([x.get('attributes') for x in results if x.get('attributes') is not None],axis=0)

#     ## Process references
    
#     # takes the most recent date
#     date_cols = ['lastEditDate','schemaLastEditDate','dataLastEditDate']
#     for column in date_cols:
#         references_scraped[column] = pd.to_datetime(references_scraped[column])
#     references_scraped['Last updated'] = references_scraped[date_cols].max(axis=1).apply(lambda x: None if str(x) == 'NaT' else str(x.year))

#     # remove html tags from the description field
#     references_scraped['Description'] = references_scraped['description'].apply(lambda x: misc.strip_tags(x) if isinstance(x,str) else None)

#     # clean up the columns
#     references_scraped = references_scraped[[x for x in references.columns if x in references_scraped.columns]]

#     # merge with REST dataframe
#     references_merged = pd.merge(rest_references,references_scraped,on='Dataset Alias')

#     # keep orginal data UNLESS null
#     columns0 = ['Description']
#     for column in columns0:
#         references_merged[column] = references_merged[f"{column}_x"].fillna(references_merged[f"{column}_y"])

#     # replace original data with scraped data if it's available
#     columns1 = ['Dataset Name','Last updated','Record Count','Field Count']
#     for column in columns1:
#         references_merged[column] = references_merged[f"{column}_y"].fillna(references_merged[f"{column}_x"])

#     # drop cols
#     references_merged.drop(columns=[x+'_x' for x in columns0+columns1],inplace=True)
#     references_merged.drop(columns=[x+'_y' for x in columns0+columns1],inplace=True)

#     # order cols
#     references_merged = references_merged[references.columns]

#     ## Process attributes
#     # fix the error ones
#     attributes_scraped.loc[attributes_scraped['count'].apply(lambda x: isinstance(x,str)),'count'] = np.nan

#     # create stats column
#     for x in ['min','max','avg']:
#         attributes_scraped[x] = attributes_scraped[x].apply(lambda x: misc.round_floats(x))
#     attributes_scraped['Statistics'] = attributes_scraped[['min','avg','max']].apply(lambda x: misc.stats_cols_to_str(x),axis=1)

#     # if coded values present put those else put in unique vals (needs a fix)
#     if attributes_scraped.get('codedValues',False):
#         remapped = attributes_scraped['unique_values'].map(attributes_scraped['codedValues'])
#         attributes_scraped['unique_values'] = remapped.fillna(attributes_scraped['unique_values'])

#     # clean the unique values
#     attributes_scraped['Unique Values'] = attributes_scraped['unique_values'].apply(lambda x: clean_unique_vals(x))

#     # if unique values are present, change the data type to categorical
#     # attributes_scraped.loc[attributes_scraped['Unique Values'].notna(),'data_type'] = 'Categorical'

#     attributes_scraped['non_null_count'] = attributes_scraped['non_null_count'].apply(lambda x: x if isinstance(x,str) == False else np.nan)

#     # get null count
#     map_dict = dict(zip(references_scraped['Dataset Alias'],references_scraped['Record Count']))
#     attributes_scraped['record_count'] = attributes_scraped['dataset_id'].map(map_dict)
#     attributes_scraped['Null Percent'] = (100 - (attributes_scraped['non_null_count'] / attributes_scraped['record_count'] * 100)).round(1)

#     col_rename = {
#         'name':'Attribute Name',
#         'alias': 'Attribute Alias Name',
#         'type': 'Data Type',
#         'count': 'Unique Counts',
#         'associated_element': 'Associated Element',
#         'notes': 'Notes',
#         'spec_variable_type': 'Spec Variable Type',
#         'dataset_id': 'Dataset Alias'
#     }
#     attributes_scraped.rename(columns=col_rename,inplace=True)

#     # clean up the columns
#     attributes_scraped = attributes_scraped[[x for x in attributes.columns if x in attributes_scraped.columns]]

#     # merge with REST dataframe
#     attributes_merged = pd.merge(rest_attributes,attributes_scraped,on=['Attribute Name','Dataset Alias'],how='right')

#     # keep orginal data UNLESS null
#     columns0 = ['Data Type','Attribute Alias Name']
#     for column in columns0:
#         attributes_merged[column] = attributes_merged[f"{column}_x"].fillna(attributes_merged[f"{column}_y"])

#     # replace original data with scraped data if it's available
#     columns1 = ['Unique Counts','Null Percent','Unique Values','Statistics']
#     for column in columns1:
#         attributes_merged[column] = attributes_merged[f"{column}_y"].fillna(attributes_merged[f"{column}_x"])

#     # drop cols
#     attributes_merged.drop(columns=[x+'_x' for x in columns0+columns1],inplace=True)
#     attributes_merged.drop(columns=[x+'_y' for x in columns0+columns1],inplace=True)

#     # order cols
#     attributes_merged = attributes_merged[attributes.columns]

#     # update the boolean column
#     references_merged.loc[references_merged['Dataset Alias'].isin(successfully_scraped),'Added to Attributes Sheets'] = True

#     return references_merged, attributes_merged
