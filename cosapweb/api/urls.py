from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as auth_views

from cosapweb.api import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename="user")
router.register(r'register', views.RegisterViewSet, basename="register")
router.register(r'projects', views.ProjectViewSet, basename="project")
router.register(r'samples', views.SampleViewSet, basename="sample")
router.register(r'actions', views.ActionViewSet, basename="action")

urlpatterns = [
    path('', include(router.urls)),
    path('login/', auth_views.obtain_auth_token),
    path('get_user/', views.GetUserView.as_view()),
]
