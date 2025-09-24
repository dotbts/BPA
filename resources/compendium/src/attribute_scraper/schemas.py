# todo add territories
state_codes = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "AS", "GU", "MP", "PR", "VI"
      ]

# these are the fields needed to properly run the scraping function
required_fields = ["dataset_id","api_endpoint","api_id"]

# these fields are only manually edited not scraped
# TODO geographic ones will hopefully get scraped using FIPS and bounding box
manual_fields = [
    "dataset_id","tags","notes",
    "entity","state","county",
    "metropolitan_statistical_area","city",
    "info_url", "api_endpoint", "api_id"
    ]
metadata_fields = [
    "status", "status_date"
]
# see the readme.md for descriptions for the keys

# useful for formats: https://json-schema.org/understanding-json-schema/reference/type
# TODO add annotations to the spec
references_schema = {
    "$schema": "https://json-schema.org/draft/2020-12",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "dataset_id": {"type": "string"},
            "dataset_name": {"type": ["string","null"]},
            "description": {"type": ["string","null"]},
            "row_count": {"type": ["number","null"]},
            "column_count": {"type": ["number","null"]},
            "last_updated": {
                "oneOf": [
                    {"type":"string","format":"date"},
                    {"type":"null"}
                ]
            },
            "tags": {
                "oneOf": [
                    {"type":"array","items":{"type":"string"}},
                    {"type":"null"}
                ]
            },
            "notes": {"type": ["string","null"]},
            "entity": {
                "oneOf": [
                    {"type":"array","items":{"type":"string"}},
                    {"type":"null"}
                ]
            },
            "state": {
                "oneOf": [
                    {"type":"array","items":{"type":"string","enum":state_codes}},
                    {"type":"null"}
                ]
            },
            "county": {
                "oneOf": [
                    {"type":"array","items":{"type":"string"}},
                    {"type":"null"}
                ]
            },
            "metropolitan_statistical_area": {
                "oneOf": [
                    {"type":"array","items":{"type":"string"}},
                    {"type":"null"}
                ]
            },
            "city": {
                "oneOf": [
                    {"type":"array","items":{"type":"string"}},
                    {"type":"null"}
                ]
            },
            #TODO: add min/max to bound numbers between -180 and 180
            "bbox": {
                "oneOf": [
                    {
                        "type":"object",
                        "properties": {
                            "xmin":{"type":"number","minimum":-180,"maximum":180},
                            "ymin":{"type":"number","minimum":-180,"maximum":180},
                            "xmax":{"type":"number","minimum":-180,"maximum":180},
                            "ymax":{"type":"number","minimum":-180,"maximum":180}
                        },
                        "required": ["xmin", "ymin", "xmax", "ymax"],
                        "additionalProperties": False
                    },
                    {"type":"null"}
                ]
            },
            "geographic_area": {"type":["string","null"]},
            "info_url": {
                "oneOf": [
                    {"type":"array","items":{"type":"string","format":"uri"}},
                    {"type":"null"}
                ]
            },
            "api_endpoint": {"type": "string","format":"uri"},
            "api_id": {"type": "string", "enum": ["arcgis","tyler","download"]},
            "status": {"type": "string", "enum": ["success","failure","warnings","not_scraped"]},
            "status_date": {
                "oneOf": [
                    {"type":"string","format":"datetime"},
                    {"type":"null"}
                ]
            },
        },
        "required": required_fields, # the required ones should just be the things you need to scrape data
        "primaryKeys": ["dataset_id", "api_endpoint"],
        "additionalProperties": False
    }
}
# maybe have an api_required vs database required
# if you're submitting the scraping request, you just need three entries but if it's a database entry, it should have them all listed?

# this format is just for submitted new data
new_data_schema = {
    "$schema": "https://json-schema.org/draft/2020-12",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {key:item for key, item in references_schema["items"]["properties"].items() if key in manual_fields},
        "required": required_fields, # the required ones should just be the things you need to scrape data
        "primaryKeys": ["dataset_id", "api_endpoint"],
        "additionalProperties": False
    }
}

# this format is just for the scraped_data.json file
new_data_schema = {
    "$schema": "https://json-schema.org/draft/2020-12",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {key:item for key, item in references_schema["items"]["properties"].items() if key in manual_fields + metadata_fields},
        "required": required_fields, #+ ['response','status','status_date'], # the required ones should just be the things you need to scrape data
        "primaryKeys": ["dataset_id", "api_endpoint"],
        "additionalProperties": False
    }
}

# i think we should make info_url required so people can look up info about the dataset

# see readme for descriptions for the keys
attributes_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "attribute_id": {"type": "string"},
            "dataset_id": {"type": "string"},
            "api_endpoint": {"type": "string","format":"uri"},
            "attribute_alias": {"type": "string"},
            "data_type": {"type": "string"},
            "unique_values": {
                "oneOf": [
                    {"type":"array","items":{"type":["string","number","boolean"]}},
                    {"type":"null"}
                ]
            },
            "unique_count": {
                "oneOf": [
                    {"type": "number","minimum":0},
                    {"type": "null"}
                ]
            },
            "null_percent": {
                "oneOf": [
                    {"type": "number","minimum":0},
                    {"type": "null"}
                ]
            },
            "min": {"type":["number","string","null"]}, # string needed for dates
            "max": {"type":["number","string","null"]},
            "avg": {"type":["number","string","null"]},
            "sum": {"type":["number","null"]},
        },
        "required": ["attribute_id", "dataset_id", "api_endpoint"],
        "primaryKeys": ["attribute_id", "dataset_id", "api_endpoint"],
        "additionalProperties": False
    }
}

# unique id check
# takes in records and key or pair of keys that should be unique