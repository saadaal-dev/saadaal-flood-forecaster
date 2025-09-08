# Dev Only
# Use the official PostgreSQL image from Docker Hub
FROM postgres:latest

# Set environment variables for database name, user, and password
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

# Copy bootstrap SQL script into the image
COPY sql/database_bootstrap.sql /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432