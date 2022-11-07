from django.urls import include, path
from rest_framework.authtoken import views as auth_views
from rest_framework.routers import DefaultRouter

from cosapweb.api import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"login", views.AuthTokenViewSet, basename="login")
router.register(r"register", views.RegisterViewSet, basename="register")
router.register(r"get_user", views.GetUserViewSet, basename="get_user")
router.register(r"projects", views.ProjectViewSet, basename="project")
router.register(r"files", views.FileViewSet, basename="files")
router.register(r"actions", views.ActionViewSet, basename="action")

urlpatterns = [path("", include(router.urls))]
