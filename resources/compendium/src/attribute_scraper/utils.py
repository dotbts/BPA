import pandas as pd
import numpy as np
from tqdm import tqdm
import sys
import pickle
import json
import re
import textwrap
from datetime import datetime
from pathlib import Path
from collections import Counter

from attribute_scraper import arcgis_scrape, tyler_scrape, schemas, misc

##################### Validator and Uniqueness Scripts #####################

from jsonschema import Draft202012Validator, validate
validator = Draft202012Validator({})
def json_schema_validate(data,schema,print_results=False):
    validate(instance=data,schema=schema,format_checker=Draft202012Validator.FORMAT_CHECKER)
    if print_results:
        print("Compliant to schema!")

def run_validator(data,schema):
    """
    Validates a references or attributes object
    """

    json_schema_validate(data,schema)
    
    # check uniqueness
    primary_keys = schema['items']['primaryKeys']
    primary_keys = [tuple([item[primary_key] for primary_key in primary_keys]) for item in data]
    if (schema == schemas.references_schema) | (schema == schemas.new_data_schema):
        # ensure each primary key is unique
        for x in range(0,len(primary_keys)):
            uniqueness_check = Counter([x[0] for x in primary_keys])
            duplicate_ids = [key for key, item in uniqueness_check.items() if item > 1]
    elif (schema == schemas.attributes_schema):
        primary_keys = Counter(primary_keys)
        duplicate_ids = [key for key, item in primary_keys.items() if item > 1]
    else:
        raise Exception("Schema not found")
    
    if len(duplicate_ids) > 0:
        raise Exception("Duplicate IDs present:",duplicate_ids)

def run_validator_relations(references,attributes):
    """
    Checks to see if keys in references are all in attributes and vice versa
    """

    run_validator(references,schemas.references_schema)
    run_validator(attributes,schemas.attributes_schema)

    references_keys = set([(item['dataset_id'],item['api_endpoint']) for item in references])
    attributes_keys = set([(item['dataset_id'],item['api_endpoint']) for item in attributes])

    unmatched_keys = set.symmetric_difference(references_keys,attributes_keys)
    if len(unmatched_keys) > 0:
        raise Exception("There are unmatched keys:",unmatched_keys)

##################### Functions #####################

# maps the api_id to the correct scraping function
scrape_functions = {
    'arcgis': arcgis_scrape.arcgis_scrape,
    'tyler': tyler_scrape.tyler_scrape
}
processing_functions = {
    'arcgis': arcgis_scrape.arcgis_process_results,
    'tyler': tyler_scrape.tyler_process_results
}

def iso_datetime():
    '''
    Return the current time in ISO format with UTC offset from the system time
    '''
    return datetime.now().astimezone().isoformat(timespec='minutes')

def general_scraper(inputs):
    '''
    Performs the scraping routine for a list of dicts in the proper format

    Errors are returned for tracking which queries need to be re-run

    TODO: this is the function that could be parallelized. Running the queries
    one by one is pretty slow.
    '''

    #TODO JSON schema check goes here
    #TODO parallelize this step to run a bunch of api calls at once

    # get the scraping 
    results = []
    for input in tqdm(inputs):                
        try:
            # confirm that api_id has a valid scraping function
            if scrape_functions[input['api_id']] is None:
                raise Exception(f"api_id {input['api_id']} does not have a valid scraping function")
            
            result = scrape_functions[input['api_id']](input['api_endpoint'])
            results.append(
                input | {
                    'response' : result,
                    'status': 'success',
                    'status_date': iso_datetime()
                }
            )
        except:
            error_message = sys.exc_info()[1] # retrieves the error message
            print(f"Failed to retrieve data for {input['dataset_id']}")
            print("Error message:",error_message)
            results.append(
                input | {
                    'status': 'failure',
                    'status_date': iso_datetime()
                }
            )
            # add to error logger
            misc.log_error(input['api_endpoint'],'general_scraper',error_message)
   
    return results

