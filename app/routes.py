from flask import Blueprint, render_template, request, redirect, url_for, g
from .models import Post, Comment, User
from . import db, redis_client
from .forms import PostForm, CommentForm
from functools import wraps
import jwt
import os
from datetime import datetime

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

@bp.route('/')
@token_required
def index():
    posts = Post.query.all()
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
        db.session.add(post)
        db.session.commit()
        
        if form.scheduled_at.data:
            redis_client.set(f"post:{post.id}", post.content)
            
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
    if request.method == 'POST' and form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.scheduled_at = form.scheduled_at.data if form.scheduled_at.data else None
        db.session.commit()
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
    posts = Post.query.filter(Post.title.contains(query) | Post.content.contains(query)).all()
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