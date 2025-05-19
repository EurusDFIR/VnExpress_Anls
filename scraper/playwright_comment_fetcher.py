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
    import time
    t_start = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        # Chặn thêm các request JS động, analytics, ads để tăng tốc
        async def block_resource(route):
            url = route.request.url
            if route.request.resource_type in ["image", "stylesheet", "font", "media"] or any(x in url for x in ["googletagmanager", "google-analytics", "doubleclick", "scorecardresearch", "cdn.ampproject.org", "quangcao", "vads"]):
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_resource)
        # Tăng timeout tải trang lên 40s, giữ wait_for_selector ở 15s
        # Sử dụng wait_until="domcontentloaded" để tránh bị kẹt khi trang tải chậm tài nguyên ngoài
        await page.goto(article_url, timeout=40000, wait_until="domcontentloaded")
        # Chờ selector tồn tại (attached), sau đó scroll nhiều lần để kích hoạt bình luận (lazy load)
        await page.wait_for_selector('#box_comment_vne', timeout=15000, state='attached')
        for _ in range(10):
            comment_box = await page.query_selector('#box_comment_vne')
            is_visible = await comment_box.is_visible() if comment_box else False
            if is_visible:
                break
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(400)
        else:
            print(f"Khối bình luận tồn tại nhưng bị ẩn ở {article_url} dù đã scroll. Có thể bài viết đã tắt bình luận hoặc bị kiểm duyệt.")
            await browser.close()
            return None
        print("Playwright: Trang đã tải, khối comment chính đã xuất hiện.")
        t_after_load = time.time()
        print(f"[DEBUG] Thời gian tải trang và khối comment: {t_after_load-t_start:.2f}s")
        # Click 'Xem thêm ý kiến' nhiều lần cho đến khi không còn nút nào nữa
        for i in range(max_load_more_clicks):
            try:
                # Ẩn các overlay phổ biến có thể che nút (sticky header, player, popup)
                await page.evaluate('''
                    let sticky = document.querySelector('.sticky');
                    if (sticky) sticky.style.display = 'none';
                    let player = document.querySelector('.section-player-pin');
                    if (player) player.style.display = 'none';
                    let popup = document.querySelector('.vne-popup');
                    if (popup) popup.style.display = 'none';
                ''')
                # Cuộn xuống cuối trang để hiện nút 'Xem thêm ý kiến' nếu bị ẩn
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # Đếm số lượng bình luận trước khi click
                before_count = await page.eval_on_selector_all('#list_comment > div.comment_item', 'els => els.length')
                btn = await page.query_selector('#show_more_coment')
                if btn:
                    comment_items = await page.query_selector_all('#list_comment > div.comment_item')
                    total_comments_loaded = len(comment_items)
                    print(f"Playwright: Đã tải {total_comments_loaded} bình luận.")
                    print(f"Playwright: Click 'Xem thêm ý kiến' lần {i+1}/{max_load_more_clicks}")
                    # Scroll nút vào giữa màn hình trước khi click
                    await btn.evaluate("el => el.scrollIntoView({block: 'center'})")
                    try:
                        await btn.click(timeout=2000)
                    except Exception as e:
                        print(f"Playwright: Click thường lỗi, thử click bằng JS: {e}")
                        try:
                            await btn.evaluate("el => el.click()")
                        except Exception as e2:
                            print(f"Playwright: Click JS cũng lỗi: {e2}")
                            break
                    # Chờ cho đến khi số lượng bình luận tăng lên (tối đa 5s)
                    try:
                        await page.wait_for_function(f'document.querySelectorAll("#list_comment > div.comment_item").length > {before_count}', timeout=5000)
                    except Exception as e:
                        print(f"Playwright: Chờ số lượng bình luận tăng lên sau click 'Xem thêm' bị timeout: {e}")
                else:
                    print("Playwright: Không tìm thấy nút 'Xem thêm ý kiến'.")
                    break
            except Exception as e:
                print(f"Playwright: Lỗi khi click 'Xem thêm ý kiến': {e}")
                break
        t_after_loadmore = time.time()
        print(f"[DEBUG] Thời gian click 'Xem thêm ý kiến': {t_after_loadmore-t_after_load:.2f}s")
        # Lặp nhiều vòng cho đến khi không còn nút 'Xem trả lời' nào xuất hiện nữa (tối đa 10 vòng)
        max_reply_rounds = 10
        for reply_round in range(max_reply_rounds):
            reply_buttons = await page.query_selector_all('p.count-reply a.view_all_reply')
            if not reply_buttons:
                print(f"Playwright: Không còn nút 'Xem trả lời' ở vòng {reply_round+1}.")
                break
            print(f"Playwright: Click {len(reply_buttons)} nút 'Xem trả lời' (song song) ở vòng {reply_round+1}.")
            before_btn_count = len(reply_buttons)
            tasks = [btn.click() for btn in reply_buttons]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Chờ cho đến khi số lượng nút 'Xem trả lời' giảm đi (tối đa 2s)
            try:
                await page.wait_for_function(
                    f'document.querySelectorAll("p.count-reply a.view_all_reply").length < {before_btn_count}',
                    timeout=1000
                )
            except Exception as e:
                print(f"Playwright: Chờ số lượng nút 'Xem trả lời' giảm đi bị timeout: {e}")
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    if "not attached to the DOM" in str(res):
                        continue
                
                    print(f"Playwright: Lỗi khi click 'Xem trả lời' (song song) nút {i+1}: {res}")
        t_after_reply = time.time()
        print(f"[DEBUG] Thời gian click tất cả 'Xem trả lời': {t_after_reply-t_after_loadmore:.2f}s")
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
        t_end = time.time()
        print(f"[DEBUG] Tổng thời gian Playwright scrape bình luận: {t_end-t_start:.2f}s")
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

