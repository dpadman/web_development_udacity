import os
import jinja2
import webapp2

from google.appengine.ext import db

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

class Mainpage(Handler):
    def get(self):
        items = self.request.get_all("food")
        self.render("shopping_list.html",
                    items=items)

class FizzBuzzHandler(Handler):
    def get(self):
        n = self.request.get('n', 0)
        n = n and int(n)
        self.render('fizzbuzz.html', n = n)

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

app = webapp2.WSGIApplication([
        ('/', Mainpage), ('/fizzbuzz', FizzBuzzHandler),
        ('/blog', Blog), ('/blog/newpost', BlogNewPost)
], debug=True)
