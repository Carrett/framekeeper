def register_blueprints(app):
    from . import movies, series, duplicates, scan, trash, mount

    app.register_blueprint(movies.bp)
    app.register_blueprint(series.bp)
    app.register_blueprint(duplicates.bp)
    app.register_blueprint(scan.bp)
    app.register_blueprint(trash.bp)
    app.register_blueprint(mount.bp)
