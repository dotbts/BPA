from datetime import datetime
import numpy as np
import requests
import pandas as pd
import sys

from attribute_scraper import misc

### Main Functions ###

def tyler_scrape(api_endpoint):
    
    # wrangle the api_endpoint to create the dataset url
    domain = api_endpoint.split("https://")[-1].split('/')[0]
    dataset_identifier = api_endpoint.split("/")[-1].split('.json')[0]
    metadata_url = f"https://{domain}/api/views/{dataset_identifier}.json"
    response = requests.get(metadata_url)        

    #TODO error handling here

    metadata_json = response.json()

    references = {
        'dataset_name': metadata_json.get('name'),
        # 'entity': [metadata_json.get('attribution')], # not always descriptive enough
        'description': metadata_json['description'],
        'last_updated': [metadata_json.get('rowsUpdatedAt'),metadata_json.get('viewLastModified')],
        'row_count': get_record_count(api_endpoint),
        'column_count': len(metadata_json['columns'])
    }

    attributes = []

    for record in metadata_json['columns']:
        
        # general information
        attribute = {
            'attribute_id': record.get('fieldName'),
            'attribute_alias': record.get('name'),
            'data_type': record.get('dataTypeName'),
            'null_percent': get_null_percent(record),
            'unique_counts': get_unique_count(api_endpoint,record.get('fieldName')),
            'unique_values': get_unique_values(api_endpoint,record.get('fieldName'))
        }

        # statistics if number or date
        if attribute['data_type'] in ['number','date']:
            stats = get_stats(api_endpoint,record['fieldName'],attribute['data_type'])
            if stats is not None:
                attribute.update(stats)

        # bbox if there is a geometry column
        if attribute['data_type'] in ['point','multipoint','line','multiline','polygon','multipolygon']:
            references['bbox'] = get_bbox(api_endpoint,record.get('fieldName'))
    
        attributes.append(attribute)

    return references, attributes

def tyler_process_results(result):
    '''
    Processes tyler tech scraped data into schema format
    '''

    response = result.get('response')
    if response is None:
        raise f"No scrpaed data found for {result.get("dataset_id")}"
    
    # don't require any special processing
    references = {}
    keys = ["description","column_count","row_count","bbox"]
    for key in keys:
        # if response[0].get(key) is not None:
        references[key] = response[0].get(key)

    references['last_updated'] = process_last_updated(response[0])

    attributes = []
    keys = ['attribute_id','attribute_alias','data_type','unique_count','unique_values','null_percent','min','max','avg','sum']
    for response_record in response[1]:
        record = {}
        for key in keys:
            record[key] = response_record.get(key)
        
        # convert uniquevalues to string?

        # if number be sure to convert back to numeric
        if record.get('data_type') == 'number':
        
            # for unique_values
            if record.get('unique_values') is not None:
                record['unique_values'] = [float(x) for x in record.get('unique_values')]

            # convert strings to numbers
            for stat in ['min','max','avg','sum']:
                if (record.get(stat) is not None):
                    record[stat] = float(record[stat])
        
        attributes.append(record)

    # update the dictionary (don't need to return)
    result['processed_response'] = (references,attributes)

def get_record_count(api_endpoint):
    params = {
    '$select':
    f"""
    COUNT(*)
    """,
    }
    response = requests.get(api_endpoint,params=params)
    if response.status_code != 200:
        misc.log_error(api_endpoint, 'get_unique_count', response)
        return None #response.status_code
    return int(response.json()[0]['COUNT'])

def get_null_percent(record):
    try:
        return round(int(record.get('cachedContents').get('null')) / int(record.get('cachedContents').get('count')) * 100,1)
    except:
        return None

def get_dates(timestamp):
    try:
        timestamp = datetime.datetime.fromtimestamp(timestamp)
        return timestamp.year
    except:
        return None
    
def get_unique_count(api_endpoint,field):
    params = {
    '$select': f'COUNT(DISTINCT {field})',
    }
    response = requests.get(api_endpoint,params=params)
    
    try:
        return int(list(response.json()[0].values())[0])
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, 'get_unique_count', error_message)
        return None

def get_stats(api_endpoint,field,data_type='number'):
    if data_type in ['date','calendar_date']:
        params = {
        '$select':
            f"""
            max({field}) AS max,
            min({field}) AS min
            """,
        }
    elif data_type == 'number':
       params = {
        '$select':
            f"""
            max({field}) AS max,
            min({field}) AS min,
            avg({field}) AS avg,
            sum({field}) AS sum
            """,
        }
    else:
        return None 
    response = requests.get(api_endpoint,params=params)
    
    if response.status_code != 200:
        misc.log_error(api_endpoint, 'get_stats', response)
        return None
    
    return response.json()[0]

def get_unique_values(api_endpoint,field,threshold=20):
    params = {
    '$select':
        f"""
        DISTINCT {field}
        """,
    }
    response = requests.get(api_endpoint,params=params)
    
    unique_values = []
    try:
        for value in response.json():
            value = list(value.values())
            if len(value) > 0:
                unique_values.append(value[0])
        unique_values = sorted(unique_values)
        if len(unique_values) > threshold:
            return unique_values[0:threshold]
        else:
            return unique_values
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, 'get_unique_values', error_message)
        return None
    
def get_bbox(api_endpoint,field):
    params = {
        '$select':
            f"""
            extent({field})
            """,
    }

    response = requests.get(api_endpoint,params=params)

    try:
        bbox = response.json()[0]['extent_the_geom']['coordinates'][0][0]
        xvals = [x[0] for x in bbox]
        yvals = [y[1] for y in bbox]
        print(xvals)
        print(yvals)
        bbox = {
            "xmin": min(xvals),
            "ymin": min(yvals),
            "xmax": max(xvals),
            "ymax": max(yvals)
        }
        return bbox
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        misc.log_error(api_endpoint, 'get_bbox', error_message)
        return None
    
def process_last_updated(response):
    last_updated = response.get('last_updated')
    # drop non numeric values
    last_updated = [x for x in last_updated if x is not None]
    last_updated = max(last_updated)
    date_format = "%Y-%m-%d"
    try:
        return datetime.strftime(datetime.fromtimestamp(last_updated),date_format)
    except:
        error_message = sys.exc_info()[1] # retrieves the error message
        print(error_message)
        return None