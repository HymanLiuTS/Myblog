#! -*-coding:utf-8-*-
from markdown import markdown
import bleach
import hashlib
from app import db,log
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin,AnonymousUserMixin
from . import login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app,request
from datetime import datetime
from app.exceptions import ValidationError


class Permission:
    FOLLOW=0x01
    COMMENT=0x02
    WRITE_ARTICLES=0x04
    MODERATE_COMMENTS=0x08
    ADMINISTER=0x80

class Follow(db.Model):
    __tablename__='follows'
    follower_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    followed_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)

class Role(db.Model):
    __tablename__='roles'
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(64),unique=True)
    default = db.Column(db.Boolean,default=False,index=True)
    permissions=db.Column(db.Integer)
    #users反向引用User,调用该字段时会自动生成和角色关联的用户列表
    #backref会在User模型中生成一个字段role,表示用户的角色
    #lazy='dynamic'设置引用users字段时可使用过滤器:
    #   user_role.users.order_by(User.username).all()
    users=db.relationship('User',backref='role',lazy='dynamic')

    def __repr__(self):
        return '<Role %r>'% self.name
    
    @staticmethod
    def insert_roles():
        roles={
            'User':(Permission.FOLLOW|
                    Permission.COMMENT|
                    Permission.WRITE_ARTICLES,True),

            'Moderator':(
                    Permission.FOLLOW|
                    Permission.COMMENT|
                    Permission.WRITE_ARTICLES|
                    Permission.MODERATE_COMMENTS,False),

            'Administrator':(0xff,False),
            }

        for r in roles:
            role =Role.query.filter_by(name=r).first()
            if role is None:
                role=Role(name=r)
            role.permissions=roles[r][0]
            role.default=roles[r][1]
            db.session.add(role)
        db.session.commit()

class Postphoto():
    def __init__(self):
        self.id=0
        self.title=""
        self.author_name=""
        self.url=""
        self.timestamp=""
        self.read_cnt=0
        self.body=""

class User(UserMixin,db.Model):
    __tablename__='users'
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(64),unique=True,index=True)
    username=db.Column(db.String(64),unique=True,index=True)
    password_hash=db.Column(db.String(128))
    #设置roles表的role_id为外键.
    role_id=db.Column(db.Integer,db.ForeignKey('roles.id'))
    confirmed=db.Column(db.Boolean,default=False)
    name=db.Column(db.String(64))
    location=db.Column(db.String(64))
    about_me=db.Column(db.Text())
    member_since=db.Column(db.DateTime(),default=datetime.utcnow)
    last_seen=db.Column(db.DateTime(),default=datetime.utcnow)
    avatar_hash=db.Column(db.String(32))
    posts=db.relationship('Post',backref='author',lazy='dynamic')
    followed=db.relationship('Follow',
                             foreign_keys=[Follow.follower_id],
                              backref=db.backref('follower',lazy='joined'),
                              lazy='dynamic',
                              cascade='all,delete-orphan')
    followers=db.relationship('Follow',
                             foreign_keys=[Follow.followed_id],
                              backref=db.backref('followed',lazy='joined'),
                              lazy='dynamic',
                              cascade='all,delete-orphan')
    comments=db.relationship('Comment',backref='author',lazy='dynamic')

    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email==current_app.config['FLASKY_ADMIN']:
                self.role=Role.query.filter_by(permissions=0xff).first()
            else:
                self.role=Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash=hashlib.md5(
                    self.email.encode('utf-8')).hexdigest()
        self.follow(self)

    def __repr__(self):
        return '<User %r>'% self.username

    #修饰器，把方法做成属性
    @property
    def password(self):
        """
        将password定义成类的属性,并控制只可写不可读,当读取该属性时将会
        抛出异常.
        """
        raise AttributeError('passwoed is not a readable attribute')
    
    #设置属性的写
    @password.setter
    def password(self,password):
        """
        password的写入,写入密码时通过调用WerkZeug的generate_password_hash接
        口,生成hash值,然后存到password_hash字段.
        """
	self.password_hash=generate_password_hash(password)

    def verify_password(self,password):
        """
        传入用户输入的密码,调用WerkZeug的check_password_has接口进行比较
        """
	return check_password_hash(self.password_hash,password)

    def generate_confirmation_token(self,expiration=3600):
        """
        生成令牌,用于用户确认.    
        """
        s=Serializer(current_app.config['SECRET_KEY'],expiration)
        token = s.dumps({'confirm':self.id})
        log.write('self.id=',self.id)
        log.write('source token=',token)
        return token

    def confirm(self,token):
        """用户点击确认链接后,将进行令牌比较,以确认用户"""
        log.write('dest token=',token)
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            data=s.loads(token)
            log.write('data =',data)
        except:
            return False
        log.write('self.id=',self.id)
        if data.get('confirm')!=self.id:
            return False
        self.confirmed=True
        db.session.add(self)
        return True

    def can(self,permissions):
        return self.role is not None and\
                (self.role.permissions & permissions)==permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)
    
    def ping(self):
        self.last_seen=datetime.utcnow()
        db.session.add(self)

    def gravatar(self,size=100,default='identicon',rating='g'):
        if request.is_secure:
            url='https://secure.gravatar.com/avatar'
        else:
            url='http://www.gravatar.com/avatar'
        hash=self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
                url=url,hash=hash,size=size,default=default,rating=rating)

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     name=forgery_py.name.full_name(),
                     location=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def follow(self,user):
        if not self.is_following(user):
            f=Follow(follower=self,followed=user)
            db.session.add(f)

    def unfollow(self,user):
        f = self.followers.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self,user):
        return self.followed.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self,user):
        return self.followers.filter_by(follower_id=user.id).first() is not None
    
    @property
    def followed_posts(self):
        return Post.query.join(Follow,Follow.followed_id==Post.author_id).filter(Follow.follower_id==self.id)

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if user != None and (not user.is_following(user)):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def generate_auth_token(self,expiration):
        s=Serializer(current_app.config['SECRET_KEY'],
                expires_in=expiration)
        return s.dumps({'id':self.id})

    @staticmethod
    def vertify_auth_token(token):
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            data=s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def to_json(self):
        json_user={
                'url':url_for('api.get_post',id=self.id,_external=True),
                'username':self.username,
                'member_since':self.member_since,
                'last_seen':self.last_seen,
                'posts':url_for('api.get_user_followed_posts',id=self.id,_external=True),
                'post_count':self.posts.count()
                }
        return json_user

    #定义未注册用户对应的user对象
    @staticmethod
    def insert_stranger():
        u = User(id=0,email='695970775@qq.com',username='Anu')
        db.session.add(u)

