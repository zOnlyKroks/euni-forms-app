"""Hook into Alliance Auth."""

# Django
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

# AA EVE Uni Forms
from euniforms import urls


class EuniFormsMenuItem(MenuItemHook):
    """Adds the Forms entry to the sidebar for authorized users."""

    def __init__(self):
        MenuItemHook.__init__(
            self,
            _("Forms"),
            "fas fa-clipboard-list fa-fw",
            "euniforms:index",
            navactive=["euniforms:"],
        )

    def render(self, request):
        if request.user.has_perm("euniforms.basic_access") or request.user.has_perm(
            "euniforms.manage_forms"
        ):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return EuniFormsMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "euniforms", r"^forms/")
