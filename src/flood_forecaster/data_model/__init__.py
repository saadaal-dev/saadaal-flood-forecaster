from sqlalchemy.orm import declarative_base, registry

# Shared Base for all ORM models
Base = declarative_base()

mapper_registry = registry()
