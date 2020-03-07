from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRequireMixin
# Create your views here.

# 添加商品到购物车:
# 1) 请求方式，采用 ajax post
# 如果涉及到数据修改(新增,跟新,删除),采用post
# 如果只涉及到数据的获取,采用get
# 2) 传递参数:商品id(sku_id) 商品数量(count)

# ajax发起的请求都在后台，在浏览器中看不到效果
# /cart/add
class CartAddView(View):
    '''购物车记录添加'''
    def post(self,request):
        '''购物车记录添加'''
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res':0,'errmsg':'请先登录'})
        # 接受数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 数据校验
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':'数据不完整'})

        #校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            #数目出错
            return JsonResponse({'res':2,'errmsg':'商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            #商品不存在
            return JsonResponse({'res':3,'errmsg':'商品不存在'})

        # 业务处理:添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 先尝试获取sku_id的值 ->hget cart_key 属性
        # 如果sku_id在hash中不存在,hget返回None
        cart_count = conn.hget(cart_key,sku_id)
        if cart_count:
            # 累加购物车中商品数目
            count += int(cart_count)
        # 校验商品库存
        if count > sku.stock:
            return JsonResponse({'res':4,'errmsg':'商品库存不足'})
        # 设置hash中sku_id对应的值
        # hset->如故sku_id已经存在，跟新数据，如果sku_id不存在就是添加
        conn.hset(cart_key,sku_id,count)

        # 计算用户购物车商品的条目数
        total_count = conn.hlen(cart_key)
        # 返回应答
        return JsonResponse({'res':5,'total_count':total_count,'errmsg':'添加成功'})

# /cart/
class CartInfoView(LoginRequireMixin,View):
    '''购物车页面显示'''
    def get(self,request):
        '''显示'''
        # 获取登录的用户
        user = request.user
        # 获取用户购物车中商品的信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # {'商品id':'商品数量'}
        cart_dict = conn.hgetall(cart_key)

        skus = []
        # 保存用户购物车中商品的总数目和总价格
        total_count = 0
        total_price = 0
        # 遍历获取商品的信息
        for sku_id, count in cart_dict.items():
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品的小计
            amount = sku.price*int(count)
            #　动态给sku对象增加一个属性amount,保存商品的小计
            sku.amount = amount
            # 动态给sku对象增加一个属性count,保存购物车中对应商品的数量
            sku.count = count
            # 添加
            skus.append(sku)

            # 累加计算商品的总数目和总价格
            total_count += int(count)
            total_price += amount

        # 组织上下文
        context = {'total_count':total_count,
                   'total_price':total_price,
                   'skus':skus}


        return render(request, 'cart.html',context)

# /cart/update
# 跟新购物车商品数目
# 采用ajax　post请求,
# 前端需要传递的参数:商品id(sku_id) 跟新的商品数量(count)
class CartUpdateView(View):

    def post(self,request):
        '''购物车记录跟新'''
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接受数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            # 数目出错
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理:跟新购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        #校验商品库存
        if count > sku.stock:
            return  JsonResponse({'res':4,'errmsg':'商品库存不足'})

        #跟新
        conn.hset(cart_key,sku_id,count)

        # 计算购物车中商品的总件数{'1':5,'2':3}　
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res':5,'total_count':total_count,'errmsg':'跟新成功'})

#删除购物车记录
#采用ajax post请求
#前端需要传递的参数:商品id(sku_id)
# /acrt/delete
class CartDeleteView(View):
    '''购物车记录删除'''
    def post(self,request):
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        #接受参数
        sku_id = request.POST.get('sku_id')

        #数据校验
        if not sku_id:
            return JsonResponse({'res':1,'errmsg':'无效的商品id'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res':2,'errmsg':'商品不存在'})

        # 业务处理:删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 删除 hdel
        conn.hdel(cart_key,sku_id)

        # 计算购物车中商品的总件数{'1':5,'2':3}　
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        # 返回应答
        return  JsonResponse({'res':3,'total_count':total_count,'errmsg':'删除成功'})
