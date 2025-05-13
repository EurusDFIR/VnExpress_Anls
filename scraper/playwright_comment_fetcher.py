# scraper/playwright_comment_fetcher.py
# Playwright version of comment HTML fetcher for VnExpress

import asyncio
from playwright.async_api import async_playwright

def get_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        return asyncio.new_event_loop()

def save_html_to_file(html, filename="debug_comment_playwright.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

async def fetch_comments_html_with_playwright(article_url, max_load_more_clicks=10, max_reply_clicks_per_comment=3, debug_save=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Chặn tải ảnh, font, css để tăng tốc (chỉ cho khối bình luận, không ảnh bài báo)
        async def block_resource(route):
            if route.request.resource_type in ["image", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_resource)
        await page.goto(article_url, timeout=60000)
        # Chờ khối bình luận xuất hiện
        await page.wait_for_selector('#box_comment_vne', timeout=30000)
        print("Playwright: Trang đã tải, khối comment chính đã xuất hiện.")
        # Click 'Xem thêm ý kiến' nhiều lần (giới hạn để lấy tối đa ~100 bình luận)
        max_comments = 100
        total_comments_loaded = 0
        for i in range(max_load_more_clicks):
            try:
                btn = await page.query_selector('#show_more_coment')
                if btn:
                    # Đếm số bình luận hiện tại
                    comment_items = await page.query_selector_all('#list_comment > div.comment_item')
                    total_comments_loaded = len(comment_items)
                    print(f"Playwright: Đã tải {total_comments_loaded} bình luận.")
                    if total_comments_loaded >= max_comments:
                        print(f"Playwright: Đã đạt giới hạn {max_comments} bình luận.")
                        break
                    print(f"Playwright: Click 'Xem thêm ý kiến' lần {i+1}/{max_load_more_clicks}")
                    await btn.click()
                    await page.wait_for_timeout(600)
                else:
                    print("Playwright: Không tìm thấy nút 'Xem thêm ý kiến'.")
                    break
            except Exception as e:
                print(f"Playwright: Lỗi khi click 'Xem thêm ý kiến': {e}")
                break
        print("Playwright: Đã click xong 'Xem thêm ý kiến'.")
        # Tối ưu: Click tất cả nút 'Xem trả lời' cho mỗi bình luận gốc
        for reply_round in range(max_reply_clicks_per_comment):
            reply_buttons = await page.query_selector_all('p.count-reply a.view_all_reply')
            if not reply_buttons:
                print(f"Playwright: Không còn nút 'Xem trả lời' ở vòng {reply_round+1}.")
                break
            print(f"Playwright: Click {len(reply_buttons)} nút 'Xem trả lời' ở vòng {reply_round+1}.")
            for btn in reply_buttons:
                try:
                    await btn.click()
                    await page.wait_for_timeout(1200)
                except Exception as e:
                    print(f"Playwright: Lỗi khi click 'Xem trả lời': {e}")
        print("Playwright: Đã click xong tất cả nút 'Xem trả lời'.")
        # Lấy HTML của khối bình luận
        try:
            comment_html = await page.inner_html('#box_comment')
            if debug_save:
                save_html_to_file(comment_html)
            print("Playwright: Đã lấy HTML của khối bình luận.")
        except Exception as e:
            print(f"Playwright: Lỗi khi lấy HTML khối bình luận: {e}")
            comment_html = None
        await browser.close()
        return comment_html

def fetch_comments_html_sync(article_url, max_load_more_clicks=10, max_reply_clicks_per_comment=3, debug_save=False):
    loop = get_event_loop()
    return loop.run_until_complete(
        fetch_comments_html_with_playwright(
            article_url,
            max_load_more_clicks=max_load_more_clicks,
            max_reply_clicks_per_comment=max_reply_clicks_per_comment,
            debug_save=debug_save
        )
    )

# Example usage (for testing):
# html = fetch_comments_html_sync('https://vnexpress.net/...')
# print(html)
