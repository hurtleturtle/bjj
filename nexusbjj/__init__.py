import os
from flask import Flask, render_template, flash
from mysql.connector import Error as SQLError


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True, template_folder='routes/templates')
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'nexusbjj.sqlite'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from nexusbjj.routes import auth
    app.register_blueprint(auth.bp)

    from nexusbjj.routes import users
    app.register_blueprint(users.bp)

    from nexusbjj.routes import classes
    app.register_blueprint(classes.bp)

    from nexusbjj.routes import reports
    app.register_blueprint(reports.bp)

    # from . import validation
    # validation.init_app(app)

     # Add custom jinja2 filters
    app.add_template_filter(os.path.basename, 'basename')
 
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        error = 'Application error. Please try again or contact the administrator.'
        flash(error)
        return render_template('base.html')

    @app.errorhandler(504)
    def handle_gateway_error(e):
        flash('Gateway error.')
        return render_template('base.html')

    # @app.errorhandler(SQLError)
    # def handle_db_error(e):
    #     flash('Database error. Please try again or contact the administrator.')
    #     return render_template('base.html')

    return app
