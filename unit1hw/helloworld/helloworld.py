import webapp2
form="""
<form method="post" action=/testform>
    <input type="password" name="q"><br>
    <input type="checkbox" name="r">
    <input type="checkbox" name="s">
    <input type="checkbox" name="t"><br>
    <label>
        1. Cacun
        <input type="radio" name="u" value="one">
    </label><br>
    <label>
        2. Sweden, northern lights
    <input type="radio" name="u" value="two">
    </label><br>
    <label>
        3. Bangkok, Thailand
    <input type="radio" name="u" value="three">
    </label><br>
    
    <select name="d">
        <option value="1">Hawaii</option>
        <option value="2">India</option>
        <option>China</option>
    </select>
    <input type="submit">
</form>
"""
class TestHandler(webapp2.RequestHandler):
    def post(self):
        q = self.request.get("q")
        self.response.out.write(self.request)


class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(form)

app = webapp2.WSGIApplication([
        ('/', MainPage), ('/testform', TestHandler)
], debug=True)