def process_results(results):
    '''
    Takes in a results dictionary and processes the response key and places the results in a
    new processed_response key.

    Modifies the dictionary in place.
    '''

    for result in results:
        try:
            if processing_functions.get(result['api_id']) is None:
                raise Exception(f"api_id {result['api_id']} does not have a valid processing function")
            
            processing_functions[result['api_id']](result)

        except:
            error_message = sys.exc_info()[1]
            print(f"Failed to process data for {result['dataset_id']}")
            print("Error message:",error_message)

def add_new_to_existing(processed_results):
    '''
    Takes a processed results object and returns a references and attributes objects
    '''

    new_references = []
    new_attributes = []

    for result in processed_results:
        
        result_copy = result.copy()

        # grab processed response if it exists
        if result_copy.get('processed_response') is None:
            continue
        processed_response = result_copy['processed_response']

        # remove from dict
        result_copy.pop('response')
        result_copy.pop('processed_response')
        
        # update keys (overwrites existing keys)
        result_copy.update(processed_response[0])

        new_references.append(result_copy)

        # add dataset_id and api_endpoint to attributes
        new_attributes += [{**x,"dataset_id":result_copy['dataset_id'],'api_endpoint':result_copy['api_endpoint']} for x in processed_response[1]]
        
    return new_references, new_attributes

