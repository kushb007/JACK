import gradio as gr
import os
import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = "problem_data"  # Directory to store input-output files
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the directory exists
db = SQLAlchemy(app)

# Define the Problem model
class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), unique=True, nullable=False)

# Define the Gradio interface
def submit_problem(title, test_cases):
    # Save the problem to the database
    problem = Problem(title=title)
    db.session.add(problem)
    db.session.commit()
    
    # Save the test cases to a file
    problem_id = problem.id
    test_cases_path = os.path.join(UPLOAD_FOLDER, f"{problem_id}_test_cases.json")
    with open(test_cases_path, 'w') as f:
        json.dump(test_cases, f)
    
    return f"Problem '{title}' submitted successfully with {len(test_cases)} test cases."

title_input = gr.inputs.Textbox(label="Problem Title")
test_case_inputs = [gr.inputs.Textbox(label=f"Test Case {i+1}") for i in range(5)]  # Adjust the number of test cases as needed

iface = gr.Interface(
    fn=submit_problem,
    inputs=[title_input] + test_case_inputs,
    outputs="text",
    live=True
)

if __name__ == "__main__":
    iface.launch()