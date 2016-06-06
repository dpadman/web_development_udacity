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

from google.appengine.ext import db

gbl_userid = 1000

template_dir = os.path.dirname(__file__)
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

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
        id = self.request.get('id', 0)
        id = id and long(id)
        if (id):
            blog = BlogEntry.get_by_id(id)
            if blog is None:
                self.redirect('/blog/invalid')
            else:
                blogs = [blog]
                self.render("front.html", blogs=blogs)
        else:
            blogs = db.GqlQuery("SELECT * FROM BlogEntry "
                                "ORDER BY created DESC")
            self.render("front.html", blogs=blogs)

class BlogNewPost(Handler):
    def get(self):
        self.render('blogpost.html', subject="", content="")

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            blog = BlogEntry(subject = subject, content = content)
            blog.put()
            self.redirect("/blog?id=" + str(blog.key().id()))
        else:
            self.render('blogpost.html', subject=subject, content=content)


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")


class BlogUser(db.Model):
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)
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
            print("get_userid:", u.username, u.password, u.userid, u.hm_hash, u.salt, u.email)
            return -1

    def get_7_random_char(self):
        s = ''
        for x in range(0, 7):
            s += random.choice(string.letters)
        return s

    def create_hmac(self, userid):
        salt = self.get_7_random_char()
        hm = hmac.new(salt, str(userid)).hexdigest()
        return(salt,hm)

    def create_cookie(self, userid):
        (salt, hm_hash) = self.create_hmac(userid)
        self.response.headers.add_header('Set-Cookie', 'userid=%s; Path=/' % (str(userid) + '|' + hm_hash))
        return (salt, hm_hash)

    def create_db_entry(self, username, password, userid, hm_hash, salt, email=None):
        db_user = BlogUser(username=username,
                           password=password, userid=str(userid),
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
            (salt, hm_hash) = self.create_cookie(userid)
            self.create_db_entry(username, password, userid, hm_hash, salt, email)
            self.redirect('/blog/welcome')

class BlogWelcome(Handler):
    def print_db(self):
        users = db.GqlQuery("SELECT * FROM BlogUser")
#print("users count=" + str(users.count()))
        for u in users:
            print(u.username, u.password, u.userid, u.hm_hash, u.salt, u.email)

    def get(self):
        import time
        time.sleep(1)
#self.print_db()
        hm_hash = self.request.cookies.get('userid')
        (userid, hm_hash) = hm_hash.split('|')
        print(userid, hm_hash)
        blog_user = db.GqlQuery("SELECT * FROM BlogUser WHERE hm_hash = :1", hm_hash)
        if blog_user.count() == 0:
            self.redirect('/blog/signup')
        else:
            for b in blog_user:
                db_hm_hash = hmac.new(str(b.salt), str(b.userid)).hexdigest()
                if db_hm_hash != hm_hash:
                    self.redirect('/blog/signup')
                else:
                    self.render('welcome.html', user=b)

    def post(self):
        pass

app = webapp2.WSGIApplication([
        ('/blog', Blog),
        ('/blog/newpost', BlogNewPost),
        ('/blog/signup', BlogSignup),
        ('/blog/welcome', BlogWelcome),
], debug=True)
