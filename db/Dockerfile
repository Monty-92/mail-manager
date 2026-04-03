FROM pgvector/pgvector:pg16

# Copy migrations for easy access inside container
COPY migrations/ /docker-entrypoint-initdb.d/

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER:-mailmanager} -d ${POSTGRES_DB:-mailmanager}
