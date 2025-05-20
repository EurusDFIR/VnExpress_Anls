from app import create_app, db
from app.models import Category

app = create_app()
with app.app_context():
    if not Category.query.filter(Category.name.ilike('Chưa phân loại')).first():
        cat = Category(name='Chưa phân loại', url='#', is_active=True)
        db.session.add(cat)
        db.session.commit()
        print("Đã thêm chuyên mục 'Chưa phân loại'")
    else:
        print("Đã có chuyên mục 'Chưa phân loại'")