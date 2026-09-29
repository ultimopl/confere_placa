import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.auth import init_default_admin
from web.config import get_active_csv_path
from web.repository import repository
from web.routes import auth_routes, plate_routes, config_routes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure admin user exists and load configured CSV
    init_default_admin()
    csv_path = get_active_csv_path()
    if csv_path and os.path.exists(csv_path):
        try:
            repository.load(csv_path)
            print(f"[OK] CSV carregado na inicialização: {csv_path} ({len(repository.data)} registros)")
        except Exception as e:
            print(f"[AVISO] Falha ao carregar CSV inicial ({csv_path}): {e}")
    else:
        print("[AVISO] Nenhum arquivo CSV encontrado. Carregue um CSV na aba Configurações.")
    yield


app = FastAPI(
    title="Confere Placa Web",
    description="Sistema Web para controle e conferência de placas de veículos com suporte a placas temporárias e controle de acesso.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(auth_routes.router)
app.include_router(plate_routes.router)
app.include_router(config_routes.router)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.main:app", host="0.0.0.0", port=8000, reload=True)
