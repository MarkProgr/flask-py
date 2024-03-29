import os
import secrets
from PIL import Image
from flask import render_template, flash, redirect, url_for, request, abort
from app import app, bcrypt, db, mail
from app.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                       PostForm, RequestResetForm, ResetPasswordForm)
from app.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.route('/')
@app.route('/home')
def index():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=2, page=page, error_out=True)
    return render_template('index.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Successfully created for {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/account', methods=['POST', 'GET'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.image.data:
            image_file = save_image(form.image.data)
            current_user.image_file = image_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template(
        'account.html', image_file=image_file, form=form,
    )


def save_image(image):
    random_hex = secrets.token_hex(8)
    _, file_ext = os.path.splitext(image.filename)
    image_filename = random_hex + file_ext
    image_path = os.path.join(app.root_path, 'static/profile_pics', image_filename)

    shorten_image_size(image).save(image_path)

    return image_filename


def shorten_image_size(image):
    output_size = (125, 125)
    i = Image.open(image)
    i.thumbnail(output_size)
    return i


@app.route('/posts', methods=['GET', 'POST'])
@login_required
def store_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Created', 'success')
        return redirect(url_for('index'))
    return render_template(
        'posts/create.html', form=form, legend='Create Post'
    )


@app.route('/posts/<int:post_id>', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Updated', 'success')
        return redirect(url_for('index'))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('posts/create.html', form=form,
                           legend='Update Post')


@app.route('/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def destroy_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Deleted', 'success')
    return redirect(url_for('index'))


@app.route('/user/<string:username>', methods=['GET'])
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = (Post.query.filter_by(author=user)
             .order_by(Post.date_posted.desc())
             .paginate(per_page=2, page=page, error_out=True))
    return render_template('posts/user_posts.html', posts=posts, user=user)


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Email has been sent to reset password', 'success')
        return redirect(url_for('login'))
    return render_template('reset/reset_request.html', form=form)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset', sender='noreply@demo.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following: 
        { url_for('reset_token', token=token, _external=True) }'''
    mail.send(msg)


@app.route('/reset-password/<string:token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid token', 'danger')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Successfully changed password', 'success')
        return redirect(url_for('login'))
    return render_template('reset/reset_token.html', form=form)
