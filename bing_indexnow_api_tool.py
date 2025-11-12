
import requests
import configparser

def get_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def submit_urls(urls):
    config = get_config()
    api_key = config['BING']['API_KEY']
    key_location = config['BING']['KEY_LOCATION']
    site_url = config['PELICAN']['SITE_URL']

    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    data = {
        "host": site_url,
        "key": api_key,
        "keyLocation": key_location,
        "urlList": urls
    }

    response = requests.post('https://api.indexnow.org/IndexNow', headers=headers, json=data)

    return response.status_code, response.text

if __name__ == '__main__':
    import sys
    urls_to_submit = sys.argv[1:]
    if not urls_to_submit:
        print("Usage: python bing_indexnow_api_tool.py <url1> <url2> ...")
    else:
        status_code, response_text = submit_urls(urls_to_submit)
        print(f"Status Code: {status_code}")
        print(f"Response: {response_text}")
