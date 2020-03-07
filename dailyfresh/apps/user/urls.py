from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from user.views import RegisterView,ActiveView,LoginView,UserInfoView,UserOrderView,UserAddressView,LogoutView

urlpatterns = [
    #url(r'^register$',views.register,name='register'), #注册
    #url(r'^register_handle$',views.register_handle,name='register_handle'), #注册处理
    url(r'^register$', RegisterView.as_view(), name='register'), #注册
    # .as_view()会返回一个view对象
    url(r'^active/(?P<token>.*)$',ActiveView.as_view(), name='active'),#激活用户
    url(r'^login$',LoginView.as_view(),name='login'),#登录
    url(r'^logout$',LogoutView.as_view(),name='logout'),#注销登录

    # url(r'^$',login_required(UserInfoView.as_view()),name='user'),#用户中心－信息页
    # url(r'^order$',login_required(UserOrderView.as_view()),name='order'),#用户中心－订单页
    # url(r'^address$',login_required(UserAddressView.as_view()),name='address'),#用户中心－地址页

    url(r'^$',UserInfoView.as_view(),name='user'),#用户中心－信息页
    url(r'^order/(?P<page>\d+)$',UserOrderView.as_view(),name='order'),#用户中心－订单页
    url(r'^address$',UserAddressView.as_view(),name='address'),#用户中心－地址页
]

