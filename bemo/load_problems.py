import json
from datetime import datetime
from bemo import db, app
from bemo.models import Problem

# Example JSON file structure:
# [
#     {
#         "title": "Sample Problem",
#         "statement": "Solve for x in the equation 2x + 3 = 7.",
#         "tags": "['math', 'equation']",
#         "rating": 3,
#         "cases": 5,
#         "inputs": "['input1.txt', 'input2.txt']",
#         "outputs": "['output1.txt', 'output2.txt']",
#         "solved": 0
#     },
#     ...
# ]

def load_problems_from_json(json_file):
    """Load problems from a JSON file and add them to the database."""
    try:
        with open(json_file, 'r') as f:
            problems_data = json.load(f)

        with app.app_context():
            for problem_data in problems_data:
                # Check if a problem with the same title already exists
                existing_problem = Problem.query.filter_by(title=problem_data['title']).first()
                if existing_problem:
                    print(f"Problem with title '{problem_data['title']}' already exists. Skipping.")
                    continue

                # Create a new Problem instance
                new_problem = Problem(
                    title=problem_data['title'],
                    statement=problem_data['statement'],
                    tags=problem_data['tags'],
                    rating=problem_data['rating'],
                    cases=problem_data['cases'],
                    inputs=problem_data['inputs'],
                    outputs=problem_data['outputs'],
                    date_posted=datetime.utcnow()
                )

                # Add the problem to the session
                db.session.add(new_problem)
                print(f"Added problem: {problem_data['title']}")

            # Commit all changes to the database
            db.session.commit()
            print("All problems have been added to the database.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    json_file_path = 'problems.json'  # Path to your JSON file
    with app.app_context():
        load_problems_from_json(json_file_path)
