from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email, ValidationError, Regexp
from bemo.models import User
from bemo import session


class Confirm(FlaskForm):
	username = StringField('Username', 
			validators=[DataRequired(), Length(min=2,max=20),Regexp(r"^(?=[a-zA-Z0-9._]{3,20}$)(?!.*[_.]{2})[^_.].*[^_.]$",0,"Incorrect characters")])
	firstname = StringField('First name', 
			validators=[DataRequired(), Length(min=2,max=20),Regexp(r"^(?=[a-zA-Z]{2,20}$)(?!.*[_.]{2})[^_.].*[^_.]$",0,"Must be only letters")])
	lastname = StringField('Last name', 
			validators=[DataRequired(), Length(min=2,max=20),Regexp(r"^(?=[a-zA-Z]{2,20}$)(?!.*[_.]{2})[^_.].*[^_.]$",0,"Must be only letters")])
	submit = SubmitField('Submit')

	def validate_username(self, username):
		user = User.query.filter_by(username=username.data).first()
		if user and ('id' not in session or user.id is not session['id']):
			raise ValidationError('That username is taken. Please choose a different one.')

	def validate_email(self, email):
		user = User.query.filter_by(email=email.data).first()
		if user and ('id' not in session or user.id is not session['id']):
			raise ValidationError('That email is taken. Please choose a different one.')

class Picture(FlaskForm):
	pic = FileField(
			validators=[ DataRequired()])
	submit = SubmitField('Upload File')

class Create(FlaskForm):
	title = StringField('Title', validators=[DataRequired()])
	statement = TextAreaField('Content', validators=[DataRequired()])
	input_exp = TextAreaField('Input', validators=[DataRequired()])
	output_exp = TextAreaField('Output', validators=[DataRequired()])
	samplein = TextAreaField('Sample Input', validators=[DataRequired()])
	sampleout = TextAreaField('Sample Output', validators=[DataRequired()])
	note = TextAreaField('Note')
	submit = SubmitField('Submit')

class Code(FlaskForm):
	code = FileField(
			validators=[])
	code_area = HiddenField("TextArea",id="code_input", name="code_input")
	submit = SubmitField('submit')


