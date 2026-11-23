from django.db import connection
from storages.backends.s3 import S3Storage


class TenantS3Storage(S3Storage):
    def _normalize_name(self, name):
        schema_name = getattr(connection, 'schema_name', 'public')

        if not name.startswith(f'{schema_name}/'):
            name = f'{schema_name}/{name}'
        return super()._normalize_name(name)