"""API v1 router module."""


from fastapi import APIRouter
from fastapi.routing import APIRoute

from . import corpus, endpoints, mcp, users

v1_router = APIRouter()
v1_router.include_router(endpoints.router, tags=["documents"])
v1_router.include_router(users.router, prefix="/user", tags=["users"])
v1_router.include_router(corpus.router, prefix="/corpus", tags=["corpus"])
v1_router.include_router(mcp.router, tags=["mcp"])


def _add_trailing_slash_aliases(router: APIRouter) -> None:
    """Serve every route at both its slash and slash-less form.

    Relying on Starlette's redirect_slashes instead is not viable behind the
    frontend proxy: Next.js normalises the trailing slash off a rewritten path,
    so a request the browser made to /api/v1/list-indexes/ arrives here as
    /api/v1/list-indexes and earns a 307 whose Location is built from the
    proxied Host header - http://backend:8000/... - an internal address the
    browser cannot reach, and one that should not be disclosed to it either.

    Registering both forms removes the redirect entirely, which also spares
    external API-key clients (the Promethean AI backend's KM connector calls
    these paths with trailing slashes) an extra round trip.

    Aliases are hidden from the schema so the OpenAPI document keeps exactly one
    entry per endpoint.
    """
    for route in list(router.routes):
        if not isinstance(route, APIRoute) or route.path in ("", "/"):
            continue

        if route.path.endswith("/"):
            alias_path = route.path.rstrip("/")
        else:
            alias_path = route.path + "/"

        if not alias_path:
            continue
        # Match on path AND methods: a collection endpoint typically has both
        # GET / and POST /, which alias to the same path. Keying on path alone
        # drops the second and the surviving route answers 405 for the other verb.
        if any(
            isinstance(r, APIRoute)
            and r.path == alias_path
            and r.methods & route.methods
            for r in router.routes
        ):
            continue

        router.add_api_route(
            alias_path,
            route.endpoint,
            methods=list(route.methods),
            response_model=route.response_model,
            status_code=route.status_code,
            dependencies=route.dependencies,
            name=route.name,
            include_in_schema=False,
        )


_add_trailing_slash_aliases(v1_router)
