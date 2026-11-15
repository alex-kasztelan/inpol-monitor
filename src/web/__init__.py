"""Flask web application package for Inpol Monitor."""

import os
from flask import Flask, session


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
    
    # Configure secret key for session management
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Register blueprints
    from src.web.routes import bp as web_bp
    app.register_blueprint(web_bp)
    
    # Register context processor for templates
    @app.context_processor
    def inject_translations():
        """Make translation function and language available in all templates."""
        # Get language from session, fallback to .env
        lang = session.get('language', os.getenv('LANGUAGE', 'en'))
        
        try:
            from src.localization import load_translations, t as _t
            # Load translations for session language
            load_translations(lang)
        except Exception as e:
            def _t(key, default=None):
                return default or key
        
        # Simple t function that always uses session language
        def t(key, default=None):
            try:
                from src.localization import t as _tr
                return _tr(key, default, language=lang)
            except Exception:
                return default or key
        
        return dict(
            t=t,
            lang=lang,
            languages=[
                ('en', 'English'),
                ('pl', 'Polski'),
                ('ua', 'Українська'),
                ('ru', 'Русский')
            ]
        )
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)