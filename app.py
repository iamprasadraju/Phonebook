from flask import Flask,render_template,request
from cs50 import SQL

db = SQL("sqlite:///database.db")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/home')
def home():
    return render_template('create.html')

@app.route('/create',methods=["POST"])
def create():
    if request.method == "POST":
        contact_name = request.form.get("contact_name")
        contact_num = request.form.get("contact_number")
        db.execute("INSERT INTO prasad(contact_name,contact_number) VALUES(?,?)",contact_name,contact_num)
        return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)