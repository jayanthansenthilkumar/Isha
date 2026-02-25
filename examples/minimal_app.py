"""
Isha Framework — Minimal Example

The simplest possible Isha application.
"""

from isha import Isha, JSONResponse

app = Isha("minimal")


@app.route("/")
async def home(request):
    return "Welcome to Isha!"


@app.route("/api/hello/<str:name>")
async def hello(request, name="World"):
    return JSONResponse({"message": f"Hello, {name}!"})


@app.route("/api/data", methods=["GET", "POST"])
async def data(request):
    if request.method == "POST":
        body = await request.json()
        return JSONResponse({"received": body}, status_code=201)
    return JSONResponse({"items": [1, 2, 3]})


if __name__ == "__main__":
    app.run(port=8000, debug=True)
