import webapp2

form="""

<!DOCTYPE html>

<html>
  <head>
    <title>Unit 2 Rot 13</title>
  </head>

  <body>
    <h2>Enter some text to ROT13:</h2>
    <form method="post">
      <textarea name="text"
                style="height: 100px; width: 400px;">%s</textarea>
      <br>
      <input type="submit">
    </form>
  </body>

</html>
"""


class Rot13(webapp2.RequestHandler):
    def get_form(self, text):
        return form % text

    def escape_text(self, text):
        for (i,o) in (('&','&amp;'),
                      ('>','&gt;'),
                      ('<','&lt;'),
                      ('"', '&quot;')):
            text = text.replace(i, o)
        return text

    def encrypt_input(self, text):
        l_text = list(text)
        i = 0
        for s in text:
            if s >= 'A' and s <= 'Z':
                l_text[i] = chr(ord('A') + ((ord(s) - ord('A') + 13) % 26))
            elif s >= 'a' and s <= 'z':
                l_text[i] = chr(ord('a') + ((ord(s) - ord('a') + 13) % 26))
            i += 1
        return "".join(l_text)

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(self.get_form(""))

    def post(self):
        text = self.request.get("text")
        text = self.encrypt_input(text)
        self.response.out.write(self.get_form(self.escape_text(text)))

app = webapp2.WSGIApplication([
        ('/', Rot13)
], debug=True)
