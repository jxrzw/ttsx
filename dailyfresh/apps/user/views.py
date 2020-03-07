from django.shortcuts import render, redirect
import re
from utils.mixin import LoginRequireMixin
from django.urls import reverse
from django.views.generic import View
from django.core.paginator import Paginator
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.http import HttpResponse
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate,login,logout
from django_redis import get_redis_connection
from django.core.mail import send_mail
# Create your views here.

# /user/register
def register(request):
    if request.method == 'GET':
        '''显示注册页面'''
        return render(request, 'register.html')
    else:
        # 进行注册处理
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户不存在
            user =  None
        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 进行业务处理:进行用户注册
        # user = User()
        # user.username = username
        # user.password = password
        # user.save()
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))

    #return render(request, 'register.html')

def register_handle(request):
    '''进行注册处理'''
    # 接受数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')
    # 进行数据校验
    if not all([username, password , email]):
        # 数据不完整
        return render(request, 'register.html', {'errmsg':'数据不完整'})

    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
        return render(request,'register.html',{'errmsg':'邮箱格式不正确'})

    if allow != 'on':
        return render(request,'register.html',{'errmsg':'请同意协议'})

    # 校验用户名是否重复
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # 用户不存在
        user =  None
    if user:
        return render(request, 'register.html', {'errmsg':'用户已存在'})



    # 进行业务处理:进行用户注册
    # user = User()
    # user.username = username
    # user.password = password
    # user.save()
    user = User.objects.create_user(username,email,password)
    user.is_active = 0
    user.save()

    # 返回应答,跳转到首页
    return redirect(reverse('goods:index'))


class RegisterView(View):
    '''注册'''
    def get(self, request):
        '''显示注册页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''进行注册处理'''
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户不存在
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 进行业务处理:进行用户注册
        # user = User()
        # user.username = username
        # user.password = password
        # user.save()
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 发送激活邮件，包含激活链接：http://127.0.0.1:8000/user/active/id
        # 激活链接中需要包含用户的身份信息，并且要把身份性息要加密
        # 加密用户的身份信息，生成激活token
        serializer = Serializer(settings.SECRET_KEY,3600)
        info = {'confirm':user.id}
        token = serializer.dumps(info) # bytes类型数据
        token = token.decode('utf8')
        # 发邮件
        send_register_active_email.delay(email,username,token)

        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户激活'''
    def get(self, request, token):
        '''进行用户激活'''
        # 进行解密,获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']
            # 根据用户id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 跳转到登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')

    # /user/login
class LoginView(View):
    '''登录'''
    def get(self, request):
        '''显示登录页面'''
        #判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            cheked = 'checked'
        else:
            username = ''
            cheked = ''
        # 使用模板
        return render(request,'login.html',{'username':username,'checked':cheked})

    def post(self,request):
        # 接受数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg':'数据不完整'})

        # 业务处理:登录校验
        #User.objects.get(username=username,password=password)

        user = authenticate(username=username,password=password)
        if user is not None:
            # 用户密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户登录状态
                login(request,user)

                # 获取登录后所要跳转到的地址
                # 默认跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))

                # 　跳转到 next_url
                response = redirect(next_url) #HttpResponseRedirect
                #判断是否需要记住用户名
                remember = request.POST.get('remember')

                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

                # 返回response
                return response


            else:
                # 用户未激活
                return render(request,'login.html',{'errmsg':'账户未激活'})
        else:
            # 用户密码错误
            return render(request, 'login.html', {'errmsg':'用户名或密码错误'})

#/user/logout
class LogoutView(View):
    '''退出登录'''
    def get(self,request):
        # 清除用户session信息
        logout(request)

        #跳转到首页
        return redirect(reverse('goods:index'))

# /user
class UserInfoView(LoginRequireMixin,View):
    '''用户中心－信息页'''
    def get(self,request):
        '''显示'''
        # page='user'
        # Django会给request对象添加一个属性request.user
        # 如果用户未登录->AnonymousUser类的一个实例
        # 如果用户登录->User类的一个实例
        # request.user.is_authenticated()　来判断用户有没有登录 True就登录　False就没

        # 获取用户个人信息

        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户的历史浏览记录

        #from redis import StrictRedis
        #sr = StrictRedis(host='192.168.190.136',port=3679,db=9)

        con = get_redis_connection('default')

        history_key = 'history_%d'%user.id

        #获取用户最新浏览的5个商品id
        sku_ids = con.lrange(history_key, 0, 4)

        # 重数据库中查询浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)

        #便利获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        #　组织上下文
        contex = {'page':'user',
                  'address':address,
                  'goods_li':goods_li}

        # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传递给模板文件
        return render(request,'user_center_info.html',contex)

# /user/order
class UserOrderView(LoginRequireMixin,View):
    '''用户中心－订单页'''
    def get(self, request, page):
        '''显示'''
        # 获取用户的订单信息
        # page='order'
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            # 根据order_id 查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历order_skus计算商品的小计
            for order_sku in order_skus:
                #计算小计
                amount = order_sku.count*order_sku.price
                # 动态给order_sku增加属性amount,保存订单商品的小计
                order_sku.amount = amount

            # 动态给order增加属性,保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            #动态给order增加属性,保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders,1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Ｐages实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        #  1.总页数下于5页，页面上显示所以页码
        # 2.如果当前页是前三页，显示１－5页
        # 3.如果当前页是后三也，显示后5也
        # 4.其他情况，显示当前的前2也，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page':order_page,
                   'pages':pages,
                   'page': 'order'}

        # 使用模板
        return render(request, 'user_center_order.html',context)


# /user/address
class UserAddressView(LoginRequireMixin,View):
    '''用户中心－地址页'''
    def get(self, request):
        '''显示'''
        # page='address'
        # 　获取登录用户对应的User对象
        user = request.user

        # 获取用户的默认收获地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True) # models.Manager
        # except Address.DoesNotExist:
        #     # 不存在默认收获地址
        #     address = None
        address = Address.objects.get_default_address(user)
        # 使用模板
        return render(request, 'user_center_site.html',{'page':'address', 'address':address})

    def post(self,request):
        '''地址添加'''
        # 接受数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html',{'errmsg':'数据不完整'})
        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$',phone):
            return render(request,'user_center_site.html',{'errmsg':'手机格式不正确'})

        # 业务处理:地址添加
        # 如果用户一存在默认收获地址，添加的地址不作为默认收获地址，否则作为默认收获地址

        #　获取登录用户对应的User对象
        user = request.user
        # try:
        #     address = Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收获地址
        #     address = None

        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        # 返回应答,刷新地址页面
        return redirect(reverse('user:address')) # get请求方式




