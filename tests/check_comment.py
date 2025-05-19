from app import create_app, db
from app.models import Comment

app = create_app()
with app.app_context():
    # Kiểm tra comment cụ thể
    comment = Comment.query.filter_by(comment_api_id='49451653').first()
    print('Comment found:', comment is not None)
    
    # In thông tin chi tiết nếu tìm thấy
    if comment:
        print('\nComment details:')
        print(f'ID: {comment.id}')
        print(f'Article ID: {comment.article_id}')
        print(f'User name: {comment.user_name}')
        print(f'Comment text: {comment.comment_text}')
        print(f'Likes count: {comment.likes_count}')
        print(f'Comment date: {comment.comment_date_str}')
    
    # In tổng số comment trong database
    total_comments = Comment.query.count()
    print(f'\nTotal comments in database: {total_comments}') 