import requests

url = 'https://vnexpress.net/nhung-yeu-to-ngan-chien-tranh-tong-luc-an-do-pakistan-4883066.html'
headers = {
     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    html_content = response.text
    print(html_content[:100000])
    
except requests.exceptions.HTTPError as errh:
    print(f"Http Error: {errh}")
except requests.exceptions.ConnectionError as errc:
    print(f"Error Connecting: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"Error Timeout Error: {errt}")
