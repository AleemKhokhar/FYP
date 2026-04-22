from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.game_search, name='game_search'),
    path('clear-history/', views.clear_history, name='clear_history'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('link-account/', views.link_account, name='link_account'),
    path('delete/<int:stat_id>/', views.delete_account, name='delete_account'),
    path('compare/', views.player_compare, name='player_compare'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('download-report/<int:stat_id>/', views.download_report, name='download_report'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('export-data/', views.export_user_data, name='export_data'),
    path('delete-profile/', views.delete_user_profile, name='delete_profile'),
    path('settings/', views.account_settings, name='account_settings'),
]