from app import create_app
from app.models import Category, Article

app = create_app()
app.app_context().push()

bongda = Category.query.filter(Category.name.ilike("bóng đá")).first()
print("bongda =", bongda)
if bongda:
    print("bongda.id =", bongda.id)
    articles = Article.query.filter_by(category_id=bongda.id).order_by(Article.id.desc()).limit(10).all()
    print("Số bài viết thuộc chuyên mục Bóng đá:", len(articles))
    for a in articles:
        print(a.id, a.title, a.category_id, a.category.name)
else:
    print("Không tìm thấy chuyên mục Bóng đá")