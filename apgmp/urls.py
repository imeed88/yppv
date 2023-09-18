from django.urls import path
from apgmp import views


urlpatterns = [
    path('', views.index, name='index'),
    path('selector/', views.selector, name='selector'),
    path('orderform/<int:order_ref>/<int:order_id>/', views.orderform, name='orderform'),
    path('equipmentform/<int:equipement_invnr>/', views.equipmentform, name='equipmentform'),
    path('order_load/', views.order_load, name='order_load'),  
    path('orders_load/', views.orders_load, name='orders_load'), 
    path('equipments_load/', views.equipments_load, name='equipments_load'), 
    path('reduced_orders_load/', views.reduced_orders_load, name='reduced_orders_load'), 
    path('reduced_orders_load_reduced_to_equipement/', views.reduced_orders_load_reduced_to_equipement, name='reduced_orders_load_reduced_to_equipement'), 
    path('reduced_orders_load_to_current_selector/', views.reduced_orders_load_to_current_selector, name='reduced_orders_load_to_current_selector'), 
    path('reduced_orders_load_to_expired_selector/', views.reduced_orders_load_to_expired_selector, name='reduced_orders_load_to_expired_selector'), 
    path('users_load/', views.users_load, name='users_load'), 
    path('group_load/', views.group_load, name='group_load'),
    path('order_post/', views.order_post, name='order_post'),
    path('upload/', views.upload, name='upload'),
    path('download/', views.download, name='download'),
    path('adminupanel/', views.adminupanel, name='adminupanel'),
    path('adminopanel/', views.adminopanel, name='adminopanel'),
    path('adminepanel/', views.adminepanel, name='adminepanel'),
    path('user_create/', views.user_create, name='user_create'),
    path('user_edit/<str:username>/', views.user_edit, name='user_edit'),
    path('user_delete/<str:username>/', views.user_delete, name='user_delete'),
    path('user_load/', views.user_load, name='user_load'),
    path('user_update/<str:username>/', views.user_update, name='user_update'),
    path('order_print/<int:order_id>/', views.order_print, name='order_print'),
    path('equipment_ohr_print/', views.equipment_ohr_print, name='equipment_ohr_print'),
    path('order_import/', views.order_import, name='order_import'),
    path('login/', views.ulogin, name='ulogin'),
    path('logout/', views.ulogout, name='ulogout'),
]

