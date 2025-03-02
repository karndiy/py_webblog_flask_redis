from flask import Blueprint, render_template, request, redirect, url_for, g
from .models import Post, Comment, User, Tag, post_tags
from . import db, redis_client
from .forms import PostForm, CommentForm
from functools import wraps
import jwt
import os
from datetime import datetime
import redis.exceptions

bp = Blueprint('main', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization') or request.cookies.get('token')
        if token and token.startswith('Bearer '):
            token = token.split(' ')[1]
        if token:
            try:
                data = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
                g.current_user = User.query.get(data['user_id'])
            except:
                g.current_user = None
        else:
            g.current_user = None
        return f(*args, **kwargs)
    return decorated

def process_tags(tag_string):
    """Convert comma-separated tag string to Tag objects."""
    if not tag_string:
        return []
    tag_names = [name.strip().lower() for name in tag_string.split(',') if name.strip()]
    tags = []
    for name in tag_names:
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
        tags.append(tag)
    return tags

@bp.route('/')
@token_required
def index():
    #posts = Post.query.all()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, current_user=g.get('current_user'))

@bp.route('/post/<int:id>')
@token_required
def view_post(id):
    post = Post.query.get_or_404(id)
    comments = Comment.query.filter_by(post_id=id).all()
    form = CommentForm()
    return render_template('post.html', post=post, comments=comments, form=form, current_user=g.get('current_user'))

@bp.route('/create', methods=['GET', 'POST'])
@token_required
def create_post():
    if not g.current_user:
        return redirect(url_for('auth.login'))
    form = PostForm()
    if request.method == 'POST' and form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            user_id=g.current_user.id,
            scheduled_at=form.scheduled_at.data if form.scheduled_at.data else None
        )
        post.tags = process_tags(form.tags.data)
        db.session.add(post)
        db.session.commit()
        
        if form.scheduled_at.data:
            try:
                redis_client.set(f"post:{post.id}", post.content)
            except redis.exceptions.ConnectionError:
                print("Warning: Could not connect to Redis. Post scheduled but not stored in Redis.")
            
        return redirect(url_for('main.index'))
    return render_template('create_post.html', form=form, current_user=g.get('current_user'))

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@token_required
def edit_post(id):
    if not g.current_user:
        return redirect(url_for('auth.login'))
    post = Post.query.get_or_404(id)
    if g.current_user.id != post.user_id:
        return redirect(url_for('main.index'))
    form = PostForm(obj=post)
    if request.method == 'GET':
        form.tags.data = ', '.join(tag.name for tag in post.tags)
    if request.method == 'POST' and form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.scheduled_at = form.scheduled_at.data if form.scheduled_at.data else None
        post.tags = process_tags(form.tags.data)
        db.session.commit()
        if form.scheduled_at.data:
            try:
                redis_client.set(f"post:{post.id}", post.content)
            except redis.exceptions.ConnectionError:
                print("Warning: Could not connect to Redis. Post scheduled but not stored in Redis.")
        return redirect(url_for('main.index'))
    return render_template('create_post.html', form=form, post=post, current_user=g.get('current_user'))

@bp.route('/delete/<int:id>')
@token_required
def delete_post(id):
    if not g.current_user:
        return redirect(url_for('auth.login'))
    post = Post.query.get_or_404(id)
    if g.current_user.id != post.user_id:
        return redirect(url_for('main.index'))
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/search')
@token_required
def search():
    query = request.args.get('q')
    if not query:
        posts = Post.query.all()  # Return all posts if no query
    else:
        # Search in title, content, and tags
        posts = Post.query.join(post_tags, isouter=True).join(Tag, isouter=True).filter(
            (Post.title.contains(query)) |
            (Post.content.contains(query)) |
            (Tag.name.contains(query))
        ).distinct().all()
    return render_template('index.html', posts=posts, current_user=g.get('current_user'))

@bp.route('/comment/<int:post_id>', methods=['POST'])
@token_required
def add_comment(post_id):
    if not g.current_user:
        return redirect(url_for('auth.login'))
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for('main.view_post', id=post_id))