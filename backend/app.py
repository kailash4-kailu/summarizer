from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder="../templates")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.json
    text = data.get("text", "")

    summary = text[:200]

    return jsonify({"summary": summary})