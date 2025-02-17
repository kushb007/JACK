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
UPLOAD_FOLDER = "bemo/static/problem_data"  # Directory to store input-output files
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the directory exists
db = SQLAlchemy(app)

# Define the Problem model
class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), unique=True, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    statement = db.Column(db.Text, nullable=False, default='')
    tags = db.Column(db.Text, nullable=False, default='[]')  # Store as JSON string
    rating = db.Column(db.Integer, nullable=False, default=0)
    cases = db.Column(db.Integer, nullable=False, default=0)
    inputs = db.Column(db.Text, nullable=False, default='[]')  # JSON file paths
    outputs = db.Column(db.Text, nullable=False, default='[]')  # JSON file paths
    solved = db.Column(db.Integer, nullable=False, default=0)

# Ensure database is created
with app.app_context():
    db.create_all()

# Function to save input-output pairs to files and store their paths
def save_input_output_pairs(input_texts, output_texts, title):
    """Save input-output pairs as separate files and return JSON lists of file paths."""
    input_paths = []
    output_paths = []
    problem_dir = os.path.join(UPLOAD_FOLDER, secure_filename(title))
    print("problem dir",problem_dir)
    os.makedirs(problem_dir, exist_ok=True)  # Ensure directory exists
    for i, (input_text, output_text) in enumerate(zip(input_texts, output_texts)):
        input_path = os.path.join(problem_dir, f"input_{i}.txt")
        output_path = os.path.join(problem_dir, f"output_{i}.txt")
        with open(input_path, "w") as f:
            print("input",input_text)
            f.write(input_text)
        with open(output_path, "w") as f:
            print("output",output_text)
            f.write(output_text)
        input_paths.append(secure_filename(title)+"/"+f"input_{i}.txt")
        output_paths.append(secure_filename(title)+"/"+f"output_{i}.txt")

    return json.dumps(input_paths), json.dumps(output_paths)

#TODO : Read inputted data properly
# Function to add a new problem
def add_problem(title, statement, tags, rating, test_cases):
    with app.app_context():
        if Problem.query.filter_by(title=title).first():
            return f"Error: Problem '{title}' already exists."

        inputs = [case[0] for case in test_cases]
        outputs = [case[1] for case in test_cases]

        # Save inputs and outputs as files
        input_paths, output_paths = save_input_output_pairs(inputs, outputs, title)

        new_problem = Problem(
            title=title,
            statement=statement,
            tags=json.dumps(tags.split(",")),  # Convert CSV input to JSON
            rating=int(rating),
            cases=len(inputs),
            inputs=input_paths,
            outputs=output_paths,
            solved=0
        )

        db.session.add(new_problem)
        db.session.commit()
        return f"Problem '{title}' added successfully with {len(inputs)} test cases!"

# Function to dynamically add a new test case
def add_test_case(test_cases):
    test_cases.append(["", ""])  # Append an empty input-output pair
    return test_cases  # Return the updated list

# Function to collect and process all test cases
def submit_problem(title, statement, tags, rating, test_cases):
    return add_problem(title, statement, tags, rating, test_cases)

# Initial test cases
test_cases = [["", ""]]  # Start with one pair

#TODO : Fix hidden inputs and outputs when not in focus
# Create Gradio interface
with gr.Blocks() as interface:
    gr.Markdown("# Add a New Problem")
    gr.Markdown("Fill out the form below to add a new problem. Click 'Add Another Test Case' to add more input-output pairs.")

    title = gr.Textbox(label="Title", placeholder="Enter problem title")
    statement = gr.Textbox(label="Statement", placeholder="Enter problem statement", lines=3)
    tags = gr.Textbox(label="Tags (comma-separated)", placeholder="e.g. arrays, dynamic programming")
    rating = gr.Number(label="Rating", value=1500)

    # Dynamic test case section
    test_case_display = gr.Dataframe(
        headers=["Input", "Output"], datatype=["str", "str"], value=test_cases,
        interactive=True, label="Test Cases", type="array", col_count=2
    )
    
    add_case_button = gr.Button("Add Another Test Case")
    add_case_button.click(add_test_case, inputs=[test_case_display], outputs=[test_case_display])

    submit_button = gr.Button("Submit Problem")
    output_text = gr.Textbox(label="Result", interactive=False)

    # When the submit button is clicked, process and save the problem
    submit_button.click(
        submit_problem,
        inputs=[title, statement, tags, rating, test_case_display],
        outputs=output_text
    )

# Run Gradio
if __name__ == "__main__":
    interface.launch()
