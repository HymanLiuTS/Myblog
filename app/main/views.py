#coding:utf-8
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
from datetime import datetime
from flask import render_template,session,redirect,url_for,current_app,flash,request,make_response,send_from_directory,abort
from decorators import admin_required,permission_required
from . import main
from .forms import NameForm,EditProfileForm,EditProfileAdminForm,PostForm,CommentForm
from .. import db,moment
from ..models import User,Permission,Role,Post,Comment,Tag,Group,RunningInfo,Postphoto
from .. import mail
from flask_login import login_required,current_user
import os
import re
import json
from uploader import Uploader
from werkzeug import secure_filename
from sqlalchemy import or_,and_

@main.route('/',methods=['GET','POST'])
def index():
    #文章分页列表
    page=request.args.get('page',1,type=int)
    pagination=Post.query.order_by(Post.timestamp.desc()).paginate(
    page,per_page=current_app.config['FLASK_POSTS_PRE_PAGE'],
    error_out=False)
    posts=pagination.items
    if len(posts)==0:
        posts=None
    #文章总数
    post_counts=Post.query.count()
    #访问量和运行时间
    running_info=RunningInfo.query.first()
    vistors=running_info.vistors
    days=(datetime.utcnow()-running_info.timestamp).days
    #最新评论文章
    recent_comment_posts=Post.query.filter(Post.last_comment_time!=None).order_by(Post.last_comment_time.desc()).limit(8)
    recommend_post=Post.query.filter_by(recommend=1).order_by(Post.last_recommend_time.desc()).first()
    return render_template('index2.html',posts=posts,pagination=pagination,
                           post_counts=post_counts,recent_comment_posts=recent_comment_posts,
                           recommend_post=recommend_post,days=days,vistors=vistors,running_info=running_info)

@main.route('/<path>')
def today(path):
    base_dir = os.path.dirname(__name__)
    tfile=os.path.join(base_dir,path)
    if os.path.exists(tfile)==True and os.path.splitext(path)[1] in ('.html','.ico','.xml'):
        resp = make_response(open(os.path.join(base_dir, path)).read())
        resp.headers["Content-type"]="application/json;charset=UTF-8"
        return resp
    abort(404)

@main.route('/admin',methods=['GET','POST'])
@login_required
@admin_required
def for_admins_only():
    return "for administrator"

@main.route('/moderator')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def for_moderators_only():
    return "for comment moderators!"

