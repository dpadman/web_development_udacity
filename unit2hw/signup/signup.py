import webapp2
import re

form="""

<!DOCTYPE html>

<html>
  <head>
    <title>Sign Up</title>
    <style type="text/css">
      .label {text-align: right}
      .error {color: red}
    </style>

  </head>

  <body>
    <h2>Signup</h2>
    <form method="post">
      <table>
        <tr>
          <td class="label">
            Username
          </td>
          <td>
            <input type="text" name="username" value="%(username)s">
          </td>
          <td class="error">
          %(username_err)s  
          </td>
        </tr>

        <tr>
          <td class="label">
            Password
          </td>
          <td>
            <input type="password" name="password" value="">
          </td>
          <td class="error">
          %(password_err)s  
          </td>
        </tr>

        <tr>
          <td class="label">
            Verify Password
          </td>
          <td>
            <input type="password" name="verify" value="">
          </td>
          <td class="error">
          %(verify_err)s  
          </td>
        </tr>

        <tr>
          <td class="label">
            Email (optional)
          </td>
          <td>
            <input type="text" name="email" value="%(email)s">
          </td>
          <td class="error">
          %(email_err)s  
          </td>
        </tr>
      </table>

      <input type="submit">
    </form>
  </body>

</html>
"""

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

class Signup(webapp2.RequestHandler):
    def get_form(self, form_data):
        return form % form_data

    def valid_username(self, username):
        return USER_RE.match(username)

    def valid_password(self, password):
        return PASSWORD_RE.match(password)

    def valid_email(self, email):
        return EMAIL_RE.match(email)

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(self.get_form({'username_err': '',
                                               'password_err': '',
                                               'verify_err': '',
                                               'email_err': '',
                                               'username': '',
                                               'email': ''}))

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

        if flag_username or flag_password or flag_verify or flag_email:
            self.response.out.write(
                    self.get_form(
                        {'username_err': 'That\'s not a valid username.' if flag_username else '',
                         'password_err': 'That wasn\'t a valid password.' if flag_password else '',
                         'verify_err': 'Your passwords didn\'t match.' if flag_verify else '',
                         'email_err': 'That\'s not a valid email.' if flag_email else '',
                         'username': username,
                         'email': email}))
        else:
            self.redirect('/welcome?username=%s' % username)

class Welcome(webapp2.RequestHandler):
    def get(self):
        username = self.request.get("username")
        self.response.out.write('<b>Welcome, %s!<b>' % username)

app = webapp2.WSGIApplication([
        ('/', Signup), ('/welcome', Welcome)
], debug=True)
