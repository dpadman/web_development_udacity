# system includes
import os
import re

# gce includes
import jinja2
import webapp2

# helper includes
import string
import random
import hmac
import json
import logging
import time

from google.appengine.ext import db
from google.appengine.api import memcache

gbl_userid = 1000
query_time = 0

template_dir = os.path.dirname(__file__)
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

def get_data(update):
    global query_time
    if update or memcache.get('blogs') is None:
        logging.info('reading from DB')
        blogs = db.GqlQuery("SELECT * FROM BlogEntry "
                            "ORDER BY created DESC")
        blogs = list(blogs)
        memcache.set('blogs', blogs)
        query_time = int(time.time())
    else:
        blogs = memcache.get('blogs')
        blogs = list(blogs)
    return blogs

def get_data_by_id(id, update):
    query_time = 0
    if update or memcache.get(str(id)) is None:
        logging.info('reading from DB for %ld' % id)
        blog = BlogEntry.get_by_id(id)
        if blog is None:
            return None
        query_time = int(time.time())
        memcache.set(str(id), (query_time, blog))
    else:
        (query_time, blog) = memcache.get(str(id))
    return (query_time, blog)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def write_json(self, j):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(j)

    def render_str(self, template, **kw):
        t = jinja_env.get_template(template)
        return t.render(kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


class BlogEntry(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

class Blog(Handler):
    def get(self):
        global query_time
        id = self.request.get('id', 0)
        id = id and long(id)
        if (id):
            (query_time, blog) = get_data_by_id(id, False)
            if blog is None:
                self.redirect('/blog/invalid')
            else:
                blogs = [blog]
                seconds = int(time.time() - query_time)
                self.render("front.html", blogs=blogs, secs=seconds)
        else:
            blogs = get_data(False)
            seconds = int(time.time() - query_time)
            self.render("front.html", blogs=blogs, secs=seconds)

class PostPage(Handler):
    def get(self, post_id):
        (query_time, blog) = get_data_by_id(long(post_id), False)
        if not blog:
            self.error(404)
            return

        blogs = [blog]
        seconds = int(time.time() - query_time)
        self.render("front.html", blogs = blogs, secs=seconds)

class PostPageJson(Handler):
    def get(self, post_id):
        (query_time, blog) = get_data_by_id(long(post_id), False)
        if not blog:
            self.error(404)
            return

        required_list = []
        required_keys = ['_content', '_subject']

        required_list.append(dict((k, blog.__dict__[k]) for k in required_keys if k in blog.__dict__))
        j = json.dumps(required_list)
        self.write_json(j)

class BlogJson(Handler):
    def get(self):
        blogs = db.GqlQuery("SELECT * FROM BlogEntry "
                            "ORDER BY created DESC")
        required_list = []
        required_keys = ['_content', '_subject']
        for blog in blogs:
            required_list.append(dict((k, blog.__dict__[k]) for k in required_keys if k in blog.__dict__))

        j = json.dumps(required_list)
        self.write_json(j)

class BlogNewPost(Handler):
    def get(self):
        self.render('blogpost.html', subject="", content="")

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            blog = BlogEntry(subject = subject, content = content)
            blog.put()
            get_data_by_id(blog.key().id(), True)
            get_data(True)
            #self.redirect("/blog?id=" + str(blog.key().id()))
            self.redirect("/blog/" + str(blog.key().id()))
        else:
            self.render('blogpost.html', subject=subject, content=content)


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")


class BlogUser(db.Model):
    username = db.StringProperty(required = True)
    userid = db.StringProperty(required = True)
    hm_hash = db.StringProperty(required = True)
    salt = db.StringProperty(required = True)
    email = db.StringProperty(required = False)

class BlogSignup(Handler):

# A way to override __init__(self)
#def __init__(self, request, response):
#self.initialize(request, response)

    def valid_username(self, username):
        return USER_RE.match(username)

    def valid_password(self, password):
        return PASSWORD_RE.match(password)

    def valid_email(self, email):
        return EMAIL_RE.match(email)

    def get_userid(self, username):
        blog_user = db.GqlQuery("SELECT * FROM BlogUser WHERE username = :1", username)

        if blog_user.count() == 0:
            global gbl_userid
            gbl_userid += 1
            return gbl_userid
        else:
            u = blog_user.get()
            return -1

    def get_7_random_char(self):
        s = ''
        for x in range(0, 7):
            s += random.choice(string.letters)
        return s

    def create_hmac(self, password):
        salt = self.get_7_random_char()
        hm = hmac.new(salt, str(password)).hexdigest()
        return(salt,hm)

    def create_cookie(self, userid, password):
        (salt, hm_hash) = self.create_hmac(password)
        self.response.headers.add_header('Set-Cookie', 'userid=%s; Path=/' % (str(userid) + '|' + hm_hash))
        return (salt, hm_hash)

    def create_db_entry(self, username, userid, hm_hash, salt, email=None):
        db_user = BlogUser(username=username,
                           userid=str(userid),
                           hm_hash=hm_hash, salt=salt, email=email)
        db_user.put()

    def get(self):
        self.render('blogsignup.html', 
                    username="", password="", verify="", email="",
                    username_err="", password_err="", verify_err="", email_err="")

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")

        flag_username = False
        flag_password = False
        flag_verify = False
        flag_email = False

        if not self.valid_username(username):
            flag_username = True

        if not self.valid_password(password):
            flag_password = True

        if password != verify:
            flag_verify = True

        if email and not self.valid_email(email):
            flag_email = True

        userid = self.get_userid(username)

        if userid == -1 or flag_username or flag_password or flag_verify or flag_email:
            self.render('blogsignup.html',
                        username_err='username exists' if userid == -1 else 'That\'s not a valid username.' if flag_username else '',
                        password_err='That wasn\'t a valid password.' if flag_password else '',
                        verify_err='Your passwords didn\'t match.' if flag_verify else '',
                        email_err='That\'s not a valid email.' if flag_email else '',
                        username=username,
                        email=email)
        else:
            (salt, hm_hash) = self.create_cookie(userid, password)
            self.create_db_entry(username, userid, hm_hash, salt, email)
            logging.info('user %s hm_hash %s' % (userid, hm_hash))
            time.sleep(1)
            self.redirect('/blog/welcome')

class BlogLogin(Handler):
    def get_db_user(self, username):
        blog_user = db.GqlQuery("SELECT * FROM BlogUser WHERE username = :1", username)
        return blog_user

    def username_match(self, blog_user):
        if blog_user.count() == 0:
            return False
        else:
            return True

    def password_match(self, blog_user, password):
        user = blog_user.get()

        if password:
            hm_hash = hmac.new(str(user.salt), str(password)).hexdigest()
            if hm_hash == user.hm_hash:
                return True
        return False

    def get(self):
        self.render('bloglogin.html', 
                    username="", password="", username_err="", password_err="")

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")

        flag_username = False
        flag_password = False

        blog_user = self.get_db_user(username)

        if not self.username_match(blog_user):
            flag_username = True

        if not self.password_match(blog_user, password):
            flag_password = True

        if flag_username or flag_password:
            self.render('bloglogin.html',
                        username_err='Username does NOT exist' if flag_username else '',
                        password_err='Incorrect password' if flag_password else '',
                        username=username)
        else:
            user = blog_user.get()
            self.response.headers.add_header('Set-Cookie', 'userid=%s; Path=/' % (str(user.userid) + '|' + str(user.hm_hash)))
            self.redirect('/blog/welcome')


class BlogLogout(Handler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', 'userid=; Path=/')
        self.redirect('/blog/signup')

class BlogWelcome(Handler):
    def print_db(self):
        users = db.GqlQuery("SELECT * FROM BlogUser")
        print("users count=" + str(users.count()))
        for u in users:
            print(u.username, u.password, u.userid, u.hm_hash, u.salt, u.email)

    def get(self):
        hm_hash = self.request.cookies.get('userid')
        logging.info('Cookie %s' % hm_hash)
        if hm_hash:
            (userid, hm_hash) = hm_hash.split('|')
        else:
            self.redirect('/blog/signup')
            return

        blog_user = db.GqlQuery("SELECT * FROM BlogUser WHERE hm_hash = :1", hm_hash)
        if blog_user.count() == 0:
            self.redirect('/blog/signup')
        else:
            b = blog_user.get()
            if b.userid != userid:
                self.redirect('/blog/signup')
            else:
                self.render('welcome.html', user=b)

    def post(self):
        pass

class BlogFlush(Handler):
    def get(self):
        global query_time
        query_time = 0
        memcache.flush_all()
        self.redirect('/blog')

app = webapp2.WSGIApplication([
        ('/blog', Blog),
        ('/blog/([0-9]+)', PostPage),
        ('/blog/([0-9]+).json', PostPageJson),
        ('/blog/newpost', BlogNewPost),
        ('/blog/signup', BlogSignup),
        ('/blog/welcome', BlogWelcome),
        ('/blog/.json', BlogJson),
        ('/blog/login', BlogLogin),
        ('/blog/logout', BlogLogout),
        ('/blog/flush', BlogFlush),
], debug=True)
