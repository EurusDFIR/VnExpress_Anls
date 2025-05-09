import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


url = 'https://quotes.toscrape.com/'

headers ={ 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
}
 
try:
    print(f"dang gui request den: {url}")
    response = requests.get(url,headers=headers)
    response.raise_for_status() # kiem tra loi http
    print(f"request thanh cong! status code: {response.status_code}")

    html_content = response.text
    print(html_content[:5000])

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


#parse html tag after get data html Structure
if html_content:
    print("\n start to parse HTML...")
    soup = BeautifulSoup(html_content,'html.parser')

    #tim block quote
    quote_blocks = soup.find_all('div',class_='quote')
    print(f"tim thay {len(quote_blocks)} khoi trich dan")

    if not quote_blocks:
        print("khong tim thay khoi trich dan nao. Kiem tra lai selector HTML HOac noi dung trang web")
    else:
        for index, block in enumerate(quote_blocks):
            print(f"\n --- trich dan # {index + 1} ---")

            quote_text_tag = block.find('span',class_='text')
            if quote_text_tag:
                quote_text = quote_text_tag.get_text(strip=True)
                print(f"cau trich dan: {quote_text}")
            else:
                print(" khong tim thay the chua cau trich dan trong khoi nay")

            #3. trich xuat ten tac gia
            author_tag = block.find('small', class_='author')
            if author_tag:
                author_name = author_tag.get_text(strip=True)
                print(f" tac gia: {author_name}")
            else:
                print("khong tim thay the chua ten tac gia trong khoi nay. ")

            #4. trich xuat tag
            tags_tag = block.find('a', class_='tag')
            if tags_tag:
                tags_name = tags_tag.get_text(strip=True)
                print(tags_name)
            else:
                print('khong tim thay the tags')
else:
    print("khong co noi dung HTML de phan tich. kiem tra lai")      

