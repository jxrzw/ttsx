# 使用celery
from celery import Celery
from django.conf import settings
import time
from django.core.mail import send_mail
from django_redis import get_redis_connection
from django.template import loader
# Create your views here.

#　在任务处理者一端加这几句　
# jango环境的初始化
import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

#　创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.190.139:6379/1')

#定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    #组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    send = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s,欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的帐号<br/><a href="http://127.0.0.1/user/active/%s">http://127.0.0.1/user/active/%s</a>' % (
    username, token, token)
    send_mail(subject, message, send, receiver, html_message=html_message)
    time.sleep(5)

@app.task
def generate_static_html():
    '''产生首页静态页面'''
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')
    # 获取首页促销活动信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banner
        type.title_banners = title_banner

    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banner': promotion_banner,
               }
    # 使用模板
    #1.加载模板文件
    temp = loader.get_template('static_index.html')
    #2.定义模板上下文(可以不要)
    #3.模板渲染
    static_index_html = temp.render(context)

    # 生成首页对应的静态文件
    save_path = os.path.join(settings.BASE_DIR,'static/index.html')
    with open(save_path,'w') as f:
        f.write(static_index_html)