class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user=AnonymousUser
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):
    __tablename__='posts'
    id=db.Column(db.Integer,primary_key=True)
    img_url=db.Column(db.Text)
    title=db.Column(db.Text)
    body=db.Column(db.Text)
    body_html=db.Column(db.Text)
    timestamp=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    author_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    comments=db.relationship('Comment',backref='post',lazy='dynamic')
    group=db.Column(db.Text)
    tag=db.Column(db.Text)
    read_cnt=db.Column(db.Integer)
    recommend=db.Column(db.Integer)
    last_recommend_time=db.Column(db.DateTime)
    last_comment_time=db.Column(db.DateTime)

    @staticmethod
    def generate_fake(count=100):
        from random import seed,randint
        import forgery_py
        seed()
        user_count=User.query.count()
        for i in range(count):
            u=User.query.offset(randint(0,user_count-1)).first()
            p=Post(body=forgery_py.lorem_ipsum.sentences(randint(1,3)),
                   timestamp=forgery_py.date.date(True),
                   author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body_html(target,value,oldvalue,initiator):
        allowed_tags=['p']
        target.body=bleach.linkify(bleach.clean(markdown(value,output_format='html'),tags=allowed_tags,strip=True))

    def to_json(self):
        json_post={
                'url':url_for('api.get_post',id=self.id,_external=True),
                'body':self.body,
                'body_html':self.body_html,
                'timstamp':self.timestamp,
                'author':url_for('api.get_user',id=self.author_id,_external=True),
                'comments':url_for('api.get_post_comments',id=self.id,_external=True),
                'comment_count':self.comments.count()
                }
        return json_post

    @staticmethod
    def from_json(json_post):
        body=json_post.get('body')
        if body is None or body=='':
            raise ValidationError('post does not have a body')
        return Post(body=body)

db.event.listen(Post.body_html,'set',Post.on_changed_body_html)


class Comment(db.Model):
    __tablename__='comments'
    id=db.Column(db.Integer,primary_key=True)
    body=db.Column(db.Text)
    body_html=db.Column(db.Text)
    timestamp=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    disabled=db.Column(db.Boolean)
    author_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id=db.Column(db.Integer,db.ForeignKey('posts.id'))
    floor_number=db.Column(db.Integer)
    stranger_name=db.Column(db.Text)
    stranger_email=db.Column(db.Text)
    stranger_img_url=db.Column(db.Text)

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags=['a','abbr','acronym','b','code','em','i','strong']
        target.body_html=bleach.clean(markdown(value,output_format='html'),
                tags=allowed_tags,strip=True)

class  RunningInfo(db.Model):
    __tablename__='runninginfo'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)
    vistors = db.Column(db.Integer)

class Tag(db.Model):
    __tablename__='tags'
    id=db.Column(db.Integer,primary_key=True)
    tag_name=db.Column(db.Text)
    posts_count=db.Column(db.Integer)
    group_id=db.Column(db.Integer)

    @staticmethod
    def insert_tags():
        tags={
            '网络编程':(0,1),
            'web前端': (0,1),
            'C/C++': (0,1),
            'C#': (0,1),
            'Python': (0,1),
            '数据库': (0,1),
            'Linux': (0,1),
            'VC++': (0,1),
            '其它': (0,1),
            '生活随笔': (0,2),
            '行万里路': (0,2),
            '瀚海拾舟':  (0,2),
            '其它':  (0,2)
        }

        for t in tags:
            tag = Tag.query.filter_by(tag_name=t.decode('utf8')).first()
            if tag==None:
                tag=Tag(tag_name=t.decode('utf8'))
                tag.posts_count=tags[t][0]
            tag.group_id=tags[t][1]
            db.session.add(tag)
        db.session.commit()

class Group(db.Model):
    __tablename__='groups'
    group_id = db.Column(db.Integer, primary_key=True)
    group_name=db.Column(db.Text)

    @staticmethod
    def insert_groups():
        groups=('技术笔记','程序人生')
        for g in groups:
            group=Group.query.filter_by(group_name=g.decode('utf8')).first()
            if group==None:
                group=Group(group_name=g.decode('utf8'))
            db.session.add(group)
        db.session.commit()

	
class Visitor(db.Model):
    __tablename__='vistors'
    visitor_id=db.Column(db.Integer,primary_key=True)
    visitor_ip=db.Column(db.Text)
    first_visit_time=db.Column(db.DateTime,default=datetime.utcnow())
    last_visit_time=db.Column(db.DateTime,default=datetime.utcnow())
    visit_counts=db.Column(db.Integer,default=0)