@main.route('/user/<username>')
def user(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    #查询用户文章并按照时间戳降序排列
    posts=user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html',user=user,posts=posts)

@main.route('/edit-profile',methods=['GET','POST'])
@login_required
def edit_profile():
    form=EditProfileForm()
    if form.validate_on_submit():
        current_user.name=form.name.data
        current_user.location=form.location.data
        current_user.about_me=form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user',username=current_user.username))
    form.name.data=current_user.name
    form.location.data=current_user.location
    form.about_me.data=current_user.about_me
    return render_template('edit_profile.html',form=form)

@main.route('/edit-profile/<int:id>',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user=User.query.get_or_404(id)
    form=EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email=form.email.data
        user.username=form.username.data
        user.confirmed=form.confirmed.data
        user.role=Role.query.get(form.role.data)
        user.name=form.name.data
        user.location=form.location.data
        user.about_me=form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user',username=user.username))
    form.email.data=user.email
    form.username.data=user.username
    form.confirmed.data=user.role_id
    form.role.data=user.role_id
    form.name.data=user.name
    form.location.data=user.location
    form.about_me.data=user.about_me
    return render_template('edit_profile.html',form=form,user=user)

@main.route('/edit/<int:id>',methods=['GET','POST'])
@login_required
def edit(id):
    post=Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    if request.method=='POST':
        # 删除本地的引导图片
        img_path = './app/static/' + post.img_url
        if os.path.exists(img_path):
            os.remove(img_path)
        post.body_html = request.form['myContent']
        post.title = request.form['title']
        file = request.files['file']
        if file != None:
            current_app.config['UPLOAD_PATH'] = os.getcwd() + '/app/static/images/' + str(post.author_id) + '/'
            if os.path.exists(current_app.config['UPLOAD_PATH']) == False:
                os.makedirs(current_app.config['UPLOAD_PATH'])
            filename = secure_filename(file.filename)
            filename = generate_filename(filename)
            file.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
            file_url = uploaded_file(post.author_id,filename)
            post.img_url = file_url
        post.group = request.form['group']
        #处理tag
        if post.tag!=request.form['tag']:
            old_tag = Tag.query.filter(Tag.tag_name == post.tag).first()
            if old_tag!=None:
                old_tag.posts_count=old_tag.posts_count-1;
                db.session.add(old_tag);
            new_tag = Tag.query.filter(Tag.tag_name == request.form['tag']).first()
            if new_tag!=None:
                new_tag.posts_count = new_tag.posts_count + 1;
                post.tag = request.form['tag']
                db.session.add(new_tag);
        db.session.add(post)
        return redirect(url_for('.post',id=post.id))
    # 获取标签类别
    tectags = Tag.query.filter(Tag.group_id == 1).all()
    lifetags = Tag.query.filter(Tag.group_id == 2).all()
    # 获取组
    groups = Group.query.all()
    return render_template('edit_post.html',post=post,tectags=tectags,lifetags=lifetags,groups=groups)

@main.route('/delete/<int:id>',methods=['GET','POST'])
@login_required
def delete(id):
    post=Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    #删除标签
    tag = Tag.query.filter(Tag.tag_name == post.tag).first()
    if tag!=None:
        tag.posts_count=tag.posts_count-1
    #删除评论
    comments=Comment.query.filter(Comment.post_id==post.id).all()
    for comment in comments:
        db.session.delete(comment)
    # 删除本地的引导图片
    img_path = './app/static/' + post.img_url
    if os.path.exists(img_path):
        os.remove(img_path)
    db.session.delete(post)
    return redirect(url_for('.index'))

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user',username=username))
    current_user.follow(user)
    flash('You are now following %s.'%username)
    return redirect(url_for('.user',username=username))

@main.route('/followers/<username>')
def followers(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page',1,type=int)
    pagination=user.followers.paginate(
            page,per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
            error_out=False)
    follows=[{'user':item.follower,'timestamp':item.timestamp}
             for item in pagination.items]
    return render_template('followers.html',user=user,title='Followers of',
            endpoint='.followers',pagination=pagination,follows=follows)
            
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    #修改阅读次数
    if post.read_cnt==None:
        post.read_cnt=0;
    post.read_cnt=post.read_cnt+1;
    db.session.add(post)
    if request.method=='POST':
    #保存评论
        comment = None
        if current_user.is_authenticated:
            comment = Comment(body=request.form['comment-textarea'],
                              post=post,
                              author=current_user._get_current_object())
        else:
            now=datetime.utcnow()
            s=now.second/2
            img_url='/static/images/headerimgs/1/'+str(s)+'.jpg'
            comment = Comment(body=request.form['comment-textarea'],
                              post=post,
                              stranger_name=request.form['name-textarea'],
                              stranger_email=request.form['mail-textarea'],
                              stranger_img_url=img_url)
        last_comment=Comment.query.order_by(Comment.timestamp).filter_by(post_id=post.id).first()
        if last_comment.floor_number==None:
            last_comment.floor_number=0;
        comment.floor_number=last_comment.floor_number + 1;
        db.session.add(comment)
        post.last_comment_time = datetime.utcnow();
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    post_counts = Post.query.count()
    # 最新评论文章
    recent_comment_posts = Post.query.filter(Post.last_comment_time != None).order_by(Post.last_comment_time.desc()).limit(8)
    #推荐文章
    recmomend_posts=Post.query.order_by(Post.timestamp.desc()).filter_by(tag=post.tag).limit(10).all()
    if post in recmomend_posts:
        recmomend_posts.remove(post)
     # 访问量和运行时间
    running_info = RunningInfo.query.first()
    vistors = running_info.vistors
    days = (datetime.utcnow() - running_info.timestamp).days

    return render_template('post2.html', post=post,
                           comments=comments, pagination=pagination,
    post_counts = post_counts, recent_comment_posts = recent_comment_posts,
                           recmomend_posts=recmomend_posts,vistors=vistors,days=days)

import time,os
def generate_filename(filename):
    if filename.find('.')== False:
        return str(time.time())+ '.'+filename;#中文时secure_filename会只返回一个扩展名
    return str(time.time()) + os.path.splitext(filename)[1]

def uploaded_file(author_id,filename):
    #return url_for('static',filename='images/'+filename,_external=True)
    return 'images/' + str(author_id) + '/'+ filename

@main.route('/post/newpost',methods=['GET','POST'])
def newpost():
    """写新文章"""
    if request.method=='GET':
        #获取标签类别
        tectags=Tag.query.filter(Tag.group_id==1).all()
        lifetags=Tag.query.filter(Tag.group_id==2).all()
        #获取组
        groups=Group.query.all()
        return render_template('new_post.html',tectags=tectags,lifetags=lifetags,groups=groups)
    elif request.method=='POST':
        #构建新文章
        post=Post()
        post.body_html = request.form['myContent']
        post.title = request.form['title']
        post.author_id = current_user.id
        post.timestamp=datetime.utcnow();
        current_app.config['UPLOAD_PATH']=os.getcwd()+'/app/static/images/'+ str(post.author_id)+'/'
        if os.path.exists(current_app.config['UPLOAD_PATH'])==False:
            os.makedirs(current_app.config['UPLOAD_PATH'])
        file=request.files['file']
        filename=secure_filename(file.filename)
        filename=generate_filename(filename)
        file.save(os.path.join(current_app.config['UPLOAD_PATH'],filename))      
        file_url=uploaded_file(post.author_id,filename)
        post.img_url=file_url
        post.group=request.form['group']
        post.tag=request.form['tag']
        post.read_cnt=1
        post.recommend=0
        db.session.add(post)
        db.session.commit()
        #查询刚刚创建的新文章
        post=Post.query.filter_by(title=post.title).first()
        #更新tag
        tag=Tag.query.filter(Tag.tag_name==post.tag).first()
        tag.posts_count=tag.posts_count+1
        db.session.add(tag)
        return redirect(url_for('.post',id=post.id))
    

@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))

@main.route('/all')
@login_required
def show_all():
    resp=make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','',max_age=30*24*60*60)
    return resp

@main.route('/followed')
@login_required
def show_followed():
    resp=make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','1',max_age=30*24*60*60)
    return resp

@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page=request.args.get('page',1,type=int)
    pagination=Comment.query.order_by(Comment.timestamp.desc()).paginate(
            page,per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
            error_out=False)
    comments=pagination.items
    return render_template('moderate.html',comments=comments,pagination=pagination,page=page)
    
    
@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))

