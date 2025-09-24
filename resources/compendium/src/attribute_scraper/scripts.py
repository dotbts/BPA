from pathlib import Path
import json
import textwrap

from attribute_scraper import utils
from attribute_scraper import schemas

def check_integrity():
    utils.load_data(require_existence=True)
    print("Successfully validated!")

def add_new_scraped_data():

    references, attributes = utils.load_data()

    # check new_data.json for new data
    if (Path.cwd() / "new_data.json").exists():
        with (Path.cwd() / "new_data.json").open('r') as fh:
            new_data = json.load(fh)
        utils.run_validator(new_data,schemas.new_data_schema)
    else:
        raise Exception(f"No new data json at {Path.cwd() / "new_data.json"}")
    
    # cross-reference against existing
    if len(references) > 0:
        existing = [(item['dataset_id'],item['api_endpoint']) for item in references]
    else:
        existing = []

    if len(new_data) > 0:
        incoming = [(item['dataset_id'],item['api_endpoint']) for item in new_data]
    else:
        incoming = []

    # these are the potential new ones
    potential = list(set(incoming) - set(existing))

    # these already exist but could contain new manually added data
    remove = list(set.intersection(set(incoming),set(existing)))

    # for the ones that already exist, check to see if there are new non-null manual entries
    if len(remove) > 0:
        print("Merging existing keys")
        manual_updates = [item for item in new_data if (item['dataset_id'],item['api_endpoint']) in remove]
        # manual_updates = utils.update_references(references,[item for item in new_data if (item['dataset_id'],item['api_endpoint']) in remove])
        # manual_updates = [{key:item for key,item in record.items() if key in schemas.manual_fields + schemas.new_data_schema['items']['required']} for record in manual_updates]
        utils.backup_scraped_data(manual_updates,update_manual_fields=True) # updates the backup file
        reprocess_existing()

    # need to check to see htat both dataset_id and api_endpoint are unique within the potentials
    # EX: existing = ("test1","api_endpoint.json") & incoming = ("test2","api_endpoint.json") should not be possible
    def filter_list_of_tuples(item,idx):
        return [tuple_item[idx] for tuple_item in item]
    dup_ids = set.intersection(set(filter_list_of_tuples(potential,0)),set(filter_list_of_tuples(existing,0)))
    dup_endpoints = set.intersection(set(filter_list_of_tuples(potential,1)),set(filter_list_of_tuples(existing,1)))
    
    malformed = [str(item) for item in potential if (item[0] in dup_ids) & (item[1] not in dup_endpoints)]
    if len(malformed) > 0:
        print(textwrap.dedent(
            f"""
            NOTE: These records have a unique API endpoint but
            not a unique dataset_id:
            {"\n".join(malformed)} 
            """
        ))
    
    final = [item for item in potential if (item[0] not in dup_ids) & (item[1] not in dup_endpoints)]
        
    print(f"{len(final)} new datasets to be scraped")
    # exit if no new data to scrape
    if len(final) > 0:
        
        to_scrape = [item for item in new_data if (item['dataset_id'],item['api_endpoint']) in final]

        # scrape new data
        results = utils.general_scraper(to_scrape)

        #NOTE these are all inplace operations, no need to re-assign
        # backup scraped data
        utils.backup_scraped_data(results)

        # # process scraped data
        utils.process_results(results)

        # # wrangle data into the right format to merge
        incoming_references, incoming_attributes = utils.add_new_to_existing(results)
        
        # merge references and add attributes
        merged_references = utils.update_references(references,incoming_references)
        merged_attributes = utils.update_attributes(attributes,incoming_attributes)

        # integrity check before exporting
        utils.run_validator(merged_references,schemas.references_schema)
        utils.run_validator(merged_attributes,schemas.attributes_schema)

        # export references/attributes
        utils.save_json(merged_references,Path.cwd()/"data/references.json")
        utils.save_json(merged_attributes,Path.cwd()/"data/attributes.json")

        updated_ref = [(item['dataset_id'],item['api_endpoint']) for item in merged_references]
        remove += updated_ref
        
    remove = list(set(remove))
    if len(remove) > 0:
        awaiting_input = True
        while awaiting_input:
            input_str = input(textwrap.dedent(
                f"""
                Do you want to remove records from
                new_data.json that already exist in references.json?
                WARNING: Permanent
                (enter 'yes' or 'no') 
                """
            ))
            if input_str in ["yes","y"]:
                new_data = [item for item in new_data if (item['dataset_id'],item['api_endpoint']) not in remove]
                utils.save_json(new_data,Path.cwd()/"new_data.json")
                awaiting_input = False
            elif input_str in ["no","n"]:
                awaiting_input = False
            else:
                print("Type 'yes' or 'no'")

def rescrape_by_id():
    
    references, attributes = utils.load_data()

    awaiting_response = True
    while awaiting_response:
        input_str = input(textwrap.dedent(
            """
            Type the dataset_id(s) in single quotes that
            you want to re-scrape.
            Seperate dataset IDs with spaces like:
            'city bike lanes' 'city_curb_ramps'
            
            Or just type '*' to rescrape everything.\n
            """
        ))

        # find dataset_ids
        existing_ids = [item['dataset_id'] for item in references]
        
        if input_str == '*':
            dataset_ids = existing_ids
        else:
            dataset_ids = utils.parse_quoted_tokens(input_str)
        
        common = set.intersection(set(dataset_ids),set(existing_ids))
        
        if len(common) > 0:
            to_scrape = [{key:item for key, item in record.items() if key in schemas.manual_fields + schemas.required_fields} for record in references if record['dataset_id'] in common]
            results = utils.general_scraper(to_scrape)
            utils.backup_scraped_data(results)
            utils.process_results(results)
            incoming_references, incoming_attributes = utils.add_new_to_existing(results)
            merged_references = utils.update_references(references,incoming_references)
            merged_attributes = utils.update_attributes(attributes,incoming_attributes)

            # export references/attributes
            utils.save_json(merged_references,Path.cwd()/"data/references.json")
            utils.save_json(merged_attributes,Path.cwd()/"data/attributes.json")

            awaiting_response = False

        else:
            print("Dataset IDs not found, try again")

def reprocess_existing():
    # load existing
    references, attributes = utils.load_data()

    # load scraped data backup
    results = utils.load_json(Path.cwd()/"data/scraped_data.json")

    # run processing functions
    utils.process_results(results)

    # wrangle data into the right format to merge
    incoming_references, incoming_attributes = utils.add_new_to_existing(results)
    
    # merge references and add attributes
    merged_references = utils.update_references(references,incoming_references)
    merged_attributes = utils.update_attributes(attributes,incoming_attributes)

    # integrity check before exporting
    utils.run_validator(merged_references,schemas.references_schema)
    utils.run_validator(merged_attributes,schemas.attributes_schema)

    # export references/attributes
    utils.save_json(merged_references,Path.cwd()/"data/references.json")
    utils.save_json(merged_attributes,Path.cwd()/"data/attributes.json")

    def scrape_location_data():
        # load existing
        references, _ = utils.load_data()

        # load existing location data if it exists

        # grab all existing bounding boxes

        # find references that haven't been added

        # scrape data from BTS api endpoints if there are references that haven't been added

        # update/save location data

        # write new version of references/attributes with the updated data