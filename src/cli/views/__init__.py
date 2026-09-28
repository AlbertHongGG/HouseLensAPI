"""HouseLensAPI - CLI 視圖套件 (CLI Views Package)"""

from src.cli.views.community_views import (
    community_to_dict,
    render_community_detail_panel,
    render_community_table,
)
from src.cli.views.console import (
    console,
    err_console,
    get_console,
    print_error,
    print_info,
    print_json_data,
    print_success,
    print_warning,
)
from src.cli.views.db_views import render_db_stats_dashboard
from src.cli.views.new_house_views import (
    new_house_to_dict,
    render_new_house_detail_view,
    render_new_house_table,
)
from src.cli.views.property_views import (
    property_to_dict,
    render_property_detail_view,
    render_property_table,
)

__all__ = [
    "console",
    "err_console",
    "get_console",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_json_data",
    "render_community_table",
    "render_community_detail_panel",
    "community_to_dict",
    "render_property_table",
    "render_property_detail_view",
    "property_to_dict",
    "render_new_house_table",
    "render_new_house_detail_view",
    "new_house_to_dict",
    "render_db_stats_dashboard",
]