@main.route('/path')
def path():
    return os.path.join(current_app.static_folder,'ueditor','php','config.json')

@main.route('/upload/', methods=['GET', 'POST', 'OPTIONS'])
def upload():
    """UEditor文件上传接口

    config 配置文件
    result 返回结果
    """
    mimetype = 'application/json'
    result = {}
    action = request.args.get('action')

    # 解析JSON格式的配置文件
    with open(os.path.join(current_app.static_folder, 'ueditor', 'php',
                           'config.json')) as fp:
        try:
            # 删除 `/**/` 之间的注释
            CONFIG = json.loads(re.sub(r'\/\*.*\*\/', '', fp.read()))
        except:
            CONFIG = {}

    if action == 'config':
        # 初始化时，返回配置文件给客户端
        result = CONFIG

    elif action in ('uploadimage', 'uploadfile', 'uploadvideo'):
        # 图片、文件、视频上传
        if action == 'uploadimage':
            fieldName = CONFIG.get('imageFieldName')
            config = {
                "pathFormat": CONFIG['imagePathFormat'],
                "maxSize": CONFIG['imageMaxSize'],
                "allowFiles": CONFIG['imageAllowFiles']
            }
        elif action == 'uploadvideo':
            fieldName = CONFIG.get('videoFieldName')
            config = {
                "pathFormat": CONFIG['videoPathFormat'],
                "maxSize": CONFIG['videoMaxSize'],
                "allowFiles": CONFIG['videoAllowFiles']
            }
        else:
            fieldName = CONFIG.get('fileFieldName')
            config = {
                "pathFormat": CONFIG['filePathFormat'],
                "maxSize": CONFIG['fileMaxSize'],
                "allowFiles": CONFIG['fileAllowFiles']
            }

        if fieldName in request.files:
            field = request.files[fieldName]
            uploader = Uploader(field, config, current_app.static_folder)
            result = uploader.getFileInfo()
        else:
            result['state'] = '上传接口出错'

    elif action in ('uploadscrawl'):
        # 涂鸦上传
        fieldName = CONFIG.get('scrawlFieldName')
        config = {
            "pathFormat": CONFIG.get('scrawlPathFormat'),
            "maxSize": CONFIG.get('scrawlMaxSize'),
            "allowFiles": CONFIG.get('scrawlAllowFiles'),
            "oriName": "scrawl.png"
        }
        if fieldName in request.form:
            field = request.form[fieldName]
            uploader = Uploader(field, config, app.static_folder, 'base64')
            result = uploader.getFileInfo()
        else:
            result['state'] = '上传接口出错'

    elif action in ('catchimage'):
        config = {
            "pathFormat": CONFIG['catcherPathFormat'],
            "maxSize": CONFIG['catcherMaxSize'],
            "allowFiles": CONFIG['catcherAllowFiles'],
            "oriName": "remote.png"
        }
        fieldName = CONFIG['catcherFieldName']

        if fieldName in request.form:
            # 这里比较奇怪，远程抓图提交的表单名称不是这个
            source = []
        elif '%s[]' % fieldName in request.form:
            # 而是这个
            source = request.form.getlist('%s[]' % fieldName)

        _list = []
        for imgurl in source:
            uploader = Uploader(imgurl, config, app.static_folder, 'remote')
            info = uploader.getFileInfo()
            _list.append({
                'state': info['state'],
                'url': info['url'],
                'original': info['original'],
                'source': imgurl,
            })

        result['state'] = 'SUCCESS' if len(_list) > 0 else 'ERROR'
        result['list'] = _list

    else:
        result['state'] = '请求地址出错'

    result = json.dumps(result)

    if 'callback' in request.args:
        callback = request.args.get('callback')
        if re.match(r'^[\w_]+$', callback):
            result = '%s(%s)' % (callback, result)
            mimetype = 'application/javascript'
        else:
            result = json.dumps({'state': 'callback参数不合法'})

    res = make_response(result)
    res.mimetype = mimetype
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = 'X-Requested-With,X_Requested_With'
    return res


