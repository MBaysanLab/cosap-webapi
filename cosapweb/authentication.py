from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.authtoken.models import Token

class BearerAuthentication(authentication.TokenAuthentication):
    keyword = "Bearer"