def update_references(existing,incoming):
    '''
    This function merges existing and incoming into one list of records.

    If existing is empty, then it will return incoming.

    New values in incoming and non-conflicting values in existing get combined.

    Any 
    
    For references we want to lean towards appending data rather than replacing in case there are
    existing values

    Need to state the merging policies so that they're clear

    Optionally, you can just edit the source json file and then just use validate to check your work

    '''

    print("-------------------------")
    print("Updating references.json")
    print("-------------------------")

    # if references is empty just export the incoming
    if len(existing) == 0:
        return incoming

    # wrangle so it's easier to access entries
    existing_dict = {(x['dataset_id'],x['api_endpoint']):x for x in existing}
    incoming_dict = {(x['dataset_id'],x['api_endpoint']):x for x in incoming}
    existing_keys, incoming_keys = set(existing_dict.keys()), set(incoming_dict.keys())

    merged = [] # initialize empty list to put merged entries into
    merge_conflicts = [] # initialize empty list to put merge conflicts into

    # untouched and new values just get appended since they're already schema compliant
    untouched_keys = existing_keys - incoming_keys
    merged += [item for key, item in existing_dict.items() if key in untouched_keys]
    new_keys = incoming_keys - existing_keys
    print(f"{len(new_keys)} new records added to existing {len(existing_keys)} records")
    merged += [item for key, item in incoming_dict.items() if key in new_keys]
    
    # find conflicting keys
    merge_keys = set.intersection(incoming_keys,existing_keys)
    
    # exit if no conflicts
    if len(merge_keys) == 0:
        return merged
    
    # determine if conflicts can be autosolved
    # non-null values take precedence
    for merge_key in merge_keys:
        null_keys, overwrite_keys = [], []
        exist_dict, inc_dict = existing_dict.get(merge_key).copy(), incoming_dict.get(merge_key).copy()
        
        # only add incoming keys if not null
        for key, item in inc_dict.items():
            exist_item = exist_dict.get(key)
            
            def check_null(item):
                if item is None:
                    return True
                if isinstance(item,str):
                    if item == '':
                        return True
                if isinstance(item,list):
                    if len(item) == 0:
                        return True
                    if len(item) == 1:
                        if item[0] is None:
                            return True

            # skip incoming item if null        
            if check_null(item):
                continue
            # check if existing is null
            if check_null(exist_item):
                null_keys.append(key)
                continue
            
            # if equivalent then skip
            if item == exist_item:
                continue

            # both existing and incoming item are not not null and different
            overwrite_keys.append(key)

        # create two versions
        # preserve_existing doesn't replace
        null_dict = {key:item for key,item in inc_dict.items() if key in null_keys}
        overwrite_dict = {key:item for key,item in inc_dict.items() if key in overwrite_keys}
        preserve_dict = {key:item for key,item in exist_dict.items() if key in overwrite_keys}
        preserve_existing = {**exist_dict,**null_dict}
        overwrite_existing = {**exist_dict,**null_dict,**overwrite_dict}

        # if data are equivalent add to merged
        if (preserve_existing == overwrite_existing):
            merged.append(overwrite_existing)
            continue
        else:
            merge_conflicts.append((preserve_existing,preserve_dict,overwrite_existing,overwrite_dict))

    # check if there are remaining merge conflicts that need manual attention
    if len(merge_conflicts) > 0:
        awaiting_input = True
        while awaiting_input:
            input_str = input(textwrap.dedent(
            f"""
            {len(merge_conflicts)} conflicts. Please select from the following options:
            1 = review each merge conflict
            2 = overwrite existing  with new (non-null values will not be overwritten with null)
            """
            ))
            if (input_str == "1"):
                overwrite_all = False
                awaiting_input = False
            elif (input_str == "2"):
                overwrite_all = True
                awaiting_input = False
            elif input_str == "exit":
                raise Exception("Merging process cancelled")
            else:
                print("Invalid response")

        for preserve_existing,preserve_dict,overwrite_existing,overwrite_dict in merge_conflicts:
            if overwrite_all:
                merged.append(overwrite_existing)
                continue
            
            awaiting_input = True
            while awaiting_input:    
                # API Endpoint: {preserve_existing['api_endpoint']}
                input_str = input(textwrap.dedent(
                    f"""
                    -------------------------------------------------------------------------
                    Press '1' to preserve existing data, press '2' to overwrite existing data.
                    Or type the key name(s) that you want to preserve (separated with spaces no quotes)
                    Dataset ID: {preserve_existing['dataset_id']}
                    -------------------------------------------------------------------------
                    Existing Data [1]: {preserve_dict}
                    Incoming Data [2]: {overwrite_dict}
                    -------------------------------------------------------------------------
                    """
                ))
                if input_str == "1":
                    awaiting_input = False
                    merged.append(preserve_existing)
                elif input_str == "2":
                    awaiting_input = False
                    merged.append(overwrite_existing)
                elif input_str == "exit":
                    raise Exception("Merging prosses cancelled")
                elif input_str.split(' '):
                    for key in input_str.split(' '):
                        if key in overwrite_keys:
                            overwrite_existing[key] = preserve_existing[key]
                            awaiting_input = False
                        else:
                            print(f"{key} key does not exist, try again")
                            awaiting_input = True
                    merged.append(overwrite_existing)
                else:
                    print("Invalid input")
    return merged

def update_attributes(existing,incoming):
    if len(existing) == 0:
        return incoming
    existing_keys = [(item['attribute_id'],item['dataset_id'],item['api_endpoint']) for item in existing]
    incoming_keys = [(item['attribute_id'],item['dataset_id'],item['api_endpoint']) for item in incoming]
    shared_keys = set.intersection(set(existing_keys),set(incoming_keys))
    only_existing = [item for item in existing if (item['attribute_id'],item['dataset_id'],item['api_endpoint']) not in shared_keys]
    return only_existing + incoming

def mk_new_dir(fp):
    if fp.parent.is_dir() == False:
        fp.parent.mkdir(parents=True)

