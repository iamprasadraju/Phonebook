from flask import Flask,render_template,request

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/home')
def home():
    return render_template('create.html')

@app.route('/create')
def create():
    ...

if __name__ == "__main__":
    app.run(debug=True)