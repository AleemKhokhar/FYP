from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path('search/', views.game_search, name='game_search'),
    path('clear-history/', views.clear_history, name='clear_history'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('link-account/', views.link_account, name='link_account'),
]
