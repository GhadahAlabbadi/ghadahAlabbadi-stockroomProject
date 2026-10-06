from django.core.management.base import BaseCommand

from inventory import queries

SECTIONS = ["crud", "querysets", "relationships", "aggregation"]


class Command(BaseCommand):
    help = "Print the project evidence: CRUD, QuerySets, relationships and aggregation."

    def add_arguments(self, parser):
        parser.add_argument(
            "sections",
            nargs="*",
            help="Sections to run (crud, querysets, relationships, aggregation). Default: all that exist.",
        )

    def handle(self, *args, **options):
        for name in options["sections"] or SECTIONS:
            function = getattr(queries, f"run_{name}", None)
            if function is None:
                self.stdout.write(f"(section '{name}' is not written yet)")
                continue
            function()