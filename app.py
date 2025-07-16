from flask import Flask, render_template, request, send_file, redirect, url_for, session
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Change if using a cloud service
db = client['annual_reports']  # Database name
reports_collection = db['reports']  # Collection name for department data
users_collection = db['users']  # Collection for user data
progress_reports_collection = db['progress_reports']  # Collection for progress reports

# Sample data for departments
data = [
    {"department": "Computer", "students": 500, "faculty": 30, "publications": 120},
    {"department": "Electrical", "students": 450, "faculty": 28, "publications": 110},
    {"department": "Mech", "students": 400, "faculty": 25, "publications": 90},
    {"department": "Physics", "students": 300, "faculty": 20, "publications": 80},
    {"department": "Maths", "students": 250, "faculty": 18, "publications": 70},
]

# Sample user data for initial load
initial_users = [
    {"email": "student@example.com", "role": "student", "password": "password123"},
    {"email": "faculty@example.com", "role": "faculty", "password": "faculty123"},
    {"email": "admin@example.com", "role": "admin", "password": "adminpass"},
]

# Insert initial user data into MongoDB if empty
if users_collection.count_documents({}) == 0:
    users_collection.insert_many(initial_users)

def generate_pdf(year):
    pdf_file = f'report_{year}.pdf'
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.drawString(100, 750, f"Annual Report for {year}")
    c.drawString(100, 730, "Department Data:")
    
    # Add more content as needed
    for i, department in enumerate(data):
        c.drawString(100, 700 - (i * 20), f"{department['department']}: {department['students']} students")

    c.save()
    
    return send_file(pdf_file, as_attachment=True)

@app.route("/")
def home():
    if 'email' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route("/dashboard")
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    role = session.get('role')

    if role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return "Unauthorized Access"

@app.route("/student_dashboard")
def student_dashboard():
    if 'email' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    reports = list(progress_reports_collection.find({}, {'_id': 0}))  # Adjust query as needed

    # You may also want to fetch department data if needed
    departments = data  # Assuming 'data' is defined elsewhere in your code

    return render_template("student_dashboard.html", progress_reports=reports, departments=departments)

@app.route("/faculty_dashboard")
def faculty_dashboard():
    if 'email' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))

    return render_template("faculty_dashboard.html", departments=data)

@app.route("/admin_dashboard")
def admin_dashboard():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    return render_template("admin_dashboard.html", departments=data)

@app.route("/view_users")
def view_users():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    users_data = list(users_collection.find({}, {'_id': 0, ' password': 0}))  # Exclude passwords
    return render_template("view_users.html", users=users_data)

@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_email = request.form['email']
        new_role = request.form['role']
        new_password = request.form['password']
        users_collection.insert_one({"email": new_email, "role": new_role, "password": new_password})
        return redirect(url_for('view_users'))

    return render_template("add_user.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({"email": email, "password": password})

        if user:
            session['email'] = email
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials, please try again."

    return render_template('login.html')

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route("/generate_graph")
def generate_graph():
    df = pd.DataFrame(data)
    plt.figure(figsize=(20, 20))
    plt.bar(df['department'], df['students'], color='blue')
    plt.title('Number of Students per Department')
    plt.xlabel('Department')
    plt.ylabel('Number of Students')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    
    return send_file(img, mimetype='image/png', as_attachment=True, download_name='report.png')

@app.route("/generate_report", methods=["POST"])
def generate_report():
    if 'email' not in session:
        return redirect(url_for('login'))

    year = request.form['year']
    file_type = request.form['file_type']

    if file_type == 'CSV':
        df = pd.DataFrame(data)
        csv_file = f'report_{year}.csv'
        df.to_csv(csv_file, index=False)
        return send_file(csv_file, as_attachment=True)

    elif file_type == 'PDF':
        return generate_pdf(year)

    elif file_type == 'GRAPH':
        return generate_graph()

    return "Invalid report type."

@app.route("/download_report")
def download_report():
    if 'email' not in session:
        return redirect(url_for('login'))

    df = pd.DataFrame(data)
    plt.figure(figsize=(10, 6))
    plt.bar(df['department'], df['students'], color='blue')
    plt.title('Number of Students per Department')
    plt.xlabel('Department')
    plt.ylabel('Number of Students')
    plt.xticks(rotation=45)
    
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    
    return send_file(img, mimetype='image/png', as_attachment=True, download_name='report.png')


@app.route("/update_settings", methods=["POST"])
def update_settings():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    app_name = request.form['app_name']
    contact_email = request.form['contact_email']
    user_roles = request.form['user_roles']

    session['current_settings'] = {
        'app_name': app_name,
        'contact_email': contact_email,
        'user_roles': user_roles
    }

    return redirect(url_for('system_settings'))

@app.route("/progress_reports", methods=["GET", "POST"])
def progress_reports():
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        year = request.form['year']
        name = request.form['name']
        student_id = request.form['student_id']
        math = request.form['math']
        science = request.form['science']
        english = request.form['english']
        attendance = request.form['attendance']
        department = request.form['department']
        remarks = request.form['remarks']
        
        # Insert or update the progress report in the database
        progress_reports_collection.update_one(
            {"student_id": student_id, "year": year},
            {"$set": {
                "name": name,
                "math": math,
                "science": science,
                "english": english,
                "attendance": attendance,
                "department": department,
                "remarks": remarks
            }},
            upsert=True
        )
        return redirect(url_for('progress_reports'))

    # Fetch all progress reports
    reports = list(progress_reports_collection.find({}, {'_id': 0}))
    return render_template("progress_reports.html", progress_reports=reports)

@app.route("/download_progress_report/<student_id>/<year>")
def download_progress_report(student_id, year):
    # Fetch the report from the database using the provided student_id and year
    report = progress_reports_collection.find_one({"student_id": student_id, "year": year}, {'_id': 0})
    
    # Check if the report exists
    if report:
        pdf_file = f'progress_report_{student_id}_{year}.pdf'  # Include student_id in the filename for uniqueness
        c = canvas.Canvas(pdf_file, pagesize=letter)
        
        # Add content to the PDF
        c.drawString(100, 750, f"Progress Report for {report['name']} ({year})")
        c.drawString(100, 730, f"Student ID: {report['student_id']}")
        c.drawString(100, 710, f"Math Score: {report['math']}")
        c.drawString(100, 690, f"Science Score: {report['science']}")
        c.drawString(100, 670, f"English Score: {report['english']}")
        c.drawString(100, 650, f"Attendance: {report.get('attendance', 'N/A')}")  # Use .get() to avoid KeyError
        c.drawString(100, 630, f"Department: {report.get('department', 'N/A')}")  # Use .get() to avoid KeyError
        c.drawString(100, 610, f"Remarks: {report.get('remarks', 'N/A')}")  # Use .get() to avoid KeyError
        
        c.save()  # Save the PDF file
        
        # Send the PDF file as an attachment
        return send_file(pdf_file, as_attachment=True)
    
    # If the report is not found, return a 404 error
    return "Report not found.", 404

@app.route("/delete_user/<email>")
def delete_user(email):
    if 'email' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    # Delete the user from the database
    result = users_collection.delete_one({"email": email})

    if result.deleted_count > 0:
        return redirect(url_for('view_users'))  # Redirect to the user list after deletion
    else:
        return "User  not found.", 404  # Handle the case where the user is not found

if __name__ == "__main__":
    app.run(debug=True)