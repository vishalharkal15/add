from flask import Flask
from flask_cors import CORS
from mtcnn import MTCNN
from keras_facenet import FaceNet

# Initialize Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)

# Initialize DB
from database import init_db
db, Attendance, Student = init_db(app)

# Initialize FaceNet & MTCNN
detector = MTCNN()
embedder = FaceNet()

# Register routes
from routes import register_routes
register_routes(app, db, Attendance, detector, embedder)

if __name__ == "__main__":
    app.run(
    host="0.0.0.0", 
    port=5000, 
    ssl_context=("../10.68.222.139+2.pem", "../10.68.222.139+2-key.pem")
)
