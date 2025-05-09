import requests
from bs4 import BeautifulSoup


url = 'https://books.toscrape.com/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'

}


try:
    print(f"dang gui request den: {url}")
    response = requests.get(url,headers=headers)
    response.raise_for_status() # kiem tra loi http
    print(f"request thanh cong! status code: {response.status_code}")

    html_content = response.text
    print(html_content[:500000])

except requests.exceptions.HTTPError as errh:
    print(f"loi http: {errh}")
except requests.exceptions.ConnectionError as errc:
    print(f"loi ket noi: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"loi time out: {errt}") 
except requests.exceptions.RequestException as err:
    print(f"loi request khac: {err}")
except Exception as e:
    print(f"loi khong xac dinh: {e}")


if html_content:
    print("\n start to parse HTML...")
    soup = BeautifulSoup(html_content,'html.parser')

    #tim block quote
    book_block = soup.find_all('article',class_='product_pod')
    print(f"tim thay {len(book_block)} khoi trich dan")

    for index, block in enumerate(book_block[:20]):
        title_tag = block.find('h3')
        if title_tag:
            link_tag = title_tag.find('a')
            if link_tag:
                title_text = link_tag.get_text(strip=True)
                print(f"Title #{index +1}: {title_text}")
            else:
                print("khong tim thay the a")
        else:
            print('khong tim thay the h3')
        rating_tag=block.find('p',class_ = 'star-rating')
        if rating_tag:
            rating_classes = rating_tag.get('class')
            if len(rating_classes) >1:

                rating_text = rating_tag.get_text(strip=True)
                print(f"rating #{index +1}: {rating_text}")
            
