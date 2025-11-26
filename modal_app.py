import modal

app = modal.App("restaurant-intelligence")

@app.function()
def hello():
    return "Modal is working!"