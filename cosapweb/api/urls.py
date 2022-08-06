from django.urls import path, include
from rest_framework.routers import DefaultRouter

from cosapweb.api import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename="user")
router.register(r'register', views.RegisterViewSet, basename="register")
router.register(r'login', views.LoginViewSet, basename="login")
router.register(r'projects', views.ProjectViewSet, basename="project")

urlpatterns = [
    path('', include(router.urls)),
    path('logout', views.LogoutView.as_view()),
]