@main.route('/programposts',methods=['GET','POST'])
def program_posts():
    page = request.args.get('page', 1, type=int)
    s='程序人生'
    #获取分页显示的文章
    pagination = Post.query.order_by(Post.timestamp.desc()).filter_by(group=s.decode('utf8')).paginate(
        page, per_page=current_app.config['FLASK_POSTS_PRE_PAGE'],
        error_out=False)
    posts = pagination.items
    if len(posts)==0:
        posts=None
    #获取最新评论的文章
    recent_comment_posts = Post.query.filter(and_(Post.group == s.decode('utf8'),Post.last_comment_time!=None)).order_by(Post.last_comment_time.desc()).limit(8)
    #获取显示的标签信息
    lifetags=Tag.query.filter(Tag.group_id==2,Tag.posts_count>0).all()
    return render_template('classfy_posts.html',pagination=pagination,posts=posts,
                           recent_comment_posts=recent_comment_posts,tags=lifetags,classfy=s)

@main.route('/technologyposts',methods=['GET','POST'])
def technology_posts():
    page = request.args.get('page', 1, type=int)
    s = '技术笔记'
    pagination = Post.query.order_by(Post.timestamp.desc()).filter_by(group=s.decode('utf8')).paginate(
        page, per_page=current_app.config['FLASK_POSTS_PRE_PAGE'],
        error_out=False)
    posts = pagination.items
    if len(posts)==0:
        posts=None
    recent_comment_posts = Post.query.filter(and_(Post.group == s.decode('utf8'),Post.last_comment_time!=None)).order_by(Post.last_comment_time.desc()).limit(8)
    tectags = Tag.query.filter(Tag.group_id==1,Tag.posts_count>0).all()
    return render_template('classfy_posts.html',pagination=pagination,posts=posts,
                           recent_comment_posts=recent_comment_posts,tags=tectags,classfy=s)
                           
