from app.main import app


REQUIRED_ROUTES = {
    ("POST", "/api/v1/users/signup"),
    ("POST", "/api/v1/users/login"),
    ("POST", "/api/v1/users/refresh"),
    ("POST", "/api/v1/users/logout"),
    ("GET", "/api/v1/users/me"),
    ("PATCH", "/api/v1/users/me"),
    ("PATCH", "/api/v1/users/me/password"),
    ("DELETE", "/api/v1/users/me"),
    ("GET", "/api/v1/admin/users"),
    ("PATCH", "/api/v1/admin/users/role"),
    ("POST", "/api/v1/patients"),
    ("GET", "/api/v1/patients"),
    ("GET", "/api/v1/patients/{patient_id}"),
    ("PATCH", "/api/v1/patients/{patient_id}"),
    ("DELETE", "/api/v1/patients/{patient_id}"),
    ("POST", "/api/v1/medical-records"),
    ("GET", "/api/v1/patients/{patient_id}/medical-records"),
    ("GET", "/api/v1/medical-records/{record_id}"),
}


def main() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})
    registered_routes = {
        (method.upper(), path)
        for path, operations in paths.items()
        for method in operations
    }

    missing_routes = sorted(REQUIRED_ROUTES - registered_routes)
    if missing_routes:
        details = "\n".join(
            f"- {method} {path}" for method, path in missing_routes
        )
        raise SystemExit(f"Required API routes are missing:\n{details}")

    print(f"FastAPI import succeeded: {len(paths)} documented paths")
    print(f"Required routes verified: {len(REQUIRED_ROUTES)}")


if __name__ == "__main__":
    main()