def backup_scraped_data(results:list,update_manual_fields=False):
    """
    Creates a backup of the scraped results

    Only overwrites existing values if status == success
    """
    
    fp = Path.cwd() / "data/scraped_data.json"
    
    # check if existing backup exists
    if fp.exists() == False:
        print('creating new one')
        # create directory if it doesn't exist
        mk_new_dir(fp)
        # save it
        with fp.open('w') as fh:
            json_string = json.dumps(results, indent=4)
            fh.write(json_string)
    elif update_manual_fields:
        # load existing
        with fp.open('r') as fh:
            backup = json.load(fh)

        # merge existing backup with new backup
        new_backup = update_references(backup,results)
        save_json(new_backup,fp)

    else:
        # load existing
        with fp.open('r') as fh:
            backup = json.load(fh)

        # get (dataset_id,api_id) if status == success
        add_to_backup = [(x['dataset_id'],x['api_endpoint']) for x in results if x['status'] == 'success']

        # remove from backup
        backup = [x for x in backup if (x['dataset_id'],x['api_endpoint']) not in add_to_backup]

        # append new ones
        backup += [x for x in results if x['status'] == 'success']

        # save
        with fp.open('w') as fh:
            json_string = json.dumps(backup, indent=4)
            fh.write(json_string)

def save_json(data,fp):
    with fp.open('w') as fh:
        json_string = json.dumps(data, indent=4)
        fh.write(json_string)

def load_json(fp):
    if fp.exists() == False:
        raise Exception(f"File not found: {fp}")
    with fp.open('rb') as fh:
        return json.load(fh)

def load_data(require_existence=False):
    '''
    Loads references.json and attributes.json and also checks their integrity + the scraped_data.json
    '''
    
    # load the references file if it exists
    if (Path.cwd() / "data/references.json").exists():
        with (Path.cwd() / "data/references.json").open('r') as fh:
            references = json.load(fh)
        run_validator(references,schemas.references_schema) # check to see if valid
    elif require_existence:
        raise Exception("references.json does not exist")
    else:
        references = []

    # load the attributes file if it exists
    if (Path.cwd() / "data/attributes.json").exists():
        with (Path.cwd() / "data/attributes.json").open('r') as fh:
            attributes = json.load(fh)
        run_validator(attributes,schemas.attributes_schema)  # check to see if valid
    elif require_existence:
        raise Exception("attributes.json does not exist")
    else:
        attributes = []

    # load the backup file if it exists
    if (Path.cwd()/"data/scraped_data.json").exists():
        results = load_json(Path.cwd()/"data/scraped_data.json")
        [x.pop('response') for x in results]
        run_validator(results,schemas.new_data_schema)
    elif require_existence:
        raise Exception("scraped_data.json does not exist")

    return references, attributes

def give_unique_name(fp):
    counter = 0
    ext = fp.name.split('.')[-1]
    new_fp = fp
    while new_fp.exists():
        new_fp = fp.parent / f"{fp.stem} ({counter}).{ext}"
        counter += 1
    return new_fp

# for stripping html tags from the description column
# from: https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
from io import StringIO
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def round_floats(x,round_floats_to=3):
    if isinstance(x,int):
        return x
    if isinstance(x,float):
        return round(x,round_floats_to)
    if isinstance(x,str) == False:
        return None
    if '.' in x:
        try:
            return str(round(float(x),round_floats_to))
        except:
            return x
    else:
        return x
    
import re
# for parsing inputs
def parse_quoted_tokens(s: str, allow_empty: bool = False) -> list[str]:
    """
    Parses a string like "'test' 'test'" into ['test', 'test'].

    Args:
        s: Input string to parse.
        allow_empty: If True, tokens can be empty (e.g. '').

    Returns:
        List of token strings without quotes.

    Raises:
        ValueError: If input string does not match the required format.
    """
    # Validation regex:
    if allow_empty:
        pattern = r"^'(?:[^']*)'(?:\s+'(?:[^']*)')*$"
        extract_pattern = r"'([^']*)'"
    else:
        pattern = r"^'(?:[^']+)'(?:\s+'(?:[^']+)')*$"
        extract_pattern = r"'([^']+)'"

    if not re.fullmatch(pattern, s):
        raise ValueError("Invalid format: string must contain one or more single-quoted tokens separated by whitespace.")

    return re.findall(extract_pattern, s)