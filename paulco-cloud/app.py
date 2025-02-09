import sys
from main import app, db
from dashboard import app

if __name__ == "__main__":
    if "--setup" in sys.argv:
        with app.app_context():
            db.create_all()
            db.session.commit()
            print("Database tables created")
    else:
        app.run(debug=True, host='0.0.0.0', port='5000')