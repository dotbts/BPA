import textwrap

from attribute_scraper import scripts

if __name__ == "__main__":
        
    awaiting_repsonse = True
    while awaiting_repsonse:
        input_str = input(textwrap.dedent(
            """
            ___________________________________________________________________________________
            Welcome to the GATIS Attribute Scraper! Please select one of the following options:
            
            0 = check data integrity of attributes.json and references.json
            1 = scrape new data from new_data.json
            2 = update references.json/attributes.json using scraped_data.json (debugging)
            3 = rescrape existing data
            OR type 'exit' to exit
            ___________________________________________________________________________________
            """
        ))

        if input_str == "exit":
            raise Exception("Exited")
        elif input_str == "0":
            scripts.check_integrity()
            awaiting_repsonse = False
        elif input_str == "1":
            scripts.add_new_scraped_data()
            awaiting_repsonse = False
        elif input_str == "2":
            scripts.reprocess_existing()
            awaiting_repsonse = False
        elif input_str == "3":
            scripts.rescrape_by_id()
            awaiting_repsonse = False
        # NOTE: see experimental version of this code in scratch.ipynb
        # elif input_str == "4":
        #     scripts.scrape_location_data()
        #     awaiting_repsonse = False
        else:
            print("\nPlease type an option from the available options:")
        
        