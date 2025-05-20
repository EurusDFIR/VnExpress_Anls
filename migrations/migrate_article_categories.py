# Script to migrate old articles to use category_id (for filtering and display)
from app import create_app, db
from app.models import Article, Category

app = create_app()

with app.app_context():
    # Optional: If you still have the old string field, use it. Otherwise, all old articles will be set to 'Chưa phân loại'.
    default_cat = Category.query.filter(Category.name.ilike('Chưa phân loại')).first()
    default_cat_id = default_cat.id if default_cat else None
    updated = 0
    for article in Article.query.filter(Article.category_id == None).all():
        # If you still have article.category (string), try to match
        cat_name = getattr(article, 'category', None)
        if cat_name:
            cat = Category.query.filter(Category.name == cat_name).first()
            if cat:
                article.category_id = cat.id
            elif default_cat_id:
                article.category_id = default_cat_id
        elif default_cat_id:
            article.category_id = default_cat_id
        updated += 1
    db.session.commit()
    print(f'Done. Updated {updated} articles.')
