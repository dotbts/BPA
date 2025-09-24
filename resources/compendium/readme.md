# NC-BPAID Active Transportation Infrastructure Data Attribute Scraper
This code is for scraping attribute information from ESRI and Tyler Technologies API endpoints. It was developed to help support the NC-BPAID specification development team in showing how existing datasets represent active transportation and universal accessibility attributes.

**All datasets were acquired through open data portals.**

## Installation

Use the `environment.yml` file to create a new environment with a name `attribute_scraper`:

```
conda env create -f environment.yml
```

Activate the environment:

```
conda activate attribute_scraper:
```

Install the attribute_scraper module. Change directory to `src` and run:

```
pip install -e .
```

## Usage

1. Add new data that you want to scrape or edit into the provided `new_data.json` file (see the section on submitting new data)
1. Run `main.py` from the root of the repository directory and follow the instructions in the terminal.

```
python main.py
```

See the following sections for the functionalities of the attribute scraper.

### Submitting New Datasets
To add new datasets, add objects to `new_data.json` that adhere to the `references_schema` in `src/attribute_scraper/schemas.py`. At minimum, you must provide a `dataset_id`, `api_endpoint`, and `api_id` for each datasource. Ideally, you should also provide the other information such as city/entity/county/etc. If you do provide this information, try to be consistent across data sources to make filtering easier.

```
[
    {
        "dataset_id": "Arizona Medians and Sidewalks",
        "tags": ["pedestrian","bike","sidewalks","medians"],
        "note": "This an example",
        "entity": ["Maricopa Association of Governments","Arizona DOT"],
        "state": ["AZ"],
        "info_url": "https://arizona-sun-cloud-agic.hub.arcgis.com"
        "api_id": ["arcgis"],
        "api_endpoint": "https://services6.arcgis.com/clPWQMwZfdWn4MQZ/arcgis/rest/services/Sun_Cloud_Medians_and_Sidewalks/FeatureServer/0"
    }
]
```

Then run `python main.py` and press `1`. The script will validate the data and check it against the existing data to make sure there isn't a duplicate entry. The scraped data gets placed in `data/scraped_data.json`.

## Updating Existing Data
To update the existing data, either place the updated data in `new_data.json` and re-scrape the data OR edit `scraped_data.json` directly with the edits. Be sure to run a data integrity check before committing changes (press `0` after running the main script). **DO NOT EDIT `data/references.json` or `data/attributes.json` directly.**

### Data Dictionary
The `data` folder contains two JSON files: `references.json` and `attributes.json`. Both files are checked against the JSON Schemas in `src/attribute_scraper/schemas.py`, respectively. **These files should never be edited directly** to prevent unintended schema violations. The 

### references.json
The primary key is `(dataset_id,api_endpoint)`. A JSON array of object with the following general structure:

| Name | Type | Description |
| - | - | - |
| `dataset_id` | string | Friendly ID used to uniquely indentify the dataset |
| *`dataset_name`* | string | Name of the dataset |
| *`description`* | string | Description of the dataset |
| *`row_count`* | number | Number of rows in the dataset |
| *`column_count`* | number | Number of columns in the dataset |
| *`last_updated`* | string | Last updated date for the dataset |
| `tags` | array<string> | User defined tags |
| `notes` | string | A user-inputted description/annotation of the data (useful when a description isn't provided) |
| `entity` | array<string> | Entity/entities responsible for maintaining the data |
| `state` | array<enum> | States that the data cover (MUST be two character code) |
| `county` | array<string> | Counties that the data cover |
| `city` | array<string> | Cities that the data cover |
| *`bbox`* | array<string> | A bounding box from the data |
| `info_url` | string | URL for information/overview of the dataset |
| `api_endpoint` | string | URL |
| `api_id` | enum | API enpoint type (must be "arcgis", "tyler") |
| *`status`* | enum | Scraping status (must be "success") |
| *`status_data`* | string | A data in YYYY-MM-DD format 
*NOTE: Italicized key values are created by the scraping process*

### attributes.json
The primary key is `(dataset_id, attribute_id)`. A JSON array of object with the following general structure:

| Name | Type | Description |
|-|-|-|
| *`attribute_id`* | string | Attribute name as it appears in the dataset (primary key) |
| `dataset_id` | string | Foreign key from `references.json` |
| *`attribute_alias`* | string |  |
| *`data_type`* | string | Data type for the attribute ([ESRI](https://pro.arcgis.com/en/pro-app/latest/help/data/geodatabases/overview/arcgis-field-data-types.htm) or [Tyler Technologies](https://dev.socrata.com/docs/datatypes/#,)) |
| *`unique_values`* | array<string> | List of unique values for the attribute |
| *`null_percent`* | number | The percentage of values that are NULL or empty |
| *`min`* | number | The minimum value if the data type is numeric |
| *`max`* | number | The maximum value if the data type is numeric |
| *`avg`* | number | The average value if the data type is numeric |
| *`sum`* | number | The sum if the data type is numeric |
*NOTE: Italicized key values are created by the scraping process*

# Known Issues
- Sometimes the Tyler Technologies API will need an API key and so none of the data will be returned
- The `status` and `status_date` fields in `scraped_data.json` were added later on so not all of the entries have it. When re-scraping data the status and status data fields will trigger a merge conflict
- If changing the `scraped_data.json` file directly, I recommend deleting `attributes.json` and `references.json` before re-scraping new data. (especially if you edit `dataset_id` or `api_endpoint`)