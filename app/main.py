import platform
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse

from app.settings import version, solverSettings
from app.solver.data.Job import Job
from app.solver.data.Result import Result
from app.solver.solver import solve
from app.solver.data.Job import QNS, INS, NS

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting CutSolver {version}...")
    print(f"Settings: {solverSettings.json()}")
    print(f"Routes: {app.routes}")
    yield
    print("Shutting down CutSolver...")


app = FastAPI(title="CutSolverBackend", version=version, lifespan=lifespan)


# needs to be before CORS!
# https://github.com/tiangolo/fastapi/issues/775#issuecomment-592946834
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # TODO: filter out expected exceptions and let unexpected ones go?
        # probably want some kind of logging here
        return PlainTextResponse(str(e), status_code=400)


app.middleware("http")(catch_exceptions_middleware)

cors_origins = [
    "http:localhost",
    "https:localhost",
    "http:localhost:8080",
    "*",  # this might be dangerous
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# response model ensures correct documentation, exclude skips optional
@app.post("/solve", response_model=Result, response_model_exclude_defaults=True)
async def post_solve(job_data: dict):
    print("Received job data:", job_data)
    available_lengths = job_data.get("stocks", [])
    cut_width = job_data.get("cut_width", 0)
    required = job_data.get("required", [])

    stocks = [INS(length=item['length'], quantity=item.get('quantity', None)) for item in available_lengths]
    required_items = []
    
    for item in required:
        length = item['length']
        quantity = item['quantity']
        name = item.get('name')
        
        print(f"Processing required item: length={length}, quantity={quantity}, name={name}")
        
        if quantity <= 0:
            print(f"Warning: Required item has non-positive quantity: {item}")
        else:
            required_items.append(QNS(length=length, quantity=quantity, name=name))

    print("Stocks prepared:", stocks)
    print("Required items prepared (final):", required_items)

    # Verificação extra antes de criar o Job
    for req in required_items:
        if req.quantity <= 0:
            print(f"Error: Item {req.name} has non-positive quantity: {req.quantity}")
            return {"error": f"Required item {req.name} has a quantity of {req.quantity}."}

    job = Job(stocks=tuple(stocks), cut_width=cut_width, required=tuple(required_items))

    print("Job created:", job)

    try:
        solved: Result = solve(job)
    except Exception as e:
        print("Error while solving:", str(e))
        raise e

    print("Returning result:", solved)
    print("Dados do Job:")
    print(f"Estoques: {[{'length': stock.length, 'name': stock.name, 'quantity': stock.quantity} for stock in job.stocks]}")
    print(f"Cortes Requeridos: {[{'length': size.length, 'quantity': size.quantity, 'name': size.name} for size in job.required]}")

    return solved.dict()



@app.get("/debug", response_class=HTMLResponse)
def get_debug():
    static_answer = (
        "Debug Infos:"
        "<ul>"
        f"<li>Node: {platform.node()}</li>"
        f"<li>System: {platform.system()}</li>"
        f"<li>Machine: {platform.machine()}</li>"
        f"<li>Processor: {platform.processor()}</li>"
        f"<li>Architecture: {platform.architecture()}</li>"
        f"<li>Python Version: {platform.python_version()}</li>"
        f"<li>Python Impl: {platform.python_implementation()}</li>"
    )

    return static_answer


@app.get("/constants")
@app.get("/settings")
def get_settings():
    return solverSettings


# content_type results in browser pretty printing
@app.get("/", response_class=HTMLResponse)
def get_root():
    static_answer = (
        f"<h2>Hello from CutSolver {version}!</h2>"
        '<h3>Have a look at the documentation at <a href="./docs">/docs</a> for usage hints.</h3>'
        'Visit <a href="https://github.com/ModischFabrications/CutSolver">the repository</a> for further information. '
        'Constants are shown at <a href="./constants">/constants</a>. '
        'Debugging log are available at <a href="./debug">/debug</a>. '
    )

    return static_answer


@app.get("/version", response_class=PlainTextResponse)
def get_version():
    return version


# for debugging only
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
