from logging.handlers import RotatingFileHandler
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_wtf import CSRFProtect
from flask import Flask, render_template, g, current_app
from flask_wtf.csrf import generate_csrf
from config import *
import redis

# 在Flask很多拓展里面都可以先初始化拓展的对象, 然后再去调用init_app方法去初始化
# 根据这个特性可以现在函数外部定义db对象然后在app_factory函数内部手动调用init_app方法
mysql_db = SQLAlchemy()
# python3.6版本可以通过添加类型标识来防止循环导入的问题
redis_db = None  # type:redis.StrictRedis


def log_factory(config_name):
    """通过此工厂函数判断当前的开发模式并配置相关日志"""
    # 设置当前日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)
    # 创建日志记录器, 参数分别是保存路径, 日志文件大小, 文件个数上限
    log_file = RotatingFileHandler('logs/log', maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志的记录格式, 参数分别是日志等级, 文件名, 行数, 日志信息
    log_format = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 设置日志记录器的日志记录格式
    log_file.setFormatter(log_format)
    # 给全局的日志工具对象添加日志记录器
    logging.getLogger().addHandler(log_file)


def app_factory(config_name):
    """通过此工厂函数将传入的不同配置名字初始化对应配置的实例对象"""
    # 配置项目日志
    log_factory(config_name)
    app = Flask(__name__)
    # 导入配置文件
    app.config.from_object(config[config_name])
    # 配置mysql
    mysql_db.init_app(app)
    # 配置redis
    global redis_db
    redis_db = redis.StrictRedis(
        host=config[config_name].REDIS_HOST,
        port=config[config_name].REDIS_PORT
    )
    # 设置SESSION保护
    Session(app)
    # 开启CSRF保护
    CSRFProtect(app)
    from info.utils.common import user_login_data

    @app.errorhandler(404)
    @user_login_data
    def page_not_found(e):
        """全局捕获404页面"""
        user = g.user
        data = {"user": user.to_dict() if user else None}
        current_app.logger.error(e)
        return render_template("news/404.html", data=data)

    @app.after_request
    def after_request(response):
        # 生成一个随机的csrf值
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 添加自定义过滤器
    from info.utils.common import index_class
    app.add_template_filter(index_class, "index_class")
    # 注册首页蓝图, 在此处进行导包防止循环导入
    from info.modules.index import index_blue
    app.register_blueprint(index_blue)
    # 注册登录页面蓝图
    from info.modules.passport import passport_blue
    app.register_blueprint(passport_blue)
    # 注册新闻详情页面蓝图
    from info.modules.news import news_blue
    app.register_blueprint(news_blue)
    # 注册个人中心页面蓝图
    from info.modules.profile import profile_blue
    app.register_blueprint(profile_blue)
    # 注册后台页面蓝图
    from info.modules.admin import admin_blue
    app.register_blueprint(admin_blue)
    return app
