from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, current_user, login_required
from flask_security.forms import RegisterForm
from wtforms import StringField, TextAreaField, SubmitField
from flask_wtf import FlaskForm
from datetime import datetime


# Configuring Flask App
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///forum.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'mysecret'
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_PASSWORD_SALT'] = 'somesaltfortheforum'
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False

# Creating Database Instance
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Create DB Roles for user implementation
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

# DB Schemas
class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(250))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())

    # Back Refs
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('user', lazy='dynamic'))
    threads = db.relationship('Thread', backref='user', lazy='dynamic')
    replies = db.relationship('Reply', backref='user', lazy='dynamic')


class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50))
    description = db.Column(db.String(300))
    date_created = db.Column(db.DateTime())
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Back Refs
    replies = db.relationship('Reply', backref='thread', lazy='dynamic')

    def get_replies(self):
        return Reply.query.filter_by(thread_id=self.id).all()

    


class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(300))
    date_created = db.Column(db.DateTime())


# App Forms
class ExtendRegisterForm(RegisterForm):
    name = StringField("Name")
    username = StringField("Username")

class NewThread(FlaskForm):
    title = StringField("Title")
    description = StringField("Description")
    submit = SubmitField("Submit")

class NewReply(FlaskForm):
    message = StringField("Message")
    submit = SubmitField("Submit")


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, register_form=ExtendRegisterForm)

@app.route('/', methods=['GET', 'POST'])
@app.route('/reply/<int:thread_id>', methods=['GET', 'POST'])
def index(thread_id=None):
    thread_form = NewThread()
    reply_form = NewReply()
    if reply_form.submit.data and reply_form.validate() and thread_id != None:
        print("from validate reply")
        thread = Thread.query.get(int(thread_id))
        reply = Reply(
            user_id=current_user.id, 
            message=reply_form.message.data, 
            date_created=datetime.now())
        thread.replies.append(reply)
        db.session.commit()
        return redirect('/')

    elif thread_form.submit and thread_form.validate():
        print("from validate thread")
        new_thread = Thread(
            title=thread_form.title.data, 
            description=thread_form.description.data, 
            date_created = datetime.now(), 
            created_by=current_user.id)
        db.session.add(new_thread)
        db.session.commit()
        return redirect(url_for('index'))

    threads = Thread.query.all()

    return render_template('index.html', reply_form=reply_form, \
        thread_form=thread_form, threads=threads, current_user=current_user)

# @app.route('/reply/<int:thread_id>', methods=['GET', 'POST'])
# def add_reply(thread_id):
#     thread = Thread.query.get(int(thread_id))

#     if form.validate_on_submit():
#         reply = Reply(user_id=current_user.id, message=form.message.data, date_created=datetime.now())
#         thread.replies.append(reply)
#         db.session.commit()
#         return render_template('index.html', reply_form=reply_form, \
#         thread_form=thread_form, threads=threads, current_user=current_user)


@app.route('/delete/reply/<int:thread_id>&<int:reply_id>', methods=['GET', 'POST'])
def delete_reply(thread_id, reply_id):
    reply_to_delete = Reply.query.get_or_404(reply_id)
    try:
        db.session.delete(reply_to_delete)
        db.session.commit()
        return redirect(url_for('/thread/', thread_id=thread_id))
    except:
        return "There was a problem deleting the reply"

@app.route('/delete/thread/<int:id>')
def delete_thread(id):
    thread_to_delete = Thread.query.get_or_404(id)
    try:
        for reply in thread_to_delete.replies:
            db.session.delete(reply)
        db.session.delete(thread_to_delete)
        db.session.commit()
        return redirect(url_for('index'))
    except:
        return "There was a problem deleting the thread"