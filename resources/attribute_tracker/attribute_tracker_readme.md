# Attribute Tracker
The `attributes.csv` and `references.csv` spreadsheets aggregate bike, pedestrian, and accessibility data from state, regional, and local government open data hubs by scraping ArcGIS REST or Socrata API endpoints. Note, not all of the datasets in `references.csv` have been scraped.

The purpose of this resource is to compile existing practices for tracking bicycle, pedestrian, and accessibility in geospatial databases. This resource serves as inspiration for developing the specification and for others in looking how to track attributes that might not be covered by the specification.

**These documents will be updated periodically as new data sources are added.**

## Attributes Table
The primary key is `(Attribute Alias, Dataset Alias)`.

| Column Name | Description |
| - | - |
| *Attribute Name |	Attribute name as it appears in the dataset |
| *Attribute Alias Name | Attribute alias name if available |
| *Data Type |	Data type used by Socrata / ESRI |
| *Unique Values |	Up to 20 unique values listed in ascending order |
| *Statistics |	Max, Min, Avg values if applicable |
| *Unique Counts |	Total number of unique values |
| *Null Percent |	Percent of rows that are null	 |
| Dataset Alias |	Foreign key referencing to the references sheet |
| Anything to the right of Dataset Alias |	These are columns added from the references sheet |

*Values may have been scraped from ArcGIS REST or Socrata

## References Table
The primary key is `Dataset Alias`.

| Column Name | Description |
| - | - |
| Dataset Alias |	Unique value used to name the dataset |
| *Dataset Name |	Actual name of the dataset as stored  |
| *Description |	Description of the dataset if available |
| *Entity |	The organization that publishes the dataset |
| State	| State name or country name if outside of United States |
| Geographic area |	General location city/county/metro area that the dataset covers |
| How acquired | All datasets were acquired through open data portals |
| *Last updated |	Date the dataset was last updated |
| *Record Count |	Number of rows in the dataset |
| *Field Count |	Number of columns/fields in the dataset |
| Info URL |	URL for information/overview of the dataset |
| REST URL |	ESRI Rest API Endpoint if available |
| Socrata URL |	Socrata API Endpoint if available |
| Download URL |	Download URL if available |

*Values may have been scraped from ArcGIS REST or Socrata

## Contributing new datasets
Are you aware of an authoritative open dataset that isn't in the attribute tracker that supports ArcGIS REST API or Socrata queries? Please email tanner.passmore.ctr@dot.gov and send me a link to the data so that I can add it.