@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/posts/tag/<int:id>',methods=['GET'])
def query_by_tag(id):
    page = request.args.get('page', 1, type=int)
    tag=Tag.query.filter_by(id=id).first()
    group=Group.query.filter_by(group_id=tag.group_id).first()
    pagination = Post.query.order_by(Post.timestamp.desc()).filter_by(tag=tag.tag_name).paginate(
        page, per_page=current_app.config['FLASK_POSTS_PRE_PAGE'],
        error_out=False)
    posts = pagination.items
    if len(posts)==0:
        posts=None
    recent_comment_posts = Post.query.filter(and_(Post.group==group.group_name.decode('utf8'),Post.last_comment_time!=None)).order_by(Post.last_comment_time.desc()).limit(8)
    tectags = Tag.query.filter(Tag.group_id == group.group_id, Tag.posts_count > 0).all()
    return render_template('classfy_posts.html', pagination=pagination, posts=posts,
                           recent_comment_posts=recent_comment_posts, tags=tectags, classfy=(group.group_name+'-'+tag.tag_name))

@main.route('/posts/user/<int:user_id>',methods=['GET'])
def query_by_author(user_id):
    page = request.args.get('page', 1, type=int)
    user=User.query.filter_by(id=user_id).first()
    pagination = Post.query.filter(Post.author_id == user_id).order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASK_POSTS_PRE_PAGE'],
        error_out=False)
    posts = pagination.items
    if len(posts)==0:
        posts=None
    recent_comment_posts = Post.query.filter(and_(Post.author_id==user_id,Post.last_comment_time!=None)).order_by(Post.last_comment_time.desc()).limit(8)
    #tags = Tag.query.filter(Tag.group_id == group.group_id, Tag.posts_count > 0).all()
    return render_template('classfy_posts.html', pagination=pagination, posts=posts,
                           recent_comment_posts=recent_comment_posts, tags=None, classfy=(user.username)+'的博客')


@main.route('/recommand/<int:id>',methods=['GET'])
def recommand_post(id):
    post=Post.query.filter_by(id=id).first()
    if post != None:
        if post.recommend==1:
            post.recommend=0
        else:
            post.recommend=1
            post.last_recommend_time=datetime.utcnow()
        db.session.add(post)
    return redirect(url_for('.post',id=id))

@main.route('/search',methods=['POST','GET'])
def search():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('q')
    #keyword=request.form['keyword']
    pagination=Post.query.filter(or_(Post.title.ilike('%'+keyword+'%') , Post.body.ilike('%'+keyword+'%'))).paginate(
        page=page, per_page=current_app.config['FLASK_POSTS_PRE_PAGE'],
        error_out=False)
    posts=pagination.items
    change_color='<span id="changecolor">'+ keyword + '</span>'
    postphotos=[]
    for post in posts:
        keyinfo = re.compile(keyword)
        postphoto=Postphoto()
        postphoto.title = keyinfo.sub(change_color,post.title)
        postphoto.id=post.id;
        postphoto.timestamp=post.timestamp
        postphoto.read_cnt=post.read_cnt
        postphoto.body = post.body
        start_index = post.body.find(keyword)
        if start_index != -1:
            start_index=postphoto.body.rfind('<p>',0,start_index)
            if start_index==-1:
                start_index=0
            end_index=postphoto.body.find('</p>',start_index)
            if end_index==-1:
                end_index=150
            postphoto.body=postphoto.body[start_index:end_index]
        postphoto.body = keyinfo.sub(change_color, postphoto.body)
        postphoto.author_name=post.author.username
        postphotos.append(postphoto)
    return render_template('search.html',pagination=pagination,posts=postphotos,keyword=keyword,q=keyword)

@main.route('/cooment/del/<int:post_id>/<int:id>',methods=['POST','GET'])
def delcomment(id,post_id):
    comment=Comment.query.filter_by(id=id).first()
    db.session.delete(comment)
    return redirect(url_for('.post',id=post_id))

@main.route('/args',methods=['POST','GET'])
def args():
    page = request.args.get('page', 1, type=int)
    return str(page)