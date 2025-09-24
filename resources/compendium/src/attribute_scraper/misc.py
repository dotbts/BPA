##################### Misc #####################

# the el paso website didn't like the request coming from a non-browser
# https://stackoverflow.com/questions/65389552/python-requests-not-working-for-a-website-api-but-works-in-browser-chrome
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'} # This is chrome, you can set whatever browser you like

# dictionary for holding error messages for debugging purposes
from collections import defaultdict
error_logger = defaultdict(list)

def log_error(api_endpoint, step, response):
    '''
    Log an error message for debugging purposes.
    '''
    # error_logger[api_endpoint] = utils.error_logger[api_endpoint] + [{'step':'get_unique_values','response':response}]
    error_logger[api_endpoint].append({
        'step': step,
        'response': response
    })