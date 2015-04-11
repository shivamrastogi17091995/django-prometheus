import sys
from django_prometheus.db import (
    connections_total, execute_total, execute_many_total, errors_total)
from django.db.backends.sqlite3 import base


class DatabaseFeatures(base.DatabaseFeatures):
    """Our database has the exact same features as the base one."""
    pass


class DatabaseWrapper(base.DatabaseWrapper):
    """Extends the DatabaseWrapper to count connections and cursors."""

    def get_new_connection(self, *args, **kwargs):
        connections_total.labels(self.alias, self.vendor).inc()
        return super(DatabaseWrapper, self).get_new_connection(*args, **kwargs)

    def create_cursor(self):
        return self.connection.cursor(factory=ExportingCursorWrapper(
            self.alias, self.vendor))


def ExportingCursorWrapper(alias, vendor):
    """Returns a CursorWrapper class that knows its database's alias and
    vendor name.
    """

    class CursorWrapper(base.SQLiteCursorWrapper):
        """Extends the base CursorWrapper to count events."""

        def get_current_exception_type(self):
            """Returns the name of the type of the current exception."""
            ex_type = sys.exc_info()[0]
            if ex_type is None:
                return '<no exception>'
            return ex_type.__name__

        def execute(self, *args, **kwargs):
            execute_total.labels(alias, vendor).inc()
            try:
                return super(CursorWrapper, self).execute(*args, **kwargs)
            except:
                errors_total.labels(
                    alias, vendor, self.get_current_exception_type()).inc()
                raise

        def execute_many(self, query, param_list, *args, **kwargs):
            execute_total.labels(alias, vendor).inc(len(param_list))
            try:
                return super(CursorWrapper, self).execute(
                    query=query, param_list=param_list, *args, **kwargs)
            except:
                errors_total.labels(
                    alias, vendor, self.get_current_exception_type()).inc()
                raise
    return CursorWrapper