import flask_login
from flask import Blueprint, render_template, flash, url_for, redirect
from config import db, Post, roles_required
from posts.forms import PostForm
from sqlalchemy import desc
from flask_login import login_required

posts_bp = Blueprint('posts', __name__, template_folder='templates')

@posts_bp.route('/create', methods=('GET', 'POST'))
@login_required
@roles_required("end_user")
def create():
    form = PostForm()
    if form.validate_on_submit():
        new_post = Post(userid=flask_login.current_user.get_id() ,title=form.title.data, body=form.body.data)

        db.session.add(new_post)
        db.session.commit()

        flash('Post created', category='success')
        return redirect(url_for('posts.posts'))
    return render_template('posts/create.html', form=form)

@posts_bp.route('/posts')
@login_required
@roles_required("end_user")
def posts():
    all_posts = Post.query.order_by(desc('id')).all()
    return render_template('posts/posts.html', posts=all_posts)

@posts_bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
@roles_required("end_user")
def update(id):
    post_to_update = Post.query.filter_by(id=id).first()
    if not post_to_update:
        return redirect(url_for('posts.posts'))

    if post_to_update.user.id == flask_login.current_user.id:
        form = PostForm()

        if form.validate_on_submit():
            post_to_update.update(title=form.title.data, body=form.body.data)

            flash('Post updated', category='success')
            return redirect(url_for('posts.posts'))

        form.title.data = post_to_update.title
        form.body.data = post_to_update.body
    else:
        flash('You may not update another User\'s post.', category='info')
        return redirect(url_for('posts.posts'))

    return render_template('posts/update.html', form=form)

@posts_bp.route('/<int:id>/delete')
@login_required
@roles_required("end_user")
def delete(id):
    post_to_delete = Post.query.filter_by(id=id).first()
    if not post_to_delete:
        return redirect(url_for('posts.posts'))
    if post_to_delete.user.id == flask_login.current_user.id:
        db.session.delete(post_to_delete)
        db.session.commit()
        flash('Post deleted', category='success')
    else:
        flash('You may not delete another User\'s post.', category='info')
    return redirect(url_for('posts.posts'))